from fastapi import APIRouter, Depends, UploadFile, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from events.schemas import EventCreateSchema, EventCreateResponseSchema, EventInviteSchema, EventRegistrationSchema
from events.models import Event, EventDate
from events.utils import upload_photo, upload_files_for_event, add_custom_fields_to_event, add_dates_and_times_to_event, create_registration_link, send_email, register_for_event, get_events, get_event_info
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
    new_event.registration_link = registration_link
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


@router.get("/view/")
async def view_all_events(db: AsyncSession = Depends(get_async_session)):
    stmt = select(Event).options(selectinload(Event.event_dates))
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    event_list = get_events(events)
    
    return event_list


@router.get("/view/{format}/")
async def view_all_events(format: str,
                          db: AsyncSession = Depends(get_async_session)):
    stmt = select(Event).where(Event.format == format).options(selectinload(Event.event_dates))
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    event_list = get_events(events)
    
    return event_list


@router.get("/{event_id}/view/")
async def view_all_events(event_id: int,
                          db: AsyncSession = Depends(get_async_session)):
    stmt = select(Event).where(Event.id == event_id).options(selectinload(Event.event_dates))
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    event_info = get_event_info(event)
    
    return event_info


@router.get("/join/{registration_link}/")
async def get_event_dates_and_times_info(registration_link: str,
                                    token: str = Depends(oauth_scheme),
                                    db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)
    stmt = select(Event).where(Event.registration_link == registration_link).options(
        selectinload(Event.custom_fields)
    )
    event_result = await db.execute(stmt)
    existing_event = event_result.scalar_one_or_none()
    if existing_event is None:
        return {"msg": "Event not found or invalid link"}
    
    dates_stmt = (
        select(EventDate)
        .where(EventDate.event_id == existing_event.id)
        .options(selectinload(EventDate.event_times))
    )
    dates_result = await db.execute(dates_stmt)
    event_dates = dates_result.scalars().all()

    dates_info = [
        {
            "date_id": event_date.id,
            "date": event_date.event_date,
            "times": [
                {
                    "time_id": event_time.id,
                    "start_time": event_time.start_time,
                    "end_time": event_time.end_time,
                    "seats_number": event_time.seats_number
                }
                for event_time in event_date.event_times
            ]
        }
        for event_date in event_dates
    ]

    custom_fields_info = [
        {
            "field_id": custom_field.id,
            "title": custom_field.title
        }
        for custom_field in existing_event.custom_fields
    ]

    return {"dates": dates_info, "custom_fields": custom_fields_info}

    
@router.post("/join/{registration_link}/")
async def register_for_event_by_link(
    registration_link: str,
    registration_fields: EventRegistrationSchema,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user = await get_user_profile_by_email(token, db)
    
    stmt = select(Event).where(Event.registration_link == registration_link).options(
        selectinload(Event.event_dates).selectinload(EventDate.event_times),
        selectinload(Event.custom_fields)
    )
    event_result = await db.execute(stmt)
    event = event_result.scalar_one_or_none()
    
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found or invalid link")
    
    return await register_for_event(event, registration_fields, user.id, db)


@router.post("/register/{event_id}/")
async def register_for_event_by_id(
    event_id: int,
    registration_fields: EventRegistrationSchema,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user = await get_user_profile_by_email(token, db)
    
    stmt = select(Event).where(Event.id == event_id).options(
        selectinload(Event.event_dates).selectinload(EventDate.event_times),
        selectinload(Event.custom_fields)
    )
    event_result = await db.execute(stmt)
    event = event_result.scalar_one_or_none()
    
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.status == "close":
        raise HTTPException(
            status_code=403,
            detail="Registration for this event is closed. You can only register with a link."
        )
    
    return await register_for_event(event, registration_fields, user.id, db)