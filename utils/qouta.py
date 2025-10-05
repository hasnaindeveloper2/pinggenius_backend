from datetime import datetime
from pymongo import ReturnDocument
from bson import ObjectId
from database.mongo import db
from config.limit import PLAN_LIMITS  # map your limits into python


async def ensure_usage_reset(user_doc):
    # reset usage if lastReset is in previous month
    last = user_doc.get("usage", {}).get("lastReset")
    if not last:
        return
    now = datetime.utcnow()
    if last.year != now.year or last.month != now.month:
        await db.users.update_one(
            {"_id": user_doc["_id"]},
            {
                "$set": {
                    "usage.emailAnalyses": 0,
                    "usage.autoReplies": 0,
                    "usage.sequencesCreated": 0,
                    "usage.contactsImported": 0,
                    "usage.lastReset": now,
                }
            },
        )


async def try_consume_quota(user_id: str, resource: str, amount: int = 1) -> bool:
    """
    Consume quota for a given resource.
    resource: one of ['emailAnalyses', 'autoReplies', 'sequencesCreated', 'contactsImported']
    Returns True if consumption succeeded, else False (limit reached).
    """
    user_obj_id = ObjectId(user_id)
    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        return False

    # reset usage if new month
    await ensure_usage_reset(user)

    # select plan limits based on isProUser boolean
    plan = "pro" if user.get("isProUser") else "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])

    limit_key_map = {
        "emailAnalyses": "emailAnalysesPerMonth",
        "autoReplies": "autoRepliesPerMonth",
        "sequencesCreated": "sequences",
        "contactsImported": "contacts",
    }
    limit_key = limit_key_map[resource]
    allowed = limits.get(limit_key)

    # if no limit, treat as unlimited
    if allowed is None:
        await db.users.update_one(
            {"_id": user_obj_id}, {"$inc": {f"usage.{resource}": amount}}
        )
        return True

    # atomic check + increment
    filter_q = {"_id": user_obj_id, f"usage.{resource}": {"$lte": allowed - amount}}
    update_q = {"$inc": {f"usage.{resource}": amount}}
    res = await db.users.find_one_and_update(
        filter_q, update_q, return_document=ReturnDocument.AFTER
    )
    return res is not None
