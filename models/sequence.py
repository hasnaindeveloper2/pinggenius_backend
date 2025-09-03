from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client["pinggenius"]
sequences = db["sequences"]


async def save_sequence(sequence_doc):
    if not sequence_doc.get("contact_id") or not sequence_doc.get("email_body"):
        return
    await sequences.insert_one(sequence_doc)
    
async def get_sequences(contact_id):
    if not contact_id:
        return "Sequence not found"
    return await sequences.find({"contact_id": contact_id}).to_list(length=None)