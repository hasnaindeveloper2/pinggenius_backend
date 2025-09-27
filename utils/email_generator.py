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


# ------------- main cold email generator agent ------------------
generator_agent = Agent(
    name="Cold Email Generator",
    instructions="""
You generate ultra-personalized cold emails based on LinkedIn profile, role, about, tone, name, and website.

Tone must match the email:
- Friendly: conversational and warm
- Formal: respectful and business-like
- Funny: witty but professional

- every email has tone
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
    except Exception as e:
        print("Error in generate_cold_email:", str(e))
