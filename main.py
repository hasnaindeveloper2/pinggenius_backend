from fastapi import FastAPI

from api.v1 import analyze_email
from api.v1 import generate_email
from api.v1 import save_contact
from api.v1 import start_sequence
from api.v1 import list_contacts
from api.v1 import generate_sequence
from api.v1 import hard_emails
from api.v1 import stop_sequence
from api.v1 import refine_hard_emails

# from gmail_service import fetch_recent_emails, get_gmail_service
from utils.APScheduler import start_user_scheduler, stop_user_scheduler

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "PingGenius Agent API is running 🚀"}


# -------- Routers --------
app.include_router(analyze_email.router, prefix="/api/v1")
app.include_router(generate_email.router, prefix="/api/v1")
app.include_router(save_contact.router, prefix="/api/v1")
app.include_router(start_sequence.router, prefix="/api/v1")
app.include_router(list_contacts.router, prefix="/api/v1")
app.include_router(stop_sequence.router, prefix="/api/v1")
app.include_router(generate_sequence.router, prefix="/api/v1")
app.include_router(hard_emails.router, prefix="/api/v1")
app.include_router(refine_hard_emails.router, prefix="/api/v1")


@app.post("/start-email-job/{user_id}")
def start_job(user_id: str, interval: int = 60):
    start_user_scheduler(user_id, interval)
    return {"status": "started", "user_id": user_id, "interval": interval}


@app.post("/stop-email-job/{user_id}")
def stop_job(user_id: str):
    stop_user_scheduler(user_id)
    return {"status": "stopped", "user_id": user_id}
