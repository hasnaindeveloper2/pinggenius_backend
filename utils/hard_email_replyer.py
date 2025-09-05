from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from openai import AsyncOpenAI
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import re
from pydantic import BaseModel

load_dotenv()
set_tracing_disabled(disabled=True)

gemini_api_key = os.getenv("GEMINI_API_KEY")


provider = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=provider,
)


class EmailReplyOutputCheck(BaseModel):
    is_valid_reply: bool
    reasoning: str


email_reply_validation_agent = Agent(
    name="Email Reply Validation Agent",
    instructions="""You are an expert email validator.
    your bob is to:
    - Ensure the email reply is professional, concise, and polite.
    - Ensure the reply directly addresses the main points of the original email.
    - Ensure the tone is clear, respectful, and human-like.
    
    if the reply is appropriate, output:
    is_valid_reply = True
    else, output: is_valid_reply = False
    """,
    output_type=EmailReplyOutputCheck,
)

reply_agent = Agent(
    name="Email Reply Agent",
    instructions="""You are an expert email assistant. 
The user provides a refined email draft. 
Your job is to:
- Transform it into a professional, concise, and polite reply also matching the tone of the original email.
- If the sender's name is provided, start the reply with a natural greeting.
- Do not include subject lines or raw headers in the output.
- Ensure the reply directly addresses the main points of the original email.
- Keep the tone clear, respectful, and human-like.

Output only the final email body content that can be sent immediately.""",
    model=model,
)
