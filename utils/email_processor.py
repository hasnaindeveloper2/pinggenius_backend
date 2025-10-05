from gmail_service import (
    get_gmail_service,
    move_to_trash,
    send_email_reply,
    marked_as_read,
)
from agent_core import run_email_agent
from models.emails import save_email
from models.hard_email import save_hard_email_to_db
from utils.analytics_service import update_analytics
import logging
import asyncio
from utils.analytics_service import update_email_volume
from utils.regex_junk_detection import is_junk_email
from utils.qouta import try_consume_quota

logger = logging.getLogger(__name__)


async def process_email(email, user_id):
    try:
        if not email or "id" not in email:
            raise ValueError("Invalid email payload")

        service = await get_gmail_service(user_id)
        input_text = f"Subject: {email['subject']}\nFrom: {email['sender']}\n\nBody: {email.get('snippet','')} user_id:{user_id}"

        
        consumed = await try_consume_quota(user_id, "emailAnalyses", 1)
        if not consumed:
        # quota exhausted: store email, mark throttled, notify the user via UI later
            return {"status": "quota_exceeded"}
        
        # ✅ Junk detection (regex)
        if is_junk_email(input_text):
            move_to_trash(service, email["id"])
            await save_email(user_id, email["subject"], email["sender"], "", "junk")
            await update_analytics(user_id, "totalEmails", 1)
            await update_email_volume(user_id, 1)
            await update_analytics(user_id, "spamDetected", 1)

            print("Email marked as junk and moved to trash and stored ✅")
            return {"status": "junk"}
        
        

        result = await run_email_agent(input_text)
        if not isinstance(result, str):
            print("⚠️ Agent returned:", repr(result))
            raise RuntimeError("Agent returned non-string")

        decision = result.lower().strip()

        # Always increment total emails count
        await update_analytics(user_id, "totalEmails", 1)
        await update_email_volume(user_id, 1)

        # fallback if agent junk detection triggers
        if decision.startswith("junk"):
            return {"status": "junk"}

        if decision.startswith("easy:"):
            reply = decision.split("easy:", 1)[1].strip()
            # .split("<")[-1].replace(">", "").strip()
            # sending raw email
            to_email = email["sender"]
            send_email_reply(service, to_email, email["subject"], reply.title())
            marked_as_read(service, email["id"])
            await save_email(user_id, email["subject"], to_email, reply.title(), "easy")

            # ✅ Update analytics
            await update_analytics(user_id, "autoReplied", 1)

            print("Easy email replied and marked as read and stored ✅")
            return {"status": "easy", "reply": reply.title()}

        await save_hard_email_to_db(email, user_id)

        # ✅ Update analytics
        await update_analytics(user_id, "hardEmails", 1)

        print("Email marked as hard and stored for manual review ✅")
        return {"status": "hard"}

    except Exception as e:
        logger.exception(
            "process_email failed for user %s email %s", user_id, email.get("id")
        )
        return {"status": "error", "message": str(e)}
