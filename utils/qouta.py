from datetime import datetime
from pymongo import ReturnDocument
from bson import ObjectId
from config.limit import PLAN_LIMITS  # map your limits into python
from models.users import users


async def ensure_usage_reset(user_doc):
    # reset usage if lastReset is in previous month
    last = user_doc.get("usage", {}).get("lastReset")
    if not last:
        return
    now = datetime.utcnow()
    if last.year != now.year or last.month != now.month:
        await users.update_one(
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
    user_obj_id = ObjectId(user_id)
    user = await users.find_one({"_id": user_obj_id})
    if not user:
        return False

    await ensure_usage_reset(user)

    # Ensure usage dict exists
    usage = user.get("usage", {})
    if resource not in usage:
        # Initialize missing field to 0
        await users.update_one(
            {"_id": user_obj_id},
            {"$set": {f"usage.{resource}": 0, "usage.lastReset": datetime.utcnow()}},
        )
        usage[resource] = 0

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

    # treat None as unlimited
    if allowed is None:
        await users.update_one(
            {"_id": user_obj_id}, {"$inc": {f"usage.{resource}": amount}}
        )
        return True

    # fix: use $lt instead of $lte - amount
    filter_q = {"_id": user_obj_id, f"usage.{resource}": {"$lt": allowed}}
    update_q = {"$inc": {f"usage.{resource}": amount}}

    res = await users.find_one_and_update(
        filter_q, update_q, return_document=ReturnDocument.AFTER
    )

    return res is not None

