from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gmail_service import (
    fetch_recent_emails,
    get_gmail_service,
)  # You'll need a function that fetches unread emails
from utils.email_processor import process_email
import asyncio

scheduler = AsyncIOScheduler()


async def scheduled_email_check():
    print("🔍 Checking for new emails...")
    asyncio.create_task(_process_emails())

async def _process_emails():
    try:
        service = get_gmail_service()
        emails = await fetch_recent_emails(service, max_results=2)
        if not emails:
            print("No! new emails yet!")
        for email in emails:
            result = await process_email(email)
            print(result)
            print(email)
    except Exception as e:
        print(f"❌ Error in job: {e}")



def start_scheduler():
    scheduler.add_job(scheduled_email_check, "interval", seconds=30)
    scheduler.start()
