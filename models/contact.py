from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
from utils.serializer import serialize_doc
from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client["pinggenius"]
contacts = db["contacts"]


# -------- Save contact to DB --------
async def save_contact_to_db(contact_data: dict):
    contact_data["created_at"] = datetime.utcnow()
    contact_data["status"] = "pending"
    contact_data["source"] = "linkedin"
    await contacts.insert_one(contact_data)


# -------- Get contact by ID --------
async def get_contact_by_id(contact_id):
    try:
        object_id = ObjectId(contact_id)
    except InvalidId:
        return None  # Or raise 400

    contact = await contacts.find_one({"_id": object_id})
    return contact


# -------- Get all contacts --------
async def get_all_contacts():
    contacts_list = await contacts.find({}).to_list(100)
    return [serialize_doc(c) for c in contacts_list]

# ------- Update the status --------
async def update_contact_status(contact_id: str, status: str):
    result = await contacts.update_one(
        {"_id": ObjectId(contact_id)},
        {"$set": {"status": status}}
    )
    return result.modified_count