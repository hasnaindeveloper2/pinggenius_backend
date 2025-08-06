from agents import (
    Agent,
    Runner,
    RunConfig,
    OpenAIChatCompletionsModel,
    output_guardrail,
    GuardrailFunctionOutput,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    TResponseInputItem,
)
from openai import AsyncOpenAI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from bson import ObjectId
from typing import Literal
from motor.motor_asyncio import AsyncIOMotorClient
import re
import asyncio

load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")


client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
db = client["test"]
users_collection = db["waitlistsusers"]

provider = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=provider,
)

config = RunConfig(
    model=model,
    model_provider=provider,
    tracing_disabled=True,
)


# A class to check wheather the cold email generated `actually a cold email` to prevent extra token usage
class ColdEmailGuardrailOutput(BaseModel):
    is_not_cold_email: bool
    reasoning: str


# ------------- this guardrail agent check is cold email valid and related to emails ------------------

cold_email_guardrail_agent = Agent(
    name="Cold Email Guardrail",
    instructions="""
You are a cold email validator. You're given the output from another agent that claims to generate cold outreach emails.

Analyze the content and decide:
- Is this a genuine cold outreach email written to initiate contact?
- Is it relevant, goal-oriented, and does it look like an actual first-time reachout?

If YES → return: is_not_cold_email = False  
If NO → return: is_not_cold_email = True

""",
    output_type=ColdEmailGuardrailOutput,
)


@output_guardrail
async def validate_cold_email_output(
    ctx: RunContextWrapper, agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(
        cold_email_guardrail_agent, input=input, context=ctx.context, run_config=config
    )
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_not_cold_email,
    )


# ------------- main cold email generator agent ------------------
generator_agent = Agent(
    name="Cold Email Generator",
    instructions="""
You generate ultra-personalized cold emails based on LinkedIn profile, role, about, and website.

Tone must match the input:
- Friendly: conversational and warm
- Formal: respectful and business-like
- Funny: witty but professional

Always keep it short, relevant, and focused on getting a reply.

if you are using /n or /n/n in the email, use the \n character instead of /n or /n/n.

important!
Your output format should be:

---
Email 1

---
Email 2

""",
    output_guardrails=[validate_cold_email_output],
)


def smart_split_variations(output: str) -> list[str]:
    return re.split(r"\n\s*---\s*\n", output.strip())  # [email1, email2]


def extract_name_from_linkedin(url: str) -> str:
    # Example: https://linkedin.com/in/muhammad-hasnain
    username = url.strip("/").split("/")[-1]
    parts = username.replace("-", " ").title().split()  # [Muhammad, Hasnain]
    return " ".join(parts)


async def generate_cold_email(
    linkedin_url: str,
    role: str,
    tone: str,
    about: str | None,
    user_id: str,
    website: str | None = None,
) -> list[str]:
    """
    Generate two cold email variations based on provided LinkedIn profile and user information.
        This asynchronous function creates personalized cold emails using the recipient's LinkedIn
        profile information and the sender's details from the database.

        Args:
            `linkedin_url (str): URL of the recipient's LinkedIn profile`

            `role (str): Professional role or position of the recipient`

            `website (str | None): Recipient's website URL, if available`

            `tone (str): Desired tone for the email (e.g., formal, casual)`

            `about (str | None): Additional context or information about the recipient`

            `user_id (str): MongoDB user ID of the sender`

        Returns:
            list[str]: A list containing two variations of generated cold emails

        Raises:
            None explicitly, but may raise database-related exceptions
    """

    # here the real logic begins
    mongo_id = ObjectId(user_id)
    user = await users_collection.find_one({"_id": mongo_id})

    your_name = (
        user["username"] if user and "username" in user else "PingGenius Assistant"
    )

    # extarct the name remove extra numbers from your_name and add space like "Hasnain siddique"
    your_name = re.sub(r"\d+", " ", your_name).strip()

    name = extract_name_from_linkedin(linkedin_url)
    input_prompt = f"""
Name: {name}
LinkedIn URL: {linkedin_url}
Role: {role}
Website: {website or 'Not provided'}
Tone: {tone}
About: {about}
always end with Best Regard or Best,
{your_name}

Generate 2 cold email variations.
"""
    try:
        result = await Runner.run(
            generator_agent, run_config=config, input=input_prompt
        )
        print("\n Guardrail didn't tripped")
        print(result.final_output)
        return smart_split_variations(result.final_output)
    except OutputGuardrailTripwireTriggered:
        print("\n Guardrail tripped - not valid cold email")


asyncio.run(
    generate_cold_email(
        linkedin_url="https://www.linkedin.com/in/hasnaindeveloper/",
        role="Full Stack developer",
        tone="formal",
        about="Hi I am a full stack developer dlivered over 3+ MVPs, and 30+ projects",
        user_id="689210e73ab6579e73ad5704",
    )
)
