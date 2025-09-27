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
from database.mongo import db
from urllib.parse import urlparse
import re
import asyncio

load_dotenv()

users = db["users"]

gemini_api_key = os.getenv("GEMINI_API_KEY")

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


# A class to check wheather the cold email or not
class ColdEmailGuardrailOutput(BaseModel):
    is_not_cold_email: bool
    reasoning: str


cold_email_guardrail_agent = Agent(
    name="Cold Email Guardrail",
    instructions="""
Validate that the text is exactly two first-contact cold emails
formatted like:

---
Email 1
---
Email 2

Requirements:
• Each email has a subject and a body.
• It greets the person by name.
• It is short, relevant, and aims for a reply.
• No placeholders such as [Name] or [Company] etc.

Return:
is_not_cold_email = False  → valid output
is_not_cold_email = True   → invalid output
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
You generate ultra-personalized cold emails based on LinkedIn profile, role, about, tone, name, and website.

Tone must match the input:
- Friendly: conversational and warm
- Formal: respectful and business-like
- Funny: witty but professional

- every email has subject and body
- greet the person using the name provided
- Always keep it short, relevant, and focused on getting a reply.
- do not include placeholders like [Name], [Company], etc.

use the \n or \n\n character 

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
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    path = urlparse(url).path
    username = path.rstrip("/").split("/")[-1]
    username = re.sub(r"-\d+$", "", username)

    # just title-case the slug, no splitting
    return username.replace("-", " ").title()  # e.g. "John Doe" or "hasnainxdev"


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

            `user_id (str): MongoDB user ID of the reciver`

        Returns:
            list[str]: A list containing two variations of generated cold emails

        Raises:
            None explicitly, but may raise database-related exceptions
    """

    # here the real logic begins
    mongo_id = ObjectId(user_id)
    user = await users.find_one({"_id": mongo_id})

    your_name = user["name"] if user and "name" in user else "PingGenius Assistant"

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
        print(result.final_output)
        return smart_split_variations(result.final_output)
    except OutputGuardrailTripwireTriggered:
        print("\n Guardrail tripped - not valid cold email")


asyncio.run(
    generate_cold_email(
        linkedin_url="https://www.linkedin.com/in/hasnainxdev/",
        role="Full-Stack Dev",
        tone="friendly",
        about="full-stack & AI dev — building real products, not portfolios. 40+ shipped projects (mini to mid-scale) — from AI email agents to e-commerce platforms.",
        user_id="68c28010ed3afa8eedba6cbc",
    )
)
