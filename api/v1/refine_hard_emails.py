from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from typing import Optional

from models.hard_email import hard_emails  # your Mongo collection
from gmail_service import get_gmail_service, send_email_reply  # Gmail API utility
from app.email_agent import generate_reply  # LLM email agent

router = APIRouter()


class RefineEmailRequest(BaseModel):
    email_id: str  # id of the hard email saved in db
    refined_body: str  # user updated/refined version of email


@router.post("/resend-hard-email")
async def resend_hard_email(req: RefineEmailRequest):
    # 1. Fetch hard email from DB
    email_doc = await hard_emails.find_one(
        {"_id": ObjectId(req.email_id), "status": "hard"}
    )
    if not email_doc:
        raise HTTPException(status_code=404, detail="Hard email not found")

    sender = email_doc["from"]
    subject = email_doc.get("subject", "Re: Your email")

    # 2. Drop refined email to AI Agent
    try:
        refined_reply = await generate_reply(req.refined_body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email agent failed: {str(e)}")

    # 3. Send auto reply immediately via Gmail API
    try:
        service = get_gmail_service()
        
        if "<" in sender and ">" in sender:
          clean_sender = sender.split("<")[1].replace(">", "").strip()
        else:
            # just in case the email is not in the format "Name <email>"
            clean_sender = sender.strip()

        await send_email_reply(service, clean_sender, subject, refined_reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gmail send failed: {str(e)}")

    # 4. Update DB status
    await hard_emails.update_one(
        {"_id": ObjectId(req.email_id)},
        {"$set": {"status": "replied", "snippet": refined_reply}},
    )

    return {"message": "Hard email successfully resent", "reply": refined_reply}
