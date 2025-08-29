from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from motor.motor_asyncio import AsyncIOMotorClient
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("❌ MONGO_URL is not set! Please check your env variables.")

client = AsyncIOMotorClient(MONGO_URL)
db = client["pinggenius"]
print("Mongo URL: ", MONGO_URL)
print(db.list_collection_names())
meta_collection = db["gmail_meta"]


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


def get_gmail_service():
    creds = None

    # Use JSON instead of pickle
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        # Save as JSON, not pickle
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


from motor.motor_asyncio import AsyncIOMotorClient

# Mongo connection


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

        # Fetch messages (primary inbox only)
        results = (
            service.users()
            .messages()
            .list(userId="me", maxResults=max_results, q="category:primary")
            .execute()
        )

        messages = results.get("messages", [])
        emails = []
        latest_history_id = last_history_id  # keep track of highest seen

        for msg in messages:
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

            # Skip already processed emails
            if last_history_id and history_id <= int(last_history_id):
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

            # Track latest historyId
            if not latest_history_id or history_id > int(latest_history_id):
                latest_history_id = history_id

        # Update Mongo with latest historyId (only if we found new emails)
        if latest_history_id and latest_history_id != last_history_id:
            await meta_collection.update_one(
                {"_id": "gmail_tracker"},
                {"$set": {"last_history_id": latest_history_id}},
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
