from fastapi import APIRouter
from pydantic import BaseModel
from utils.APScheduler import start_user_scheduler, stop_user_scheduler
from models.jobs import jobs

router = APIRouter(tags=["Scheduler"])


class EmailJobStartRequest(BaseModel):
    user_id: str
    interval_minutes: int


class EmailJobStopRequest(BaseModel):
    user_id: str


@router.post("/start-email-job")
async def start_job(email_job: EmailJobStartRequest):
    """Starts a background job to check for new emails for a user at a specified interval."""
    await jobs.update_one(
        {"user_id": email_job.user_id},
        {"$set": {"is_sync_running": True, "interval": email_job.interval_minutes}},
        upsert=True,
    )
    await start_user_scheduler(email_job.user_id, email_job.interval_minutes)
    return {
        "status": "started",
        "user_id": email_job.user_id,
        "interval": email_job.interval_minutes,
    }


@router.post("/stop-email-job")
async def stop_job(payload: EmailJobStopRequest):
    """Stops the email checking job for a specific user."""
    await jobs.update_one(
        {"user_id": payload.user_id}, {"$set": {"is_sync_running": False}}
    )
    await stop_user_scheduler(payload.user_id)
    return {"status": "stopped", "user_id": payload.user_id}


@router.get("/email-job-status")
async def job_status(user_id: str):
    doc = await jobs.find_one({"user_id": user_id})
    return {"running": bool(doc and doc.get("is_sync_running"))}
