import os
from utils.extract_name import extract_name
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    RunConfig,
    Runner,
    function_tool,
    output_guardrail,
    OutputGuardrailTripwireTriggered,
    GuardrailFunctionOutput,
    RunContextWrapper,
    TResponseInputItem,
)
from pydantic import BaseModel
import asyncio
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import re

# Load environment variables
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
db = client["test"]
users_collection = db["waitlistsusers"]

# Gemini client setup
provider = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# Model + config
model = OpenAIChatCompletionsModel(
    openai_client=provider,
    model="gemini-2.0-flash",
)
config = RunConfig(model=model, model_provider=provider, tracing_disabled=True)


class ReplyValidatorOutput(BaseModel):
    is_not_valid_reply: bool
    reasoning: str


class EasyResponseCheck(BaseModel):
    is_easy: bool
    reasoning: str


# -------------- guardrail agents ------------------
reply_guardrail_agent = Agent(
    name="Reply Output Guardrail",
    instructions="""
You are a reply quality checker.

Given an email reply, decide if it's:
- Polite and directly related to the original email
- Includes a proper greeting with the sender’s name
- Ends with "best regards" or "best"
- Doesn’t contain filler like "I’m just an AI language model" or garbage

If yes, return: is_not_valid_reply = True  
Else, return: is_not_valid_reply = False and explain why.
""",
    output_type=ReplyValidatorOutput,
)


@output_guardrail
async def validate_reply_output(
    ctx: RunContextWrapper,
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    result = await Runner.run(
        reply_guardrail_agent, input=input, context=ctx.context, run_config=config
    )
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_not_valid_reply,
    )


# ------------------- Tools -------------------


@function_tool
def is_junk(subject: str, body: str) -> bool:
    return "unsubscribe" in body.lower() or "offer" in subject.lower()


easy_response_agent = Agent(
    name="Easy Response Classifier",
    instructions="""
You are an email complexity detector.

Given an email's subject and body, decide if it's an **easy response**. That means:
- It's quick to reply (status update, scheduling, thanks, minor question)
- Doesn't need deep thought, long writing, or research

If yes → is_easy = True  
If no → is_easy = False

Always provide a short reasoning (e.g., "Simple scheduling request", "Detailed pricing inquiry").
""",
    output_type=EasyResponseCheck,
)


@function_tool
async def is_easy_response(subject: str, body: str) -> bool:
    input_prompt = f"Subject: {subject}\nBody: {body}"
    result = await Runner.run(
        easy_response_agent,
        input=input_prompt,
        run_config=config,
    )
    return result.final_output.is_easy


# Sub-agent for reply generation
reply_agent = Agent(
    name="Reply Writer",
    instructions="""
You are a professional email replier.

- Read the subject AND body carefully.
- Your reply must be based on the sender's name, subject and body.
- Match the tone (Casual → Friendly, Business → Formal, Funny → Witty).
- Greet the person using their name.
- Always include a closing like:  
best regards,
""",
)


@function_tool
async def generate_reply(subject: str, body: str, sender: str, id: str) -> str:
    mongo_id = ObjectId(id)
    user = await users_collection.find_one({"_id": mongo_id})
    your_name = (
        user["username"] if user and "username" in user else "PingGenius Assistant"
    )

    # extarct the name remove extra numbers from your_name and add space like "Hasnain siddique"
    your_name = re.sub(r"\d+", " ", your_name).strip()

    name = extract_name(sender)

    body = body.strip() if body else "No body content provided."
    print("body is presents", body)

    prompt = f"""You are an ultra-personalized email reply assistant.
    
Email Details:
- From: {name}
- Subject: {subject}
- Body: {body}

Instructions:
Write a polite and personalized reply addressed to {name}.
- Match tone: Casual → Friendly, Business → Formal, Funny → Witty but professional.
- Always include a greeting using {name}.
- End with:  
best regards or best,  
{your_name}
"""

    result = await Runner.run(reply_agent, run_config=config, input=prompt)
    return result.final_output


# ------------------- Main Agent -------------------

main_agent = Agent(
    name="Email Agent",
    instructions="""
You are an email agent.

1. Call `is_junk(subject, body)` → If True, return 'junk'
2. Else, call `is_easy_response(subject, body)`
3. If easy → call `generate_reply(subject, body, sender, id)` and return: 'easy: <reply>'
4. Else → return 'hard'

Always call tools. Never guess.
""",
    tools=[is_junk, is_easy_response, generate_reply],
    output_guardrails=[validate_reply_output],
)


# Run wrapper
async def run_email_agent(input_text: str) -> str:
    try:
        result = await Runner.run(main_agent, run_config=config, input=input_text)
        # replace subject: word with empty
        replaced_subject_final_output = result.final_output.replace("Subject:", "")

        return replaced_subject_final_output
    except OutputGuardrailTripwireTriggered:
        print("guardrail was triggered — not a valid reply")
