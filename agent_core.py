import os
from utils.extract_name import extract_name
from dotenv import load_dotenv
from openai import AsyncOpenAI
from agents import Agent, OpenAIChatCompletionsModel, RunConfig, Runner, function_tool

# Load environment variables
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

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
        "talk"
    ]
    return any(word in f"{subject.lower()} {body.lower()}" for word in keywords)


# Sub-agent for reply generation
reply_agent = Agent(
    name="Reply Writer",
    instructions="""
You write professional replies. Your tone must match the context:
- Casual → Friendly
- Business → Formal
- Funny → witty but professional
Always include a polite closing.

!important

write the name of user using their email address
""",
)


@function_tool
async def generate_reply(subject: str, body: str, sender: str) -> str:
    name = extract_name(sender)

    prompt = f"""
    You are an ultra-personalized email reply assistant.

    From: {name}
    Subject: {subject}
    Body: {body}

    Write a reply addressed to **{name}**.
    - Match tone: Casual → Friendly, Business → Formal, Funny → Witty but professional.
    - Add a **personal closing** like: Best regards, [Your Name]".

    IMPORTANT:
    - Greet using {name}
    - End the email with:  
    **Warm regards,**  
"""

    result = await Runner.run(reply_agent, run_config=config, input=prompt)
    return result.final_output


# ------------------- Main Agent -------------------

main_agent = Agent(
    name="Email Agent",
    instructions="""
You are an email assistant.

1. Call `is_junk(subject, sender, body)` → If True, return 'junk'
2. Else, call `is_easy_response(subject, body)`
3. If easy → call `generate_reply(subject, body, sender)` and return: 'easy: <reply>'
4. Else → return 'hard'

Always call tools. Never guess.
""",
    tools=[is_junk, is_easy_response, generate_reply],
)


# Run wrapper
async def run_email_agent(input_text: str) -> str:
    result = await Runner.run(main_agent, run_config=config, input=input_text)
    return result.final_output.split("\n")[0]
