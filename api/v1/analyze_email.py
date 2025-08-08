from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from utils.email_processor import process_email

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
        result = await process_email(email.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
