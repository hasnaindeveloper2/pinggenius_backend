from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from models.hard_email import hard_emails
from gmail_service import get_gmail_service, send_email_reply
from utils.hard_email_replyer import generate_reply
import os
from motor.motor_asyncio import AsyncIOMotorClient
import re
from models.users import users

router = APIRouter(tags=["Hard Email"])


class RefineEmailRequest(BaseModel):
    email_id: str
    user_id: str
    refined_body: str


@router.post("/refine-hard-email")
async def resend_hard_email(req: RefineEmailRequest):
    # 1. Fetch hard email from DB
    email_doc = await hard_emails.find_one(
        {"_id": ObjectId(req.email_id), "status": "hard"}
    )
    if not email_doc:
        raise HTTPException(status_code=404, detail="Hard email not found")

    user_data = await users.find_one({"_id": ObjectId(req.user_id)})

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    sender = email_doc.get("sender")
    subject = email_doc.get("subject")
    # extract sender's name
    sender_name = sender.split("<")[0].strip()

    # 2. Drop refined email to AI Agent
    try:
        refined_reply = await generate_reply(
            req.refined_body, user_data["name"], sender_name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email agent failed: {str(e)}")

    # 3. Send auto reply immediately via Gmail API
    try:
        service = await get_gmail_service(req.user_id)

        match = re.search(r"<(.+?)>", sender)
        # Extract the email address
        clean_sender = match.group(1) if match else sender.strip()

        send_email_reply(service, clean_sender, subject, refined_reply)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gmail send failed: {str(e)}")

    # 4. Update DB status
    await hard_emails.update_one(
        {"_id": ObjectId(req.email_id)},
        {"$set": {"status": "replied", "snippet": refined_reply}},
    )

    return {"message": "Hard email successfully re-send", "reply": refined_reply}