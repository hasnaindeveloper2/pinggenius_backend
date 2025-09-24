from fastapi import APIRouter
from pydantic import BaseModel
from utils.APScheduler import start_user_scheduler, stop_user_scheduler

router = APIRouter(tags=["Scheduler"])


class EmailJobRequest(BaseModel):
    user_id: str
    interval_minutes: int


@router.post("/start-email-job")
def start_job(email_job: EmailJobRequest):
    """Starts a background job to check for new emails for a user at a specified interval."""
    start_user_scheduler(email_job.user_id, email_job.interval_minutes)
    return {
        "status": "started",
        "user_id": email_job.user_id,
        "interval": email_job.interval_minutes,
    }


@router.post("/stop-email-job")
def stop_job(user_id: str):
    """Stops the email checking job for a specific user."""
    stop_user_scheduler(user_id)
    return {"status": "stopped", "user_id": user_id}
