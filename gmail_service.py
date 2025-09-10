from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from motor.motor_asyncio import AsyncIOMotorClient
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
from database.mongo import db
from models.users import users

load_dotenv()

meta_collection = db["gmail_meta"]

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_gmail_service(user_id: str):
    # Fetch user refresh token from DB
    user = users.find_one({"_id": user_id})
    if not user or "refresh_token" not in user:
        raise Exception("No refresh token found for this user")

    creds = Credentials(
        None,  # no access token saved
        refresh_token=user["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )

    # Always refresh access token
    creds.refresh(Request())

    # Return Gmail service
    return build("gmail", "v1", credentials=creds)


# ---------- Fetch Latest Email using Gmail API ----------
async def fetch_recent_emails(service, max_results):
    """
    Fetch the most recent emails from Gmail, avoiding duplicates
    using Gmail's historyId stored in MongoDB.
    """
    try:
        # Get last stored historyId
        last_meta = await meta_collection.find_one({"_id": "gmail_tracker"})
        last_history_id = last_meta.get("last_history_id") if last_meta else None
        seen_ids = set(last_meta.get("processed_ids", [])) if last_meta else set()

        # Fetch messages (primary inbox only)
        results = (
            service.users()
            .messages()
            .list(userId="me", maxResults=max_results, q="category:primary")
            .execute()
        )

        messages = results.get("messages", [])
        emails = []
        new_ids = set()
        latest_history_id = last_history_id  # keep track of highest seen

        for msg in messages:
            if msg["id"] in seen_ids:  # 👈 skip already processed
                continue

            msg_data = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["Subject", "From"],
                )
                .execute()
            )

            headers = {
                h["name"]: h["value"]
                for h in msg_data.get("payload", {}).get("headers", [])
            }

            history_id = int(msg_data.get("historyId", 0))

            # Skip old history
            if history_id <= last_history_id:
                continue

            emails.append(
                {
                    "id": msg["id"],
                    "subject": headers.get("Subject", ""),
                    "sender": headers.get("From", ""),
                    "snippet": msg_data.get("snippet", ""),
                    "historyId": history_id,
                }
            )

            new_ids.add(msg["id"])
            latest_history_id = max(latest_history_id, history_id)

        # Update Mongo with latest historyId (only if we found new emails)
        if new_ids:
            await meta_collection.update_one(
                {"_id": "gmail_tracker"},
                {
                    "$set": {"last_history_id": latest_history_id},
                    "$addToSet": {"processed_ids": {"$each": list(new_ids)}},
                },
                upsert=True,
            )

        return emails

    except Exception as e:
        raise RuntimeError(f"Error fetching recent emails: {e}")


def move_to_trash(service, message_id):
    service.users().messages().trash(userId="me", id=message_id).execute()


def send_email_reply(service, to_email, subject, message_body):
    """Send an email reply using Gmail API."""
    message = MIMEText(message_body)
    message["to"] = to_email
    message["subject"] = (
        "Re: " + subject
    )  # why Re? because it's a reply to the original email

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw_message}

    sent_message = service.users().messages().send(userId="me", body=body).execute()
    return sent_message


def marked_as_read(service, message_id):
    """Mark an email as read."""
    body = {"removeLabelIds": ["UNREAD"]}
    service.users().messages().modify(userId="me", id=message_id, body=body).execute()


def get_reciever_name(message):
    return message["sender"].split("<")[-1].replace(">", "").strip()
