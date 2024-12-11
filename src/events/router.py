from fastapi import APIRouter, Depends, UploadFile, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct, and_
from events.schemas import EventCreateSchema, EventCreateResponseSchema, EventInviteSchema, EventRegistrationSchema, EventInfoSchema, EventSchema, FilterSchema, MessageSchema
from events.models import Event, Booking, EventDateTime
from events.utils import upload_photo, upload_files_for_event, add_custom_fields_to_event, add_dates_and_times_to_event, create_registration_link, send_email, register_for_event, get_events, get_event_info, get_event, collect_filters, send_message_to_email
from auth.utils import oauth_scheme
from user_profile.utils import get_user_profile_by_email
from database import get_async_session
from typing import List, Optional
from sqlalchemy.orm import selectinload
from s3 import S3Client, get_s3_client


router = APIRouter(
    prefix="/api/event"
)

@router.post("/create/", response_model=EventCreateResponseSchema)
async def create_event(
    event: EventCreateSchema = Body(...),
    token: str = Depends(oauth_scheme),
    s3_client: S3Client = Depends(get_s3_client),
    db: AsyncSession = Depends(get_async_session),
    photo: Optional[UploadFile] = UploadFile(None),
    schedule: Optional[UploadFile] = UploadFile(None)
):
    user = await get_user_profile_by_email(token, db)

    photo_path = None
    if photo.filename:
        photo_path = await upload_photo(photo, photo.filename, s3_client)

    schedule_path = None
    if schedule.filename:
        schedule_path = await upload_photo(schedule, schedule.filename, s3_client)

    
    new_event = Event(
        name=event.name,
        description=event.description,
        visit_cost=event.visit_cost,
        city=event.city,
        address=event.address,
        status=event.status,
        format=event.format,
        photo=photo_path,
        schedule=schedule_path,
        creator_id=user.id
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


@router.get("/view/", response_model=List[EventInfoSchema])
async def view_all_events(s3_client: S3Client = Depends(get_s3_client), db: AsyncSession = Depends(get_async_session)):
    stmt = select(Event).options(selectinload(Event.event_dates_times))
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    event_list = get_events(events, s3_client)
    return event_list


@router.get("/view/my/", response_model=List[EventInfoSchema])
async def view_all_my_events(s3_client: S3Client = Depends(get_s3_client),
                          token: str = Depends(oauth_scheme),
                          db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)
    stmt = select(Event).where(Event.creator_id == user.id).options(selectinload(Event.event_dates_times))
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    event_list = get_events(events, s3_client)
    return event_list


@router.get("/view/participate/", response_model=List[EventInfoSchema])
async def view_participate_events(s3_client: S3Client = Depends(get_s3_client),
                          token: str = Depends(oauth_scheme),
                          db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)
    stmt = (
        select(Event)
        .join(EventDateTime, EventDateTime.event_id == Event.id)
        .join(Booking, Booking.event_date_time_id == EventDateTime.id)
        .where(Booking.user_id == user.id, Event.creator_id != user.id)
        .options(
            selectinload(Event.event_dates_times).selectinload(EventDateTime.event_initiator)
        )
    )
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    event_list = get_events(events, s3_client)
    return event_list


@router.get("/view/other/", response_model=List[EventInfoSchema])
async def view_participate_events(s3_client: S3Client = Depends(get_s3_client),
                          token: str = Depends(oauth_scheme),
                          db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)
    stmt = (
        select(Event)
        .join(EventDateTime, EventDateTime.event_id != Event.id)
        .join(Booking, Booking.event_date_time_id != EventDateTime.id)
        .where(Booking.user_id != user.id, Event.creator_id != user.id)
        .distinct()
        .order_by(Event.id)
        .options(
            selectinload(Event.event_dates_times).selectinload(EventDateTime.event_initiator)
        )
    )
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    event_list = get_events(events, s3_client)
    return event_list



@router.get("/view/{format}/", response_model=List[EventInfoSchema])
async def view_all_events(format: str,
                          s3_client: S3Client = Depends(get_s3_client),
                          db: AsyncSession = Depends(get_async_session)):
    stmt = select(Event).where(Event.format == format).options(selectinload(Event.event_dates_times))
    result = await db.execute(stmt)
    events = result.scalars().all()
    
    event_list = get_events(events, s3_client)
    
    return event_list


@router.get("/{event_id}/view/", response_model=EventSchema)
async def view_all_events(event_id: int,
                          s3_client: S3Client = Depends(get_s3_client),
                          db: AsyncSession = Depends(get_async_session)):
    stmt = select(Event).where(Event.id == event_id).options(selectinload(Event.event_dates_times).selectinload(EventDateTime.date_time_bookings),
                                                             selectinload(Event.creator))
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    event_info = get_event(event, s3_client)
    
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
    
    dates_times_stmt = (
        select(EventDateTime)
        .where(EventDateTime.event_id == existing_event.id)
    )
    dates_times_result = await db.execute(dates_times_stmt)
    event_dates_times = dates_times_result.scalars().all()

    dates_info = [
        {
            "date_time_id": event_date_time.id,
            "start_date": event_date_time.start_date,
            "end_date": event_date_time.end_date,
            "start_time": event_date_time.start_time,
            "end_time": event_date_time.end_time,
            "seats_number": event_date_time.seats_number,
        }
        for event_date_time in event_dates_times
    ]
    if existing_event.custom_fields:
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
        selectinload(Event.event_dates_times),
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
        selectinload(Event.event_dates_times),
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


@router.post("/message/{event_id}/")
async def send_message_to_event_participants(
    event_id: int,
    message: MessageSchema,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)

    stmt = select(Event).where(Event.id == event_id).options(
        selectinload(Event.event_dates_times).selectinload(EventDateTime.date_time_bookings)
        .selectinload(Booking.user_bookings)
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if not event:
        raise "Event doesn't exist"
    
    if event.creator_id != user.id:
        raise "User is not a event creator"
    
    participants_emails = set()
    for date_time in event.event_dates_times:
        for booking in date_time.date_time_bookings:
            if booking.user_bookings and booking.user_bookings.email:
                participants_emails.add(booking.user_bookings.email)
    
    for email in participants_emails:
        await send_message_to_email(message.theme, message.message, email)
    
    return {"msg": "Message was send"}


@router.get("/cities/")
async def get_cities(db: AsyncSession = Depends(get_async_session)):
    stmt = select(distinct(Event.city)).where(Event.city != None)
    result = await db.execute(stmt)
    cities = result.scalars().all()

    return {"cities": cities}


@router.post("/filter/", response_model=List[EventInfoSchema])
async def filter_events(
    filters: Optional[FilterSchema] = Body(default=None),
    s3_client: S3Client = Depends(get_s3_client),
    db: AsyncSession = Depends(get_async_session)
):
    stmt = select(Event).distinct().options(
        selectinload(Event.event_dates_times),
        selectinload(Event.creator)
    )
    
    conditions = collect_filters(filters)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await db.execute(stmt)
    events = result.scalars().all()

    event_list = get_events(events, s3_client)
    
    return event_list