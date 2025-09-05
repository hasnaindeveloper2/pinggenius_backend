import asyncio
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


email_reply_validate = Agent(
    name="Email Reply Validation Agent",
    instructions="""You are a expert email validator
Your job is to:
- Ensure the email reply is professional, concise, and polite.
- Ensure the reply directly addresses the main points of the original email.
- Ensure the tone is clear, respectful, and human-like.
- Ensure the reply ends with a warm closing such as 'Best,' or 'Best regards,'

If the reply meets all of the above requirements, output:
is_valid_reply = True

If the reply fails to meet any of the requirements, output:
is_valid_reply = False
provide reasoning why it is not a valid reply.
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
    result = await Runner.run(email_reply_validate, input, context=ctx.context)
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

    never guess always generate the email reply
    """,
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
        print(result.final_output)
        return result.final_output
    except OutputGuardrailTripwireTriggered:
        print("Guardrail triggered — not a valid reply.")
        return "Guardrail triggered — not a valid reply."

