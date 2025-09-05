from agents import (
    Agent,
    Runner,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
    GuardrailFunctionOutput,
    output_guardrail,
    OutputGuardrailTripwireTriggered,
    RunContextWrapper,
    TResponseInputItem,
)
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
    your job is to:
    - Ensure the email reply is professional, concise, and polite.
    - Ensure the reply directly addresses the main points of the original email.
    - Ensure the tone is clear, respectful, and human-like.
    
    if the reply is appropriate, output:
    is_valid_reply = True
    else, output: is_valid_reply = False
    """,
    model=model,
    output_type=EmailReplyOutputCheck,
)


@output_guardrail
async def email_reply_validation_guardrail(
    ctx: RunContextWrapper[EmailReplyOutputCheck],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    result = await Runner.run(email_reply_validation_agent, input, context=ctx.context)
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not result.final_output.is_valid_reply,
    )


reply_agent = Agent(
    name="Email Reply Agent",
    instructions="""You are an expert email assistant. 
The user provides a refined email draft. 
Your job is to:
- Transform it into a professional, concise, and polite reply matching the tone of the original email.
- If the sender's name is provided, start the reply with a natural greeting using that name.
- Do not include subject lines or raw headers in the output.
- Ensure the reply directly addresses the main points of the original email.
- Keep the tone clear, respectful, and human-like.
- End with a warm closing (e.g. "Best," "Best regards,") signed with the user's name.

Output only the final email body content that can be sent immediately.""",
    model=model,
    output_guardrails=[email_reply_validation_guardrail],
)


async def generate_reply(refined_body: str, your_name: str, sender_name: str) -> str:
    try:
        result = await Runner.run(
            reply_agent,
            input=f"""
You are the professional email reply assistant.

The user has refined their draft.  
Draft the reply with:
- A greeting using the sender’s name: {sender_name}
- The refined content: {refined_body}
- A closing signed off with the user’s name (e.g. best or best regards): {your_name}
        """,
        )
        return result.final_output
    except OutputGuardrailTripwireTriggered:
        raise Exception("Guardrail triggered — not a valid reply.")
