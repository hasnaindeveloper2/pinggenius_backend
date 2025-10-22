from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.sequence import save_sequence, sequences
from models.contact import get_contact_by_id
from gmail_service import get_gmail_service, send_email_reply
from utils.extract_subject import extract_subject
from models.sequence_job import sequence_job
from models.users import users
from datetime import datetime
from bson import ObjectId
from utils.analytics_service import update_analytics
from utils.scheduler import scheduler
from utils.send_emails_via_smtp import send_email_smtp
from utils.analytics_service import update_sequence_progress

router = APIRouter(tags=["Sequence"])


# ---------- Schema ----------
class SequenceRequest(BaseModel):
    user_id: str
    contact_id: str
    email_body: str


async def send_scheduled_email(contact_id: str, email_body: str, user_id: str):
    """Helper for scheduled jobs"""
    contact = await get_contact_by_id(contact_id)
    if not contact:
        return

    to_email = contact.get("email")
    subject = extract_subject(email_body)

    if email_body.startswith("Subject:"):
        # split only on first newline
        _, body = email_body.split("\n", 1)
        email_body = body.strip()

    # TODO: do this later
    # send_email_reply(service, to_email, subject, email_body)
    send_email_smtp(to_email, subject, email_body)

    # ✅ Update analytics
    await update_analytics(user_id, "autoReplied", 1)
    # ✅ Update sequence progress
    await update_sequence_progress(user_id, "stepsCompleted", 1)

    # Mark sequence step as sent
    await sequences.update_one(
        {"contact_id": contact_id, "email_body": email_body},
        {"$set": {"sent_at": datetime.utcnow(), "status": "sent"}},
    )


@router.post("/start-sequence")
async def start_sequence(data: SequenceRequest):
    try:
        # service = await get_gmail_service(data.user_id)
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

        # TODO: do this later
        # send_email_reply(service, to_email, subject, email_body)
        send_email_smtp(to_email, subject, data.email_body)

        # ✅ Update analytics
        await update_analytics(data.user_id, "autoReplied", 1)

        # Save this step in DB
        await save_sequence(
            {
                "user_id": data.user_id,
                "contact_id": data.contact_id,
                "contact_name": contact["name"],
                "email_body": data.email_body,
                "step": 1,
                "sent_at": datetime.utcnow(),
                "next_send_at": None,
                "status": "sent",
                "created_at": datetime.utcnow(),
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
                args=[data.contact_id, step["email_body"], data.user_id],
                id=f"seq_{data.contact_id}_{step['step']}",
            )
            # ✅ Update analytics
            await update_sequence_progress(data.user_id, "stepsPlanned", 1)
        await sequence_job.update_one(
            {"user_id": ObjectId(data.user_id), "contact_id": contact_id},
            {"$set": {"is_sequence_running": True}},
            upsert=True,
        )
        print(f"Scheduled follow-up email for {step['step']} on {run_date}")

        return {
            "message": f"Sequence started. First email sent, follow-ups scheduled for {step['step']} on {run_date}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
