from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client["pinggenius"]
sequences = db["sequences"]


async def save_sequence(contact_id: str, email_body: str):
    sequence_doc = {
        "contact_id": contact_id,
        "email_body": email_body,
        "step": 1,
        "sent_at": datetime.utcnow(),
        "next_send_at": datetime.utcnow() + timedelta(days=3),
        "status": "sent",
    }
    await sequences.insert_one(sequence_doc)
