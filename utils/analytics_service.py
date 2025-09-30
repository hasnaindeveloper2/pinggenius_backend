from models.analytics_overview import analytics_overview
from datetime import datetime

async def update_analytics(user_id: str, field: str, value: int = 1):
    await analytics_overview.update_one(
        {"userId": user_id},
        {
            "$inc": {f"overview.{field}": value},
            "$set": {"lastUpdated": datetime.utcnow()},
        },
        upsert=True
    )
