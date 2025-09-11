import os
from utils.extract_name import extract_name
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    output_guardrail,
    OutputGuardrailTripwireTriggered,
    GuardrailFunctionOutput,
    RunContextWrapper,
    TResponseInputItem,
    set_tracing_disabled,
)
from pydantic import BaseModel
import asyncio
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from database.mongo import db
import re

# Load environment variables
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

set_tracing_disabled(disabled=True)

users_collection = db["users"]

# Gemini client setup
client = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# Model + config
model = OpenAIChatCompletionsModel(
    openai_client=client,
    model="gemini-2.0-flash",
)


# ---------------- Models ----------------
class ReplyValidatorOutput(BaseModel):
    is_valid_reply: bool
    reasoning: str


class EasyResponseCheck(BaseModel):
    is_easy: bool
    reasoning: str


class ProfessionalCheck(BaseModel):
    is_professional: bool
    reasoning: str


# ---------------- Guardrail ----------------
reply_guardrail_agent = Agent(
    name="Reply Output Guardrail",
    instructions="""
You are a reply quality checker.

Given an email reply, decide if it's:
- Polite and directly related to the original email
- Includes a proper greeting with the sender’s name
- Ends with "best regards" or "best"
- Doesn’t contain filler like "I’m just an AI language model" or garbage

If yes, return: is_valid_reply = True  
Else, return: is_valid_reply = False.
""",
    output_type=ReplyValidatorOutput,
    model=model,
)


@output_guardrail
async def validate_reply_output(
    ctx: RunContextWrapper,
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    result = await Runner.run(reply_guardrail_agent, input=input, context=ctx.context)
    
    out = result.final_output or ReplyValidatorOutput(
        is_valid_reply=False, reasoning="empty output"
    )
    
    return GuardrailFunctionOutput(
        output_info=out,
        tripwire_triggered=not bool(out.is_valid_reply),
    )


# ---------------- Agents ----------------

# 1. Professional filter
professional_agent = Agent(
    name="Professional Filter",
    instructions="""
You are an email professional relevance filter.

Given subject + body, classify the email strictly into one of two categories:

1. PROFESSIONAL (business, client, work, networking, sales inquiries, partnerships, investment, product demo requests, communication, formal collaboration, simple questions (e.g. greetings))
2. NON-PROFESSIONAL (spam, promotions, newsletters, system updates, marketing campaigns, login/sign-up confirmations, job alerts, welcome emails, community/social media notifications like LinkedIn/Twitter/Instagram, receipts, OTPs, system alerts)

Rules:
- If the email is explicitly about work opportunities, business proposals, sales deals, partnerships, or professional networking, mark as PROFESSIONAL.
- If it is generic, promotional, marketing, newsletters, system alerts, or account/login related, mark as NON-PROFESSIONAL.
- Be conservative: only mark emails as PROFESSIONAL if they clearly show work/business intent.

Output:
- is_professional (True/False)
- reasoning (one short reason why)
""",
    output_type=ProfessionalCheck,
    model=model,
)


@function_tool
async def is_professional(subject: str, body: str) -> bool:
    input_prompt = f"Subject: {subject}\nBody: {body}"
    result = await Runner.run(professional_agent, input=input_prompt)
    return result.final_output.is_professional


# 2. Easy response classifier
easy_response_agent = Agent(
    name="Easy Response Classifier",
    instructions="""
You are an email complexity detector.

Given an email's subject and body, decide if it's an easy response. That means:
- Doesn't need deep thought, long writing, or research

If yes → is_easy = True
If no → is_easy = False

reasoning too (but optional).
""",
    output_type=EasyResponseCheck,
    model=model,
)


@function_tool
async def is_easy_response(subject: str, body: str) -> bool:
    safe_subject = subject or ""
    safe_body = body or ""
    input_prompt = f"Subject: {safe_subject}\nBody: {safe_body}"
    result = await Runner.run(
        easy_response_agent,
        input=input_prompt,
    )
    return bool(result.final_output.is_easy)


# 3. Reply generator
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
    model=model,
)


@function_tool
async def generate_reply(subject: str, body: str, sender: str, id: str) -> str:
    mongo_id = ObjectId(id)
    user = await users_collection.find_one({"_id": mongo_id})
    your_name = (
        user["username"] if user and "username" in user else "PingGenius Assistant"
    )

    your_name = re.sub(r"\d+", " ", your_name).strip()
    name = extract_name(sender)

    body = body.strip() if body else "No body content provided."

    prompt = f"""You are an ultra-personalized email reply assistant.
    
Email Details:
- From: {name}
- Subject: {subject}
- Body: {body}

Instructions:
Write a polite and personalized reply addressed to {name}.
- Match tone: Casual → Friendly, Business → Formal, Funny → Witty but professional.
- your reply should be title case professionally.
- Always include a greeting using {name}.
- End with:  
best regards or best,  
{your_name}
"""

    result = await Runner.run(reply_agent, input=prompt)
    return result.final_output


# ---------------- Main Agent ----------------
main_agent = Agent(
    name="Email Agent",
    instructions="""
You are an email agent.

1. Call `is_professional(subject, body)` → 
   - If False → return 'junk'
2. Else, call `is_easy_response(subject, body)` → 
   - If easy → call `generate_reply(subject, body, sender, id)` and return: 'easy: <reply>'
   - If not easy → return 'hard'

Always call tools. Never guess.
""",
    tools=[is_professional, is_easy_response, generate_reply],
    output_guardrails=[validate_reply_output],
    model=model,
)


# Run wrapper
async def run_email_agent(input_text: str) -> str:
    try:
        result = await Runner.run(main_agent, input=input_text)
        # replace subject: word with empty
        final_output = result.final_output.replace("Subject:", "")

        print(final_output)
        return final_output
    except OutputGuardrailTripwireTriggered:
        print("guardrail was triggered — not a valid reply")