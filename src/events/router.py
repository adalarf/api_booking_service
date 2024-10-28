from fastapi import APIRouter, Depends, UploadFile, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from events.schemas import EventCreateSchema, EventCreateResponseSchema, EventInviteSchema
from events.models import Event
from events.utils import upload_photo, upload_files_for_event, add_custom_fields_to_event, add_dates_and_times_to_event, create_registration_link, encrypt_registration_link, send_email
from auth.utils import oauth_scheme
from user_profile.utils import get_user_profile_by_email
from database import get_async_session
from typing import List, Optional
from sqlalchemy.orm import selectinload


router = APIRouter(
    prefix="/api/event"
)

@router.post("/create/", response_model=EventCreateResponseSchema)
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
    new_event_id = new_event.id
    registration_link = create_registration_link(new_event_id)
    new_event.registration_link = encrypt_registration_link(registration_link)

    await db.commit()

    return {
        "msg": "Event created",
        "event_id": new_event.id,
        "registration_link": registration_link
    }


@router.post("/upload_event_files/{event_id}/", response_model=EventCreateResponseSchema)
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


@router.post("/invite/")
async def invite_users(users_invited_to_event: EventInviteSchema, token: str = Depends(oauth_scheme), db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)
    event_id = users_invited_to_event.event_id
    stmt = select(Event).where(Event.id == event_id)

    # event = await db.execute(stmt)
    # existing_event = event.scalar_one_or_none()
    # res = await db.scalars(
    #     select(Event).options(selectinload(Event.creator))
    # )
    # creator = res.first()
    stmt = select(Event).where(Event.id == event_id).options(selectinload(Event.creator))
    event_result = await db.execute(stmt)
    existing_event = event_result.scalar_one_or_none()

    if existing_event:
        creator = existing_event.creator
        if creator == user:
            for invited_user in users_invited_to_event.users_emails:
                await send_email(existing_event.registration_link, existing_event.name, invited_user)

            return {
                "msg": "Registration link was sent successfully",
            }
        
        return {
            "msg": "user is not a event creator"
        }
    
    return{
        "msg": "event doesn't exist"
    }