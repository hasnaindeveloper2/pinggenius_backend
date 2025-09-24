from gmail_service import (
    get_gmail_service,
    move_to_trash,
    send_email_reply,
    marked_as_read,
)
from agent_core import run_email_agent
from models.emails import save_email
from models.hard_email import save_hard_email_to_db
from fastapi import logger
import asyncio


async def process_email(email, user_id):
    try:
        if not email or "id" not in email:
            raise ValueError("Invalid email payload")

        service = await get_gmail_service(user_id)
        input_text = f"Subject: {email['subject']}\nFrom: {email['sender']}\n\nBody: {email.get('snippet','')}"

        result = await asyncio.wait_for(run_email_agent(input_text), timeout=30)
        if not isinstance(result, str):
            raise RuntimeError("Agent returned non-string")

        decision = result.lower().strip()
        if decision == "junk":
            await move_to_trash(service, email["id"])
            return {"status": "junk"}

        if decision.startswith("easy:"):
            reply = decision.split("easy:", 1)[1].strip()
            to_email = email["sender"].split("<")[-1].replace(">", "").strip()
            await send_email_reply(service, to_email, email["subject"], reply)
            await marked_as_read(service, email["id"])
            await save_email(user_id, email["subject"], to_email, reply, "easy")
            return {"status": "easy", "reply": reply}

        await save_hard_email_to_db(email, user_id)
        return {"status": "hard"}

    except Exception as e:
        logger.exception(
            "process_email failed for user %s email %s", user_id, email.get("id")
        )
        return {"status": "error", "message": str(e)}
