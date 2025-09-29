from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from models.sequence import save_sequence
from models.contact import get_contact_by_id
from utils.followup_generator import generate_followups
from models.contact import contacts
from bson import ObjectId

router = APIRouter(tags=["Sequence"])


class GenerateSequenceRequest(BaseModel):
    user_id: str
    contact_id: str
    email_body: str
    schedule_days: list[int]  # e.g. [1, 3, 7]


@router.post("/generate-sequence")
async def generate_sequence(data: GenerateSequenceRequest):
    try:
        contact = await get_contact_by_id(data.contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        # ---- Using agent to generate follow-ups ----
        followups = await generate_followups(
            contact, data.email_body, num=len(data.schedule_days)
        )

        if not followups:
            raise HTTPException(status_code=500, detail="Failed to generate follow-ups")

        sequence_docs = []
        now = datetime.utcnow()

        for idx, (day, followup_email) in enumerate(
            zip(data.schedule_days, followups), start=2
        ):
            doc = {
                "user_id": data.user_id,
                "contact_id": data.contact_id,
                "email_body": followup_email,
                "step": idx,
                "sent_at": None,
                "next_send_at": now + timedelta(days=day),
                "status": "pending",
                "created_at": now,
            }
            await save_sequence(dict(doc))
            await contacts.find_one_and_update(
                {"_id": ObjectId(data.contact_id)}, {"$set": {"status": "inSequence"}}
            )
            sequence_docs.append(doc)

        return {
            "message": f"Sequence with {len(sequence_docs)} steps generated.",
            "steps": sequence_docs,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
