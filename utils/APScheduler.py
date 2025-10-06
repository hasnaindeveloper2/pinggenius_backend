from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gmail_service import fetch_recent_emails, get_gmail_service
from utils.email_processor import process_email
from models.users import users
import asyncio
from models.jobs import jobs
from datetime import datetime, timedelta


scheduler = AsyncIOScheduler()
scheduler.start()


# Store job metadata to control auto-stop timers
ACTIVE_JOBS = {}


# ✅ Helper: actual email processing
async def _process_emails(user_id: str):
    try:
        print(f"🔍 Checking new emails for user {user_id}...")
        service = await get_gmail_service(user_id)  # per-user service
        emails = await fetch_recent_emails(service, user_id, max_results=3)

        if not emails:
            print(f"No new emails yet for {user_id}")
            return

        for email in emails:
            await process_email(email, user_id)
            if email.get("status").startswith("quota_exceeded"):
                stop_user_scheduler(user_id)
                await jobs.update_one(
                    {"user_id": user_id}, {"$set": {"is_sync_running": False}}
                )
                print(f"🛑 Stopped scheduler for {user_id} (qouta exceeded)")
                return {f"🛑 Stopped scheduler for {user_id} (qouta exceeded)"}

    except Exception as e:
        print(f"❌ Error in job for {user_id}: {e}")



# ✅ Wrapper: this is the job scheduler will call
async def scheduled_email_check(user_id: str):
    asyncio.create_task(_process_emails(user_id))



# ✅ Start job for a user
async def start_user_scheduler(user_id: str, interval_minutes: int):
    user = await users.find_one({"_id": user_id})
    if not user:
        print(f"⚠️ User not found for scheduler: {user_id}")
        return

    is_pro = user.get("isProUser")
    job_id = f"user_{user_id}"

    # Avoid duplicate jobs
    if scheduler.get_job(job_id):
        print(f"⚠️ Job already running for user {user_id}")
        return

    scheduler.add_job(
        scheduled_email_check,
        "interval",
        minutes=interval_minutes,
        args=[user_id],
        id=job_id,
        max_instances=1,
    )
    print(f"✅ Started scheduler for {user_id} every {interval_minutes} minutes")

    # Save job metadata
    ACTIVE_JOBS[user_id] = {
        "started_at": datetime.utcnow(),
        "auto_stop_after": timedelta(hours=3) if not is_pro else None,
    }



# ✅ Stop job for a user
def stop_user_scheduler(user_id: str):
    job_id = f"user_{user_id}"
    job = scheduler.get_job(job_id)
    if job:
        scheduler.remove_job(job_id)
        print(f"🛑 Stopped scheduler for {user_id}")
    else:
        print(f"⚠️ No active job found for {user_id}")


# ✅ Check and stop auto-expired jobs (for free users)
async def monitor_schedulers():
    while True:
        now = datetime.utcnow()
        for user_id, meta in list(ACTIVE_JOBS.items()):
            if (
                meta["auto_stop_after"]
                and now - meta["started_at"] > meta["auto_stop_after"]
            ):
                stop_user_scheduler(user_id)
                await jobs.update_one(
                    {"user_id": user_id}, {"$set": {"is_sync_running": False}}
                )
                del ACTIVE_JOBS[user_id]
                print(f"🛑 Auto-stopped free user scheduler after 3 hours → {user_id}")
        await asyncio.sleep(60)
