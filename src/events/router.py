from fastapi import APIRouter, Depends, UploadFile, File, Request, HTTPException, status, Body
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from auth.models import User
from events.schemas import EventCreateSchema, EventCreateResponseSchema, EventFileSchema
from events.models import Event, CustomField, EventDate, EventTime, EventFile
from events.utils import upload_photo, upload_files_for_event, add_custom_fields_to_event, add_dates_and_times_to_event
from auth.utils import oauth_scheme
from user_profile.utils import get_user_profile_by_email
from pydantic import ValidationError
from database import get_async_session
from typing import List, Optional, Annotated
import shutil


router = APIRouter(
    prefix="/api/event"
)

@router.post("/create_event", response_model=EventCreateResponseSchema)
async def create_event(
    event: EventCreateSchema = Body(...),
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session),
    photo: Optional[UploadFile] = UploadFile(None)
):
    user = await get_user_profile_by_email(token, db)

    photo_path = None
    if photo:
        photo_path = upload_photo(photo)

    new_event = Event(
        name=event.name,
        theme=event.theme,
        description=event.description,
        visit_cost=event.visit_cost,
        city=event.city,
        address=event.address,
        status=event.status,
        format=event.format,
        photo=photo_path,
        creator=user
    )

    add_custom_fields_to_event(new_event, event)

    add_dates_and_times_to_event(new_event, event)

    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)

    registration_link = f"/api/event/{new_event.id}/register"

    return {
        "msg": "Event created",
        "event_id": new_event.id,
        "registration_link": registration_link
    }


@router.post("/upload_event_files/{event_id}", response_model=EventCreateResponseSchema)
async def upload_event_files(
    event_id: int,
    files: List[UploadFile],
    files_descriptions: Optional[List[str]] = None,
    db: AsyncSession = Depends(get_async_session)
):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")


    event_files = upload_files_for_event(files, files_descriptions)

    for file in event_files:
        file.event_id = event.id
        db.add(file)

    await db.commit()
    await db.refresh(event)

    return {
        "msg": "Files uploaded successfully",
        "event_id": event.id,
        "registration_link": f"/api/event/{event.id}/register"
    }