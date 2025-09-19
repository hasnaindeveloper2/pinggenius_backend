from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from motor.motor_asyncio import AsyncIOMotorClient
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
from bson import ObjectId
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


async def get_gmail_service(user_id: str):
    # Fetch user refresh token from DB
    id = ObjectId(user_id)
    user = await users.find_one({"_id": id})

    if not user:
        raise Exception(f"User {user_id} not found in DB")

    refresh_token = user.get("refresh_token")
    if not refresh_token:
        raise Exception("No refresh token found for this user")

    creds = Credentials(
        None,  # no access token saved
        refresh_token=refresh_token,
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
async def fetch_recent_emails(service, user_id: str, max_results: int):
    """
    Fetch the most recent emails for a specific tenant/user, avoiding duplicates
    using a per-user Gmail historyId stored in MongoDB.
    """
    try:
        # Get last stored historyId for this user
        last_meta = await meta_collection.find_one({"_id": f"gmail_tracker_{user_id}"})
        last_history_id = last_meta.get("last_history_id") if last_meta else None
        seen_ids = set(last_meta.get("processed_ids", [])) if last_meta else set()

        results = (
            service.users()
            .messages()
            .list(userId="me", maxResults=max_results, q="category:primary")
            .execute()
        )

        messages = results.get("messages", [])
        emails = []
        new_ids = set()
        latest_history_id = last_history_id or 0  # default to 0 if None

        for msg in messages:
            if msg["id"] in seen_ids:
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

            # If we have a last_history_id, skip older messages
            if last_history_id is not None and history_id <= last_history_id:
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

            # Add to seen IDs and track latest historyId
            new_ids.add(msg["id"])
            latest_history_id = max(latest_history_id, history_id)

        # Update Mongo with latest historyId and processed IDs per user
        if new_ids:
            await meta_collection.update_one(
                {"_id": f"gmail_tracker_{user_id}"},
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
