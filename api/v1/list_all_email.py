from fastapi import APIRouter, HTTPException
from models.emails import list_all_emails

router = APIRouter(tags=["Emails"])


@router.get("/list-all-emails")
async def list_all_emails(user_id: str):
    try:
        emails = await list_all_emails(user_id)

        if not emails:
            raise HTTPException(status_code=404, detail="No emails found")

        return emails
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
