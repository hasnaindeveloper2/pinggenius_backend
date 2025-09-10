from motor.motor_asyncio import AsyncIOMotorClient
import os

MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise RuntimeError("❌ MONGO_URL is not set! Please check your env variables.")

client = AsyncIOMotorClient(MONGO_URL)
db = client["test"]
