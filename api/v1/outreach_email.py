from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Literal
from utils.email_generator import generate_cold_email
from utils.linkedin_scraper import guardrail_linkedin_scrape

router = APIRouter(tags=["Cold Email"])


class GenerateEmailRequest(BaseModel):
    email: str
    user_id: str
    linkedin_url: str
    website: str | None = None
    tone: Literal["friendly", "formal", "funny"] = "friendly"


class EmailResponse(BaseModel):
    email: str
    variation_1: str
    variation_2: str | None = None


@router.post("/generate-email", response_model=EmailResponse)
async def generate_email(data: GenerateEmailRequest):
    try:
        # STEP 1: Validate
        if "linkedin.com/in/" not in data.linkedin_url:
            raise HTTPException(status_code=400, detail="Invalid LinkedIn URL format")

        # STEP 2: Scrape LinkedIn with guardrail + caching
        linkedin_data = guardrail_linkedin_scrape(data.linkedin_url)
        if linkedin_data["status"] != "success":
            raise HTTPException(status_code=400, detail=linkedin_data["message"])

        user_data = linkedin_data["data"]

        result = await generate_cold_email(
            linkedin_url=data.linkedin_url,
            role=user_data["headline"],
            website=data.website,
            tone=data.tone,
            about=user_data["about"],
            user_id=data.user_id,
        )
        return {
            "email": data.email,
            "variation_1": result[0],
            "variation_2": result[1] if len(result) > 1 else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
