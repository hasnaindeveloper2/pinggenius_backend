from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from gmail_service import (
    get_gmail_service,
    move_to_trash,
    send_email_reply,
    marked_as_read,
)
from agent_core import run_email_agent
from models.hard_email import save_hard_email_to_db

router = APIRouter()


class Email(BaseModel):
    subject: str
    sender: str
    snippet: str
    id: str
    user_id: str


@router.post("/analyze")
async def analyze_email(email: Email):
    try:
        input_text = f"Subject: {email.subject}\nFrom: {email.sender}\n\n Body: {email.snippet}\n\n id: {email.user_id}"

        result = await run_email_agent(input_text)
        decision = result.strip().lower()
        print("RESULT:", result)
        print("DECISION:", decision)

        service = get_gmail_service()

        email_dict = {
            "subject": email.subject,
            "sender": email.sender,
            "snippet": email.snippet,
            "id": email.id,
        }

        if decision == "junk":
            move_to_trash(service, email.id)
            return {"status": "junk", "message": "Email trashed."}

        elif decision.startswith("easy:"):
            reply = decision.replace("easy:", "").strip()
            to_email = email.sender.split("<")[-1].replace(">", "").strip()
            send_email_reply(service, to_email, email.subject, reply)
            marked_as_read(service, email.id)
            return {
                "status": "easy",
                "reply": reply,
                "message": "auto reply sent!✅ email marked as read!",
            }

        else:
            await save_hard_email_to_db(email_dict)
            return {"status": "hard", "message": "Email marked as hard and stored."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
