from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.sequence import save_sequence, sequences
from models.contact import get_contact_by_id, update_contact_status
from gmail_service import get_gmail_service, send_email_reply
from utils.extract_subject import extract_subject
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import pytz

router = APIRouter(tags=["Sequence"])
scheduler = AsyncIOScheduler(timezone=pytz.UTC)
scheduler.start()

# ---------- Schema ----------
class SequenceRequest(BaseModel):
    contact_id: str
    email_body: str


async def send_scheduled_email(contact_id: str, email_body: str):
    """Helper for scheduled jobs"""
    service = get_gmail_service()
    contact = await get_contact_by_id(contact_id)
    if not contact:
        return

    to_email = contact.get("email")
    subject = extract_subject(email_body)

    send_email_reply(service, to_email, subject, email_body)

    # Mark sequence step as sent
    await sequences.update_one(
        {"contact_id": contact_id, "email_body": email_body},
        {"$set": {"sent_at": datetime.utcnow(), "status": "sent"}}
    )


@router.post("/start-sequence")
async def start_sequence(data: SequenceRequest):
    try:
        service = get_gmail_service()
        contact = await get_contact_by_id(data.contact_id)

        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        if not contact.get("email"):
            raise HTTPException(status_code=400, detail="Contact email is missing")

        to_email = contact["email"]
        subject = extract_subject(data.email_body)

        # Send first email immediately
        send_email_reply(service, to_email, subject, data.email_body)

        # Update status
        await update_contact_status(contact_id=data.contact_id, status="inSequence")

        # Save this step in DB
        await save_sequence({
            "contact_id": data.contact_id,
            "email_body": data.email_body,
            "step": 1,
            "sent_at": datetime.utcnow(),
            "next_send_at": None,
            "status": "sent"
        })

        # -------- Schedule Remaining Steps --------
        sequence_steps = await sequences.find({
            "contact_id": data.contact_id,
            "status": "pending"
        }).to_list(None)

        for step in sequence_steps:
            run_date = step["next_send_at"]
            scheduler.add_job(
                send_scheduled_email,
                "date",
                run_date=run_date,
                args=[data.contact_id, step["email_body"]],
                id=f"seq_{data.contact_id}_{step['step']}"
            )

        return {"message": "Sequence started. First email sent, follow-ups scheduled."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
