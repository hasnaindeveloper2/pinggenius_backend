from fastapi import FastAPI

from api.v1 import analyze_email
from api.v1 import generate_email
from api.v1 import save_contact
from api.v1 import start_sequence
from api.v1 import list_contacts
from api.v1 import hard_emails
from gmail_service import fetch_recent_emails, get_gmail_service


app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "PingGenius Email Agent API is running 🚀"}


# -------- Routers --------
app.include_router(analyze_email.router, prefix="/api/v1")
app.include_router(generate_email.router, prefix="/api/v1")
app.include_router(save_contact.router, prefix="/api/v1")
app.include_router(start_sequence.router, prefix="/api/v1")
app.include_router(list_contacts.router, prefix="/api/v1")
app.include_router(hard_emails.router, prefix="/api/v1")


# -------- fetched latest emails from gmail --------
@app.get("/latest-emails")
def test_gmail():
    try:
        service = get_gmail_service()
        emails = fetch_recent_emails(service)
        return {"count": len(emails), "emails": emails}
    except Exception as e:
        return {"error": str(e)}
