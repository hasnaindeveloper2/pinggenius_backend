from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime, timedelta
from models.sequence import save_sequence
from models.contact import get_contact_by_id
from utils.followup_generator import generate_followups
from models.contact import contacts
from bson import ObjectId
from utils.qouta import try_consume_quota


router = APIRouter(tags=["Sequence"])


class GenerateSequenceRequest(BaseModel):
    user_id: str
    contact_id: str
    email_body: str
    schedule_days: list[int]  # e.g. 1 day after, 2 days after so on...


@router.post("/generate-sequence")
async def generate_sequence(data: GenerateSequenceRequest):
    try:
        contact = await get_contact_by_id(data.contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

            # ✅ Quota check before generating sequences
        # We only consume *1* sequence per "sequence flow" creation, not per step
        consumed = await try_consume_quota(data.user_id, "sequencesCreated", 1)
        if not consumed:
            raise HTTPException(
                status_code=403,
                detail="Sequence limit exceeded. Upgrade to Pro to create more outreach sequences.",
            )

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
                "contact_name": contact["name"],
                "email_body": followup_email,
                "step": idx,
                "sent_at": None,
                "next_send_at": now + timedelta(days=day),
                "status": "pending",
                "created_at": now,
            }
            # before creating sequence steps (count planned steps)
            # user_allowed = PLAN_LIMITS[plan]['sequences'] - user['usage']['sequencesCreated']
            # if number_of_steps > user_allowed:
            #     raise HTTPException(403, detail="Sequence limit exceeded. Upgrade to Pro.")
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
