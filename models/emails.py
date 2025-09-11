from database.mongo import db
from datetime import datetime


async def save_email(
    user_id: str, subject: str, to_email: str, reply: str, status: str
):
    emails = db["emails"]
    email_data = {
        "user_id": user_id,
        "subject": subject,
        "to_email": to_email,
        "reply": reply,
        "status": status,
        "created_at": datetime.utcnow(),
    }
    await emails.insert_one(email_data)
