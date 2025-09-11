from gmail_service import (
    get_gmail_service,
    move_to_trash,
    send_email_reply,
    marked_as_read,
)
from agent_core import run_email_agent
from models.emails import save_email
from models.hard_email import save_hard_email_to_db


async def process_email(email, user_id):
    """Process a single email dict {subject, sender, snippet, user_id}."""
    service = await get_gmail_service(user_id)
    input_text = f"Subject: {email['subject']}\nFrom: {email['sender']}\n\n Body: {email['snippet']}\n\n id: {user_id}"

    result = await run_email_agent(input_text)
    if not result or not isinstance(result, str):
        print("❌ Invalid agent response")
    decision = result.lower()

    if decision == "junk":
        move_to_trash(service, email["id"])
        return {"status": "junk", "message": "Email trashed."}

    elif decision.startswith("easy:"):
        reply = decision.replace("easy:", "").strip()
        to_email = email["sender"].split("<")[-1].replace(">", "").strip()
        send_email_reply(service, to_email, email["subject"], reply)
        marked_as_read(service, email["id"])
        await save_email(user_id, email["subject"], to_email, reply, "easy")
        return {
            "status": "easy",
            "reply": reply,
            "message": "Auto Reply Sent ✅ Email Marked as Read, Email stored!",
        }

    else:
        await save_hard_email_to_db(email)
        return {"status": "hard", "message": "Email marked as hard and stored."}
