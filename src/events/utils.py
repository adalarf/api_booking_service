from fastapi import UploadFile, Body, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from auth.models import User
from events.models import Event, EventFile, CustomField, Booking, CustomValue, EventDateTime, StatusEnum
from events.schemas import EventCreateSchema, EmailSchema, EventRegistrationSchema, FilterSchema, UpdateCustomFieldSchema, UpdateEventDateTimeSchema, EventDateTimeSchema
from cryptography.fernet import Fernet
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from typing import List, Optional
from database import async_session_maker
from email.message import EmailMessage
from config import REGISTATION_LINK_CIPHER_KEY, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_HOST, EMAIL_PORT
from s3 import S3Client
from datetime import datetime, timedelta
import secrets
import base64
import aiosmtplib


cipher = Fernet(REGISTATION_LINK_CIPHER_KEY.encode())

async def delete_expired_bookings():
    async with async_session_maker() as db:
        stmt = select(Booking).where(Booking.expiration_date <= datetime.utcnow())
        expired_bookings = await db.execute(stmt)
        for booking in expired_bookings.scalars().all():
            await db.delete(booking)
            event_date_time_slot_stmt = select(EventDateTime).where(EventDateTime.id == booking.event_date_time_id)
            existing_event_date_time_slot = await db.execute(event_date_time_slot_stmt)
            event_date_time_slot = existing_event_date_time_slot.scalar_one_or_none()
            event_date_time_slot.seats_number += 1
        await db.commit()


async def schedule_jobs():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(delete_expired_bookings, "interval", hours=1)
    scheduler.start()


async def upload_photo(file: UploadFile, object_name: str, s3_client: S3Client):
    await s3_client.upload_file(file, object_name)
    return object_name


async def upload_files_for_event(files: Optional[List[UploadFile]] = None,
                       files_descriptions: Optional[List[str]] = None):
    event_files = []
    if files:
        for index, file in enumerate(files):
            await upload_photo(file, file.filename)

            file_description = files_descriptions[index] if index < len(files_descriptions) else None
            new_file = EventFile(file_path=file.filename, description=file_description)
                
            event_files.append(new_file)

    return event_files

def create_registration_link(event_id: str) -> str:
    secret = secrets.token_urlsafe()
    registration_link = f"{event_id}/{secret}/"
    encoded_link = base64.urlsafe_b64encode(registration_link.encode()).decode()
    return encoded_link


def decrypt_registration_link(encrypted_link: str) -> str:
    decrypted_link = cipher.decrypt(encrypted_link.encode()).decode()
    decoded_link = base64.urlsafe_b64decode(decrypted_link.encode()).decode()
    return decoded_link


def add_custom_fields_to_event(new_event: Event, event: EventCreateSchema = Body(...)):
    if event.custom_fields:
        for custom_field in event.custom_fields:
            new_custom_field = CustomField(title=custom_field.title)
            new_event.custom_fields.append(new_custom_field)


def add_dates_and_times_to_event(new_event: Event, event: EventCreateSchema = Body(...)):
    for event_date_time in event.event_dates_times:
        new_event_date_time = EventDateTime(
            start_date=event_date_time.start_date,
            end_date=event_date_time.end_date,
            start_time=event_date_time.start_time,
            end_time=event_date_time.end_time,
            seats_number=event_date_time.seats_number,
        )

        new_event.event_dates_times.append(new_event_date_time)


async def update_custom_fields_for_event(event: Event, custom_fields: List[UpdateCustomFieldSchema], db: AsyncSession):
    for field_data in custom_fields:
        existing_field = await db.execute(
            select(CustomField).filter(CustomField.id == field_data.id, CustomField.event_id == event.id)
        )
        existing_field = existing_field.scalar_one_or_none()

        if existing_field:
            existing_field.title = field_data.title or existing_field.title
        else:
            return {"msg": "Custom field doesn't exist"}

    await db.flush()


async def update_dates_and_times_for_event(event: Event, event_dates_times: List[UpdateEventDateTimeSchema], db: AsyncSession):
    for date_time_data in event_dates_times:
        existing_date_time = await db.execute(
            select(EventDateTime).filter(EventDateTime.id == date_time_data.id, EventDateTime.event_id == event.id)
        )
        existing_date_time = existing_date_time.scalar_one_or_none()

        if existing_date_time:
            existing_date_time.start_date = date_time_data.start_date or existing_date_time.start_date
            existing_date_time.end_date = date_time_data.end_date or existing_date_time.end_date
            existing_date_time.start_time = date_time_data.start_time or existing_date_time.start_time
            existing_date_time.end_time = date_time_data.end_time or existing_date_time.end_time
            existing_date_time.seats_number = date_time_data.seats_number or existing_date_time.seats_number
        else:
            return {"msg": "Datetime slot doesn't exist"}

    await db.flush()


async def create_new_custom_fields_for_event(event: Event, new_custom_fields: List[UpdateCustomFieldSchema], db: AsyncSession):
    for field_data in new_custom_fields:
        new_field = CustomField(
            title=field_data.title,
            event_id=event.id
        )
        db.add(new_field)

    await db.flush()


async def create_new_dates_and_times_for_event(event: Event, new_event_dates_times: List[EventDateTimeSchema], db: AsyncSession):
    for date_time_data in new_event_dates_times:
        new_date_time = EventDateTime(
            start_date=date_time_data.start_date,
            end_date=date_time_data.end_date,
            start_time=date_time_data.start_time,
            end_time=date_time_data.end_time,
            seats_number=date_time_data.seats_number,
            event_id=event.id
        )
        db.add(new_date_time)

    await db.flush()


async def send_email(event_id: str, event_name: str, receiver: EmailSchema):
    event_link = f"http://localhost:3001/events/{event_id}"
    sender = EMAIL_SENDER
    email_host = EMAIL_HOST
    email_port = EMAIL_PORT
    email_password = EMAIL_PASSWORD
    message = f"Здравствуйте!\nВы были приглашены на мероприятие - {event_name}\nСсылка на регистрацию: {event_link}"
    email = EmailMessage()
    email["From"] = sender
    email["To"] = receiver.email
    email["Subject"] = "Приглашение на мероприятие"
    email.set_content(message)

    smtp = aiosmtplib.SMTP()
    
    await smtp.connect(hostname=email_host, port=email_port)
    await smtp.login(sender, email_password)

    await smtp.sendmail(sender, receiver.email, email.as_string())
    await smtp.quit()


async def send_message_to_email(theme: str, message: str, receiver_email: str):
    sender = EMAIL_SENDER
    email_host = EMAIL_HOST
    email_port = EMAIL_PORT
    email_password = EMAIL_PASSWORD
    email = EmailMessage()
    email["From"] = sender
    email["To"] = receiver_email
    email["Subject"] = theme
    email.set_content(message)

    smtp = aiosmtplib.SMTP()
    
    await smtp.connect(hostname=email_host, port=email_port)
    await smtp.login(sender, email_password)

    await smtp.sendmail(sender, receiver_email, email.as_string())
    await smtp.quit()


def get_start_and_end_dates_and_times(event: Event):
    if event.event_dates_times:
        start_date_obj = min(event.event_dates_times, key=lambda d: d.start_date)
        end_date_obj = max(event.event_dates_times, key=lambda d: d.end_date)

        start_date = start_date_obj.start_date
        end_date = end_date_obj.end_date
        start_time = start_date_obj.start_time
        end_time = end_date_obj.end_time
    else:
        start_date = None
        end_date = None
        start_time = None
        end_time = None

    return start_date, end_date, start_time, end_time


def get_event_photo_url(event: Event, s3_client: S3Client):
    photo_url = None
    if event.photo:
        photo_url = s3_client.config["endpoint_url"] + f"/{s3_client.bucket_name}/{event.photo}"
    
    return photo_url


def get_event_schedule_url(event: Event, s3_client: S3Client):
    schedule_url = None
    if event.schedule:
        schedule_url = s3_client.config["endpoint_url"] + f"/{s3_client.bucket_name}/{event.schedule}"
    
    return schedule_url


def get_event_info(event: Event, s3_client: S3Client):
    start_date, end_date, start_time, end_time = get_start_and_end_dates_and_times(event)
    
    photo_url = get_event_photo_url(event, s3_client)

    event_info = {
            "id": event.id,
            "name": event.name,
            "start_date": start_date,
            "end_date": end_date,
            "start_time": start_time,
            "end_time": end_time,
            "city": event.city,
            "visit_cost": event.visit_cost,
            "format": event.format.value,
            "state": event.state,
            "photo_url": photo_url,
        }
    
    return event_info


def get_creator_info(event: Event, s3_client: S3Client):
    photo_url = get_event_photo_url(event.creator, s3_client)

    creator_info = {
        "first_name":event.creator.first_name,
        "last_name": event.creator.last_name,
        "patronymic": event.creator.patronymic,
        "company": event.creator.company_name,
        "photo_url": photo_url,
        "contacts": {
            "email": event.creator.email,
            "phone_number": event.creator.phone_number,
            "vk": event.creator.vk,
            "telegram": event.creator.telegram,
            "whatsapp": event.creator.whatsapp,
        },
    }

    return creator_info


def get_time_slots_descriptions(event: Event):
    times_with_description = [
        {
            "id": date_time.id,
            "start_date": date_time.start_date,
            "end_date": date_time.end_date,
            "start_time": date_time.start_time,
            "end_time": date_time.end_time,
            "seats_number": None if date_time.seats_number is None else date_time.seats_number + len(date_time.date_time_bookings),
            "bookings_count": len(date_time.date_time_bookings),
        }
        for date_time in event.event_dates_times
    ]

    times_with_description = sorted(
        times_with_description,
        key=lambda x: (x["start_date"], x["start_time"])
    )

    return times_with_description


def get_event(event: Event, s3_client: S3Client):
    start_date, end_date, start_time, end_time = get_start_and_end_dates_and_times(event)
    
    photo_url = get_event_photo_url(event, s3_client)
    schedule_url = get_event_schedule_url(event, s3_client)
    creator_info = get_creator_info(event, s3_client)
    times_with_description = get_time_slots_descriptions(event)

    event_info = {
            "id": event.id,
            "name": event.name,
            "description": event.description,
            "start_date": start_date,
            "end_date": end_date,
            "start_time": start_time,
            "end_time": end_time,
            "city": event.city,
            "address": event.address,
            "visit_cost": event.visit_cost,
            "status": event.status,
            "format": event.format.value,
            "online_link": event.online_link,
            "state": event.state,
            "photo_url": photo_url,
            "schedule_url": schedule_url,
            "creator": creator_info,
            "time_slots_descriptions": times_with_description,
        }

    return event_info


def get_events(events: List[Event], s3_client: S3Client):
    event_list = []
    for event in events:
        event_info = get_event_info(event, s3_client)
        event_list.append(event_info)

    return event_list


async def register_for_event(
    event: Event,
    registration_fields: EventRegistrationSchema,
    user_id: int,
    db: AsyncSession,
    expiration_days: int,
):
    date_time_id = registration_fields.event_date_time_id

    existing_booking_stmt = select(Booking).where(
        Booking.user_id == user_id,
        Booking.event_date_time_id == date_time_id
    )
    existing_booking = await db.execute(existing_booking_stmt)
    if existing_booking.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="You are already registered for this event at the selected time.")
    
    selected_event_date_time = None
    for event_date_time in event.event_dates_times:
        if event_date_time.id == date_time_id:
            selected_event_date_time = date_time_id
            break
    
    if selected_event_date_time is None:
        raise HTTPException(status_code=404, detail="Selected date or time not found")
    
    event_date_time_slot_stmt = select(EventDateTime).where(EventDateTime.id == selected_event_date_time)
    existing_event_date_time_slot = await db.execute(event_date_time_slot_stmt)
    event_date_time_slot = existing_event_date_time_slot.scalar_one_or_none()
    if event_date_time_slot.seats_number:
        if event_date_time_slot.seats_number <= 0:
            raise HTTPException(status_code=400, detail="No seats available for the selected time")

        event_date_time_slot.seats_number -= 1

    event_end_date = max(
        datetime.combine(event_date_time.end_date, event_date_time.end_time)
        for event_date_time in event.event_dates_times
    )
    expiration_date = None
    if expiration_days is not None:
        expiration_date = event_end_date + timedelta(days=expiration_days)

    db.add(event_date_time_slot)
    booking = Booking(user_id=user_id, 
                      booking_date_time=event_date_time_slot, 
                      expiration_date=expiration_date)
    db.add(booking)
    await db.flush()
    
    if event.custom_fields:
        for field_data in registration_fields.custom_fields:
            matched_field = next(
                (cf for cf in event.custom_fields if cf.title == field_data.title),
                None,
            )
            if matched_field:
                custom_value = CustomValue(
                    value=field_data.value,
                    custom_field_id=matched_field.id,
                    booking_id=booking.id,
                )
                db.add(custom_value)
    
    await db.commit()

    return {"message": "Successfully registered for the event"}


def collect_filters(filters: Optional[FilterSchema]):
    if not filters:
        return []

    conditions = []

    if filters:
        conditions.append(Event.status != StatusEnum.close)

    if filters.city:
        conditions.append(Event.city.ilike(f"%{filters.city}%"))

    if filters.search:
        search = f"%{filters.search}%"
        conditions.append(
            or_(
                Event.name.ilike(search),
                User.first_name.ilike(search),
                User.last_name.ilike(search),
                User.patronymic.ilike(search),
                User.company_name.ilike(search)
            )
        )

    if filters.date_start is not None:
        conditions.append(EventDateTime.start_date >= filters.date_start)
    if filters.date_end is not None:
        conditions.append(EventDateTime.end_date <= filters.date_end)

    if filters.format:
        conditions.append(Event.format == filters.format)

    return conditions