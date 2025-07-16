from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from utils.email_sender import send_email
from models.sequence import save_sequence
from models.contact import get_contact_by_id, update_contact_status

router = APIRouter(tags=["Sequence"])


# ---------- Schema ----------
class SequenceRequest(BaseModel):
    contact_id: str
    email_body: str


@router.post("/start-sequence")
async def start_sequence(data: SequenceRequest):
    try:
        contact = await get_contact_by_id(data.contact_id)

        email = contact.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Contact email is missing")

        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")

        await send_email(
            to=contact["email"], subject="👋 Just Reaching Out", body=data.email_body
        )
        await update_contact_status(contact_id=data.contact_id, status="replied")
        await save_sequence(contact_id=data.contact_id, email_body=data.email_body)

        return {"message": "Sequence started and email sent."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
