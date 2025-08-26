from gmail_service import (
    get_gmail_service,
    move_to_trash,
    send_email_reply,
    marked_as_read,
)
from agent_core import run_email_agent
from models.hard_email import save_hard_email_to_db


async def process_email(email):
    """Process a single email dict {subject, sender, snippet, id, user_id}."""
    service = get_gmail_service()
    input_text = f"Subject: {email['subject']}\nFrom: {email['sender']}\n\n Body: {email['snippet']}\n\n id: 689210e73ab6579e73ad5704"

    result = await run_email_agent(input_text)
    decision = result.lower()

    if decision == "junk":
        move_to_trash(service, email["id"])
        return {"status": "junk", "message": "Email trashed."}

    elif decision.startswith("easy:"):
        reply = decision.replace("easy:", "").strip()
        to_email = email["sender"].split("<")[-1].replace(">", "").strip()
        send_email_reply(service, to_email, email["subject"], reply.upper())
        marked_as_read(service, email["id"])
        return {
            "status": "easy",
            "reply": reply,
            "message": "Auto reply sent ✅ Email marked as read!",
        }

    else:
        await save_hard_email_to_db(email)
        return {"status": "hard", "message": "Email marked as hard and stored."}
