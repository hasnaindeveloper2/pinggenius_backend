import os
from utils.extract_name import extract_name
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, RunConfig, Runner, function_tool
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

# ------------------- Tools -------------------


@function_tool
def is_junk(subject: str, body: str) -> bool:
    return "unsubscribe" in body.lower() or "offer" in subject.lower()


@function_tool
def is_easy_response(subject: str, body: str) -> bool:
    keywords = [
        "projects",
        "status",
        "update",
        "meeting",
        "availability",
        "question",
        "help",
        "thanks",
        "schedule",
        "important",
        "greeting",
        "feedback",
        "conversation",
        "talk",
    ]
    return any(word in f"{subject.lower()} {body.lower()}" for word in keywords)


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
You are an email assistant.

1. Call `is_junk(subject, body)` → If True, return 'junk'
2. Else, call `is_easy_response(subject, body)`
3. If easy → call `generate_reply(subject, body, sender, id)` and return: 'easy: <reply>'
4. Else → return 'hard'

Always call tools. Never guess.
""",
    tools=[is_junk, is_easy_response, generate_reply],
)


# Run wrapper
async def run_email_agent(input_text: str) -> str:
    result = await Runner.run(main_agent, run_config=config, input=input_text)
    # replace subject: word with empty
    replaced_subject_final_output = result.final_output.replace("Subject:", "")
    # print(replaced_subject_final_output)
    return replaced_subject_final_output