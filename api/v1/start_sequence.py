from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.sequence import save_sequence, sequences
from models.contact import get_contact_by_id, update_contact_status, contacts
from gmail_service import get_gmail_service, send_email_reply
from utils.extract_subject import extract_subject
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from bson import ObjectId
from utils.scheduler import scheduler

router = APIRouter(tags=["Sequence"])


# ---------- Schema ----------
class SequenceRequest(BaseModel):
    user_id: str
    contact_id: str
    email_body: str


async def send_scheduled_email(contact_id: str, email_body: str, user_id: str):
    """Helper for scheduled jobs"""
    service = await get_gmail_service(user_id)
    contact = await get_contact_by_id(contact_id)
    if not contact:
        return

    to_email = contact.get("email")
    subject = extract_subject(email_body)

    if email_body.startswith("Subject:"):
        # split only on first newline
        _, body = email_body.split("\n", 1)
        email_body = body.strip()

    send_email_reply(service, to_email, subject, email_body)

    # Mark sequence step as sent
    await sequences.update_one(
        {"contact_id": contact_id, "email_body": email_body},
        {"$set": {"sent_at": datetime.utcnow(), "status": "sent"}},
    )


@router.post("/start-sequence")
async def start_sequence(data: SequenceRequest):
    try:
        service = await get_gmail_service(data.user_id)
        contact_id = ObjectId(data.contact_id)
        contact = await get_contact_by_id(contact_id)

        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        if not contact.get("email"):
            raise HTTPException(status_code=400, detail="Contact email is missing")

        to_email = contact["email"]
        subject = extract_subject(data.email_body)

        if data.email_body.startswith("Subject:"):
            # split only on first newline
            _, body = data.email_body.split("\n", 1)
            data.email_body = body.strip()

        # Send first email immediately
        send_email_reply(service, to_email, subject, data.email_body)

        # Update status
        await update_contact_status(contact_id=data.contact_id, status="inSequence")

        # Save this step in DB
        await save_sequence(
            {
                "contact_id": data.contact_id,
                "email_body": data.email_body,
                "step": 1,
                "sent_at": datetime.utcnow(),
                "next_send_at": None,
                "status": "sent",
            }
        )

        # -------- Schedule Remaining Steps --------
        sequence_steps = await sequences.find(
            {"contact_id": data.contact_id, "status": "pending"}
        ).to_list(None)

        for step in sequence_steps:
            run_date = step["next_send_at"]
            scheduler.add_job(
                send_scheduled_email,
                "date",
                run_date=run_date,
                args=[data.contact_id, step["email_body"]],
                id=f"seq_{data.contact_id}_{step['step']}",
            )
            print(f"Scheduled follow-up email for {step['step']} on {run_date}")

        return {
            "message": f"Sequence started. First email sent, follow-ups scheduled for {step['step']} on {run_date}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
