from fastapi import APIRouter
from models.contact import get_all_contacts

router = APIRouter(tags=["Contact"])


@router.get("/list-contacts")
async def list_contacts():

    contacts = await get_all_contacts()
    return contacts
