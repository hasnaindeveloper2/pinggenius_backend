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
    service = get_gmail_service()
    emails = fetch_recent_emails(
        service, max_results=5
    )  # Returns list of {subject, sender, snippet, id, user_id}
    for email in emails:
        result = await process_email(email)
        print(result)


def start_scheduler():
    scheduler.add_job(scheduled_email_check, "interval", minutes=1)
    scheduler.start()
