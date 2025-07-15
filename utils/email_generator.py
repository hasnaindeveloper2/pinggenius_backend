from agents import (
    Agent,
    Runner,
    RunConfig,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
import re

load_dotenv()
set_tracing_disabled(disabled=True)

gemini_api_key = os.getenv("GEMINI_API_KEY")

provider = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

model = OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=provider)
config = RunConfig(model=model, model_provider=provider)

generator_agent = Agent(
    name="Cold Email Generator",
    instructions="""
You generate ultra-personalized cold emails based on LinkedIn profile, role, and website also include email if provided.

Tone must match the input:
- Friendly: conversational and warm
- Formal: respectful and business-like
- Funny: witty but professional

Always keep it short, relevant, and focused on getting a reply.

Your output format should be:

---
Email 1
[put email]

---
Email 2
[put email]

""",
)


def smart_split_variations(output: str) -> list[str]:
    return re.split(r"\n\s*---\s*\n", output.strip())  # [email1, email2]


def extract_name_from_linkedin(url: str) -> str:
    # Example: https://linkedin.com/in/muhammad-hasnain
    username = url.strip("/").split("/")[-1]
    parts = username.replace("-", " ").title().split()  # [Muhammad, Hasnain]
    return " ".join(parts)


async def generate_cold_email(
    linkedin_url: str, role: str, website: str | None, tone: str, email: str
) -> list[str]:
    name = extract_name_from_linkedin(linkedin_url)
    input_prompt = f"""
Name: {name}
LinkedIn URL: {linkedin_url}
Role: {role}
Website: {website or 'Not provided'}
Tone: {tone}
Email: {email}

Generate 2 cold email variations.
"""
    result = await Runner.run(generator_agent, run_config=config, input=input_prompt)
    return smart_split_variations(result.final_output)
