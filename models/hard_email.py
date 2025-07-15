from datetime import datetime
from utils.serializer import serialize_doc
from database.mongo import hard_emails

async def save_hard_email_to_db(email_data: dict):
    email_data["type"] = "inbound"
    email_data["source"] = "gmail"
    email_data["status"] = "hard"
    email_data["created_at"] = datetime.utcnow()
    await hard_emails.insert_one(email_data)


async def get_all_hard_emails():
    emails = await hard_emails.find({"status": "hard"}).to_list(length=100)
    return [serialize_doc(email) for email in emails]