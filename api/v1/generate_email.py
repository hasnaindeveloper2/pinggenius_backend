from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Literal
from utils.email_generator import generate_cold_email

router = APIRouter(tags=["Cold Email"])


class GenerateEmailRequest(BaseModel):
    linkedin_url: HttpUrl = Field(
        ..., description="Must be a valid LinkedIn profile URL"
    )
    role: str = Field(..., min_length=2)
    website: Optional[HttpUrl] = Field(None, description="User or company website")
    tone: Literal["friendly", "formal", "funny"] = "friendly"
    user_id: str = Field(..., min_length=3)


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
            user_id=data.user_id,
        )
        return {
            "variation_1": result[0],
            "variation_2": result[1] if len(result) > 1 else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
