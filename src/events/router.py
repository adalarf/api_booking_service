from fastapi import APIRouter, Depends, UploadFile, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct, and_, delete
from sqlalchemy.orm import joinedload
from events.schemas import EventCreateSchema, EventCreateResponseSchema, EventInviteSchema, EventRegistrationSchema, EventInfoSchema, EventSchema, FilterSchema, MessageSchema, ChangeOnlineLinkSchema, EventUpdateSchema, TeamInvitationSchema
from events.models import Event, Booking, EventDateTime, EventInvite, StatusEnum
from events.utils import upload_photo, upload_files_for_event, add_custom_fields_to_event, add_dates_and_times_to_event, send_email, register_for_event, get_events, get_event_info, get_event, collect_filters, send_message_to_email, update_custom_fields_for_event, update_dates_and_times_for_event, create_new_custom_fields_for_event, create_new_dates_and_times_for_event
from auth.utils import oauth_scheme
from auth.models import User
from user_profile.utils import get_user_profile_by_email
from teams.models import Team, UserTeam
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

    online_link = str(event.online_link) if event.online_link else None

    new_event = Event(
        name=event.name,
        description=event.description,
        visit_cost=event.visit_cost,
        city=event.city,
        address=event.address,
        status=event.status,
        format=event.format,
        online_link=online_link,
        photo=photo_path,
        schedule=schedule_path,
        creator_id=user.id
    )

    add_custom_fields_to_event(new_event, event)

    add_dates_and_times_to_event(new_event, event)

    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)

    return {
        "msg": "Event created",
        "event_id": new_event.id,
        "event_link": f"http://localhost:3001/events/{new_event.id}"
    }


@router.patch("/update/{event_id}/")
@router.put("/update/{event_id}/")
async def update_event(
    event_id: int,
    updated_event: EventUpdateSchema = Body(...),
    token: str = Depends(oauth_scheme),
    s3_client: S3Client = Depends(get_s3_client),
    db: AsyncSession = Depends(get_async_session),
    photo: Optional[UploadFile] = UploadFile(None),
    schedule: Optional[UploadFile] = UploadFile(None)
):
    user = await get_user_profile_by_email(token, db)

    event = await db.get(Event, event_id, options=[joinedload(Event.event_dates_times), joinedload(Event.creator)])
    if not event:
        return {"msg": "Event not found"}
    
    if event.creator_id != user.id:
        return {"msg": "User isn't a creator of the event"}
    
    if event.state != "Открыто":
        return {"msg": "Event doesn't open"}
    
    if photo.filename:
        if event.photo:
            await s3_client.delete_file(event.photo)
        event.photo = await upload_photo(photo, photo.filename, s3_client)

    if schedule.filename:
        if event.schedule:
            await s3_client.delete_file(event.schedule)
        event.schedule = await upload_photo(schedule, schedule.filename, s3_client)

    for field, value in updated_event.dict(exclude_unset=True).items():
        if field not in {"custom_fields", "new_custom_fields", "event_dates_times", "new_event_dates_times"}:
            if value is not None:
                setattr(event, field, value)

    if updated_event.custom_fields:
        await update_custom_fields_for_event(event, updated_event.custom_fields, db)

    if updated_event.event_dates_times:
        await update_dates_and_times_for_event(event, updated_event.event_dates_times, db)

    if updated_event.new_custom_fields:
        await create_new_custom_fields_for_event(event, updated_event.new_custom_fields, db)

    if updated_event.new_event_dates_times:
        await create_new_dates_and_times_for_event(event, updated_event.new_event_dates_times, db)

    await db.commit()

    stmt = (
        select(User)
        .join(Booking, Booking.user_id == User.id)
        .filter(Booking.event_date_time_id.in_([dt.id for dt in event.event_dates_times]))
    )
    participants_result = await db.execute(stmt)
    participants = participants_result.scalars().all()
    
    for participant in participants:
        await send_message_to_email("Пожалуйста проверьте обновлённое мероприятие", f"Мероприятие '{event.name}' было обновлено", participant.email)

    return {
        "msg": "Event updated successfully",
        "event_id": event.id
    }


@router.delete("/cancel/{event_id}/")
async def cancel_event(
    event_id: int,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user = await get_user_profile_by_email(token, db)
    stmt = select(Event).where(Event.id == event_id).options(selectinload(Event.custom_fields),
                                                             selectinload(Event.event_dates_times),
                                                             selectinload(Event.files))
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(detail="Event doesn't exist", status_code=404)
    
    if event.creator_id != user.id:
        raise HTTPException(detail="User isn't a event creator", status_code=403)
    
    if event.state != "Открыто":
        raise HTTPException(detail="Event doesn't have 'open' state", status_code=403)
    
    stmt = (
        select(User)
        .join(Booking, Booking.user_id == User.id)
        .filter(Booking.event_date_time_id.in_([dt.id for dt in event.event_dates_times]))
    )
    participants_result = await db.execute(stmt)
    participants = participants_result.scalars().all()

    for participant in participants:
        await send_message_to_email("Ваше мероприятие удалено", f"Мероприятие '{event.name}' было удалено", participant.email)

    await db.delete(event)
    await db.commit()

    return {"msg": "Event was deleted"}


@router.patch("/change-online-link/{event_id}/")
@router.put("/change-online-link/{event_id}/")
async def change_online_link_for_event(
    event_id: int,
    online_link: ChangeOnlineLinkSchema,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user = await get_user_profile_by_email(token, db)

    stmt = select(Event).where(Event.id == event_id)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()

    if not event:
        return {"msg": "Event doesn't exist"}
    
    if event.creator_id != user.id:
        return {"msg": "User isn't a event creator"}
    
    event.online_link = str(online_link.online_link)
    await db.commit()
    return {"msg": "Link for online event was changed"}


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

    stmt = select(Event).where(Event.id == event_id).options(selectinload(Event.creator))
    event_result = await db.execute(stmt)
    existing_event = event_result.scalar_one_or_none()

    if existing_event:
        creator = existing_event.creator
        if creator == user:
            for invited_user in users_invited_to_event.users_emails:
                invite = EventInvite(email=invited_user.email, event_id=event_id)
                db.add(invite)
                await send_email(existing_event.id, existing_event.name, invited_user)
            
            await db.commit()

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
    stmt = select(Event).where(Event.status!=StatusEnum.close).options(selectinload(Event.event_dates_times))
    result = await db.execute(stmt)
    events = result.scalars().all()

    filtered_events = [event for event in events if event.state != "Завершено"]
    
    event_list = get_events(filtered_events, s3_client)
    return event_list


@router.get("/view/my/", response_model=List[EventInfoSchema])
async def view_all_my_events(s3_client: S3Client = Depends(get_s3_client),
                          token: str = Depends(oauth_scheme),
                          db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)
    stmt = select(Event).where(Event.creator_id == user.id).distinct().options(selectinload(Event.event_dates_times))
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

    filtered_events = [event for event in events if event.state != "Завершено"]
    
    event_list = get_events(filtered_events, s3_client)
    return event_list



@router.get("/view/{format}/", response_model=List[EventInfoSchema])
async def view_all_events(format: str,
                          s3_client: S3Client = Depends(get_s3_client),
                          db: AsyncSession = Depends(get_async_session)):
    stmt = select(Event).where(Event.format == format, Event.status!=StatusEnum.close).options(selectinload(Event.event_dates_times))
    result = await db.execute(stmt)
    events = result.scalars().all()

    filtered_events = [event for event in events if event.state != "Завершено"]
    
    event_list = get_events(filtered_events, s3_client)
    
    return event_list


@router.get("/{event_id}/view/", response_model=EventSchema)
async def view_events(event_id: int,
                          s3_client: S3Client = Depends(get_s3_client),
                          db: AsyncSession = Depends(get_async_session)):
    stmt = select(Event).where(Event.id == event_id).options(selectinload(Event.event_dates_times).selectinload(EventDateTime.date_time_bookings),
                                                             selectinload(Event.creator))
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if event.status == StatusEnum.close:
        raise HTTPException(detail="Event is closed", status_code=403)

    event_info = get_event(event, s3_client)
    
    return event_info


@router.get("/{event_id}/view-closed/", response_model=EventSchema)
async def view_closed_events(event_id: int,
                          token: str = Depends(oauth_scheme),
                          s3_client: S3Client = Depends(get_s3_client),
                          db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)
    stmt = select(Event).where(Event.id == event_id).options(selectinload(Event.event_dates_times).selectinload(EventDateTime.date_time_bookings),
                                                             selectinload(Event.creator),
                                                             selectinload(Event.invites))
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if event.status == StatusEnum.close:
        registered_stmt = (
            select(Booking).where(and_(
                    Booking.user_id == user.id,
                    Booking.event_date_time_id.in_([dt.id for dt in event.event_dates_times]))
                    ))
        registration_result = await db.execute(registered_stmt)
        is_registered = registration_result.scalar_one_or_none()

        invite_stmt = (
            select(EventInvite)
            .where(and_(
                    EventInvite.event_id == event.id,
                    EventInvite.email == user.email))
        )
        invite_result = await db.execute(invite_stmt)
        has_invite = invite_result.scalar_one_or_none()

        if not is_registered and not has_invite:
            raise HTTPException(detail="You do not have access to this event")

    event_info = get_event(event, s3_client)
    
    return event_info


@router.get("/register/{event_id}/")
async def get_register_by_event_id_info(
    event_id: int,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user = await get_user_profile_by_email(token, db)
    stmt = select(Event).where(Event.id == event_id).options(
        selectinload(Event.custom_fields)
    )
    event_result = await db.execute(stmt)
    existing_event = event_result.scalar_one_or_none()
    if existing_event is None:
        return {"msg": "Event not found or invalid link"}
    
    dates_times_stmt = (
        select(EventDateTime)
        .where(EventDateTime.event_id == existing_event.id)
        .order_by(EventDateTime.start_date, EventDateTime.start_time)
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
    return {"dates": dates_info}


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
        invite = await db.execute(
            select(EventInvite).where(EventInvite.email == user.email, EventInvite.event_id == event_id)
        )
        if not invite.scalar_one_or_none():
            return "Registration by link is required for this event."
    
    response = await register_for_event(event, registration_fields, user.id, db)

    await db.execute(
        delete(EventInvite).where(EventInvite.email == user.email, EventInvite.event_id == event_id)
    )
    await db.commit()

    return response


@router.delete("/cancel-booking/{event_id}/")
async def cancel_booking(
    event_id: int,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user = await get_user_profile_by_email(token, db)
    stmt = select(Booking).join(EventDateTime).where(EventDateTime.event_id == event_id).options(
        selectinload(Booking.booking_values)
    )
    result = await db.execute(stmt)
    booking = result.scalar_one_or_none()

    if not booking:
        return {"msg": "Booking doesn't exist"}
    
    if booking.user_id != user.id:
        return {"msg": "User isn't a member of the event"}
    
    await db.delete(booking)

    event_date_time_slot_stmt = select(EventDateTime).where(EventDateTime.id == booking.event_date_time_id)
    existing_event_date_time_slot = await db.execute(event_date_time_slot_stmt)
    event_date_time_slot = existing_event_date_time_slot.scalar_one_or_none()
    event_date_time_slot.seats_number += 1

    await db.commit()

    return {"msg": "Booking was deleted"}


@router.get("/member/{event_id}/")
async def is_event_member(
    event_id: int,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
    ):

    user = await get_user_profile_by_email(token, db)

    stmt = select(Booking).join(EventDateTime).where(EventDateTime.event_id == event_id, Booking.user_id == user.id)
    result = await db.execute(stmt)
    member = bool(result.scalar_one_or_none())
    return member


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
    stmt = select(Event).distinct().join(
        EventDateTime, Event.id == EventDateTime.event_id, isouter=True
        ).join(User, Event.creator_id == User.id).where(Event.status != StatusEnum.close).order_by(Event.id).options(
        selectinload(Event.event_dates_times),
        selectinload(Event.creator)
    )
    
    conditions = collect_filters(filters)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await db.execute(stmt)
    events = result.scalars().all()

    filtered_events = [event for event in events if event.state != "Завершено"]

    event_list = get_events(filtered_events, s3_client)
    
    return event_list


@router.post("/invite-team/{event_id}/")
async def send_event_invitation_to_team_members(
    event_id: int,
    team_invitation: TeamInvitationSchema,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
    ):
    user = await get_user_profile_by_email(token, db)

    stmt = select(Event).where(Event.id == event_id)
    stmt_result = await db.execute(stmt)
    event = stmt_result.scalar_one_or_none()

    if not event:
        raise HTTPException(detail="Event doesn't exist", status_code=404)
    
    stmt = select(UserTeam).where(UserTeam.team_id == team_invitation.team_id, 
                                  UserTeam.user_id == user.id,
                                  UserTeam.is_admin == True)
    stmt_result = await db.execute(stmt)
    team = stmt_result.scalar_one_or_none()

    if not team:
        raise HTTPException(detail="Team doesn't exist or user isn't a creator", status_code=404)
    
    stmt = select(UserTeam).where(UserTeam.team_id == team_invitation.team_id,
                                  UserTeam.is_admin == False).options(
                                      selectinload(UserTeam.user)
                                  )
    stmt_result = await db.execute(stmt)
    team_members = stmt_result.scalars().all()

    for team_member in team_members:
        await send_email(event_id, event.name, team_member.user)

    return {"msg": "Team was invited"}