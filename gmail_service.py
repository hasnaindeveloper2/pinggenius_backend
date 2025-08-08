from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email.mime.text import MIMEText
import os

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



def fetch_recent_emails(service, max_results: int):
    """
    Fetch the most recent unread emails from Gmail.
    
    Args:
        service: Authenticated Gmail API service instance.
        max_results (int): Maximum number of emails to fetch.
    
    Returns:
        list[dict]: List of emails with id, subject, sender, and snippet.
    """
    try:
        # Fetch unread messages only
        results = service.users().messages().list(
            userId="me",
            maxResults=max_results,
            q="is:unread"
        ).execute()

        messages = results.get("messages", [])
        emails = []

        for msg in messages:
            msg_data = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["Subject", "From"]
            ).execute()

            headers = {h["name"]: h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
            emails.append({
                "id": msg["id"],
                "subject": headers.get("Subject", ""),
                "sender": headers.get("From", ""),
                "snippet": msg_data.get("snippet", "")
            })

        return emails

    except Exception as e:
        # Log and raise in production
        raise RuntimeError(f"Error fetching recent emails: {e}")


def move_to_trash(service, message_id):
    service.users().messages().trash(userId="me", id=message_id).execute()


def send_email_reply(service, to_email, subject, message_body):
    """Send an email reply using Gmail API."""
    message = MIMEText(message_body)
    message["to"] = to_email
    message["subject"] = "Re: " + subject # why Re? because it's a reply to the original email

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