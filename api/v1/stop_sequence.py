from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.sequence import sequences
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from utils.scheduler import scheduler

router = APIRouter(tags=["Sequence"])


class StopSequenceRequest(BaseModel):
    contact_id: str

@router.post("/stop-sequence")
async def stop_sequence(id: StopSequenceRequest):
    try:
        jobs = scheduler.get_jobs()
        cancelled_steps = []

        for job in jobs:
            if job.id.startswith(f"seq_{id.contact_id}_"):
                scheduler.remove_job(job.id)

                step = int(job.id.split("_")[-1])
                cancelled_steps.append(step)

                # DB update
                await sequences.update_one(
                    {"contact_id": id.contact_id, "step": step},
                    {"$set": {"status": "cancelled"}},
                )

        return {
            "message": f"Cancelled steps {cancelled_steps} for contact {id.contact_id}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
