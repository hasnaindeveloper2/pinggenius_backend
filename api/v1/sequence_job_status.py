from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.sequence_job import sequence_job
from bson import ObjectId

router = APIRouter(tags=["Sequence"])


class SequenceStatusRequest(BaseModel):
    user_id: str
    contact_id: str


class SequenceStatusResponse(BaseModel):
    is_sequence_running: bool


@router.post("/sequence-status", response_model=SequenceStatusResponse)
async def get_sequence_status(data: SequenceStatusRequest):
    """
    Return True if a sequence job for this user/contact is currently running.
    """
    try:
        job = await sequence_job.find_one(
            {
                "user_id": ObjectId(data.user_id),
                "contact_id": ObjectId(data.contact_id),
            }
        )

        # ✅ explicit bool to avoid None/other types
        is_running = bool(job["is_sequence_running"]) if job else False
        return {"is_sequence_running": is_running}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")
