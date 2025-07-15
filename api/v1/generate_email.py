from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from utils.email_generator import generate_cold_email

router = APIRouter(tags=["Cold Email"])


class GenerateEmailRequest(BaseModel):
    linkedin_url: str
    role: str
    website: str | None = None
    tone: str = "friendly"


class EmailResponse(BaseModel):
    variation_1: str
    variation_2: str | None = None


@router.post("/generate-email", response_model=EmailResponse)
async def generate_email(data: GenerateEmailRequest):
    try:
        result = await generate_cold_email(
            linkedin_url=data.linkedin_url,
            role=data.role,
            website=data.website,
            tone=data.tone,
        )
        return {
            "variation_1": result[0],
            "variation_2": result[1] if len(result) > 1 else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
