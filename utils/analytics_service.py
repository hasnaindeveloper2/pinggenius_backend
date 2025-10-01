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
    
async def update_sequence_progress(user_id: str, field: str, value: int = 1):
    await analytics_overview.update_one(
        {"userId": user_id},
        {
            "$inc": {f"charts.sequenceProgress.{field}": value},
            "$set": {"lastUpdated": datetime.utcnow()},
        },
        upsert=True
    )



async def update_email_volume(user_id: str, count: int = 1):
    today = datetime.utcnow().strftime("%Y-%m-%d")

    await analytics_overview.update_one(
        {"userId": user_id, "charts.emailVolume.date": today},
        {
            "$inc": {"charts.emailVolume.$.count": count},
            "$set": {"lastUpdated": datetime.utcnow()},
        },
        upsert=False,
    )

    # If no entry for today exists → push new one
    await analytics_overview.update_one(
        {"userId": user_id, "charts.emailVolume.date": {"$ne": today}},
        {
            "$push": {"charts.emailVolume": {"date": today, "count": count}},
            "$set": {"lastUpdated": datetime.utcnow()},
        },
        upsert=True,
    )