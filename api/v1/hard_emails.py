from fastapi import APIRouter, HTTPException
from models.hard_email import get_all_hard_emails

router = APIRouter(tags=["Hard Emails"])


@router.get("/list-hard-emails")
async def list_hard_emails(user_id: str):
    try:
        emails = await get_all_hard_emails(user_id)
        return emails
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
