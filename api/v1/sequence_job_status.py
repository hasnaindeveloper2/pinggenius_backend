from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from models.sequence_job import sequence_job

router = APIRouter(tags=["Sequence"])


class SequenceStatusRequest(BaseModel):
    user_id: str
    contact_id: str

class SequenceStatusResponse(BaseModel):
    is_sequence_running: bool

@router.post("/sequence-status", response_model=SequenceStatusResponse)
async def get_sequence_status(data: SequenceStatusRequest):
    """
    Get the sequence job status for a specific contact and user.
    """
    try:
        job = await sequence_job.find_one({
            "user_id": data.user_id,
            "contact_id": data.contact_id
        })

        if not job:
            # If no job document exists, return False
            return {"is_sequence_running": False}

        return {"is_sequence_running": job.get("is_sequence_running")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
