from fastapi import APIRouter
from models.contact import get_all_contacts

router = APIRouter(tags=["Contact"])


@router.get("/list-contacts")
async def list_contacts(user_id: str):
    try:
        if not user_id:
            raise ValueError("user_id is required")
        
        contacts = await get_all_contacts(user_id)
        return {"message": "Contacts fetched successfully", "contacts": contacts}

    except Exception as e:
        return {"message": "Error fetching contacts", "error": str(e)}
