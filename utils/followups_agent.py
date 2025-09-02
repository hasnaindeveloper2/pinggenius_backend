from agents import (
    Agent,
    RunContextWrapper,
    Runner,
    set_tracing_disabled,
    OpenAIChatCompletionsModel,
    GuardrailFunctionOutput,
    output_guardrail,
    TResponseInputItem,
)
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import AsyncOpenAI
import os

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


class FollowUpEmailOutput(BaseModel):
    is_follow_up_email: bool
    reasoning: str


followups_email_guardrail = Agent(
    name="Followups Email Guardrail",
    instructions="""
You are a follow-up email validator. You're given the output from another agent that claims to generate follow-up emails.

Analyze the content and decide:
- Is this a genuine follow-up email that continues a previous conversation?
- Does it reference prior interactions or context?

If YES → return: is_follow_up_email = True
If NO → return: is_follow_up_email = False

""",
    model=model,
    output_type=FollowUpEmailOutput,
)


@output_guardrail
async def validate_cold_email_output(
    ctx: RunContextWrapper, agent: Agent, input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    result = await Runner.run(
        followups_email_guardrail,
        input=input,
        context=ctx.context,
    )
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=not result.final_output.is_follow_up_email,
    )


followups_generator_agent = Agent(
    name="Followups Generator",
    instructions="""
You generate ultra-personalized follow-up emails based on LinkedIn profile, role, about, and website.

Tone must match the input:
- Friendly: conversational and warm
- Formal: respectful and business-like
- Funny: witty but professional

Always keep it short, relevant, and focused on getting a reply.

use \n \n\n character instead of /n or /n/n.

never guess anything just generate unique follow-up emails.

don't include anything unrelated like okay, i will assist you, will help you with generating follow-up emails

important!
Your output format should be:

---
Email 1

---
Email 2
""",
    model=model,
    output_guardrails=[validate_cold_email_output],
)
