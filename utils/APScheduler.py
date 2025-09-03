from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gmail_service import fetch_recent_emails, get_gmail_service
from utils.email_processor import process_email
import asyncio

scheduler = AsyncIOScheduler()
scheduler.start()


# ✅ Helper: actual email processing
async def _process_emails(user_id: str):
    try:
        print(f"🔍 Checking new emails for user {user_id}...")
        service = get_gmail_service()  # per-user service
        emails = await fetch_recent_emails(service, max_results=5)

        if not emails:
            print(f"No new emails yet for {user_id}")
            return

        for email in emails:
            result = await process_email(email, user_id)
            print(f"[User {user_id}] {result}")
            print(email)

    except Exception as e:
        print(f"❌ Error in job for {user_id}: {e}")


# ✅ Wrapper: this is the job scheduler will call
async def scheduled_email_check(user_id: str):
    asyncio.create_task(_process_emails(user_id))


# ✅ Start job for a user
def start_user_scheduler(user_id: str, interval_seconds):
    job_id = f"user_{user_id}"
    # Prevent duplicate job for same user
    if scheduler.get_job(job_id):
        print(f"⚠️ Job already running for user {user_id}")
        return

    scheduler.add_job(
        scheduled_email_check,
        "interval",
        seconds=interval_seconds,
        args=[user_id],
        id=job_id,
        max_instances=1,
    )
    print(f"✅ Started scheduler for {user_id} every {interval_seconds}s")


# ✅ Stop job for a user
def stop_user_scheduler(user_id: str):
    job_id = f"user_{user_id}"
    job = scheduler.get_job(job_id)
    if job:
        scheduler.remove_job(job_id)
        print(f"🛑 Stopped scheduler for {user_id}")
    else:
        print(f"⚠️ No active job found for {user_id}")
