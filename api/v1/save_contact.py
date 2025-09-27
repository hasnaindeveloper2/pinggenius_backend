from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from datetime import datetime
from models.contact import save_contact_to_db

router = APIRouter(tags=["Contacts"])


# -------- Schema --------
class Contact(BaseModel):
    user_id: str
    name: str
    linkedin_url: str
    role: str
    email: str
    website: str | None = None
    tone: str = "formal"
    selected_email: str


# -------- Route --------
@router.post("/save-contact")
async def save_contact(contact: Contact):
    try:
        contact_data = contact.dict()
        contact_data["created_at"] = datetime.utcnow()

        await save_contact_to_db(contact_data, user_id=contact.user_id)

        return {"status": "success", "message": "Contact saved!"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
