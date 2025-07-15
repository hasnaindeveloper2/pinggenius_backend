from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client["pinggenius"]
contacts = db["contacts"]


async def save_contact_to_db(contact_data: dict):
    contact_data["created_at"] = datetime.utcnow()
    contact_data["status"] = "pending"
    contact_data["source"] = "linkedin"
    await contacts.insert_one(contact_data)


async def get_contact_by_id(contact_id: str):
    try:
        object_id = ObjectId(contact_id)
    except InvalidId:
        return None  # Or raise 400

    contact = await contacts.find_one({"_id": object_id})
    return contact
