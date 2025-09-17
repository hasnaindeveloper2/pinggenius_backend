from fastapi import APIRouter
from utils.APScheduler import start_user_scheduler, stop_user_scheduler

router = APIRouter(tags=["Scheduler"])


@router.post("/start-email-job/{user_id}")
def start_job(user_id: str, interval_minutes: int = 5):
    """Starts a background job to check for new emails for a user at a specified interval."""
    start_user_scheduler(user_id, interval_minutes)
    return {"status": "started", "user_id": user_id, "interval": interval_minutes}


@router.post("/stop-email-job/{user_id}")
def stop_job(user_id: str):
    """Stops the email checking job for a specific user."""
    stop_user_scheduler(user_id)
    return {"status": "stopped", "user_id": user_id}