from fastapi import UploadFile, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from auth.models import User
from events.models import Event, EventFile, CustomField, EventDate, EventTime, Booking, CustomValue
from events.schemas import EventCreateSchema, EmailSchema, EventRegistrationSchema, FilterSchema
from cryptography.fernet import Fernet
from typing import List, Optional
from email.message import EmailMessage
from config import REGISTATION_LINK_CIPHER_KEY, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_HOST, EMAIL_PORT
from s3 import S3Client
import shutil
import secrets
import aiosmtplib
import base64


cipher = Fernet(REGISTATION_LINK_CIPHER_KEY.encode())


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


def add_custom_fields_to_event(new_event: Event, event: EventCreateSchema = Body(...)):
    for custom_field in event.custom_fields:
        new_custom_field = CustomField(title=custom_field.title)
        new_event.custom_fields.append(new_custom_field)


def add_dates_and_times_to_event(new_event: Event, event: EventCreateSchema = Body(...)):
    for event_date in event.event_dates:
        new_event_date = EventDate(event_date=event_date.event_date)

        for event_time in event_date.event_times:
            new_event_time = EventTime(
                start_time=event_time.start_time,
                end_time=event_time.end_time,
                seats_number=event_time.seats_number,
                description=event_time.description
            )
            new_event_date.event_times.append(new_event_time)

        new_event.event_dates.append(new_event_date)


def create_registration_link(event_id: str) -> str:
    secret = secrets.token_urlsafe()
    registration_link = f"{event_id}/{secret}"
    encoded_link = base64.urlsafe_b64encode(registration_link.encode()).decode()
    return encoded_link


def encrypt_registration_link(link: str) -> str:
    return cipher.encrypt(link.encode()).decode()


def decrypt_registration_link(encrypted_link: str) -> str:
    decrypted_link = cipher.decrypt(encrypted_link.encode()).decode()
    decoded_link = base64.urlsafe_b64decode(decrypted_link.encode()).decode()
    return decoded_link


async def send_email(registration_link: str, event_name: str, receiver: EmailSchema):
    registration_link_decrypted = decrypt_registration_link(registration_link)
    sender = EMAIL_SENDER
    email_host = EMAIL_HOST
    email_port = EMAIL_PORT
    email_password = EMAIL_PASSWORD
    message = f"Здравствуйте!\nВы были приглашены на мероприятие - {event_name}\nСсылка на регистрацию: {registration_link_decrypted}"
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


def get_start_and_end_dates_and_times(event: Event):
    if event.event_dates:
        start_date_obj = min(event.event_dates, key=lambda d: d.event_date)
        end_date_obj = max(event.event_dates, key=lambda d: d.event_date)

        start_date = start_date_obj.event_date
        end_date = end_date_obj.event_date

        start_times = [
            {"start_time": time.start_time, "end_time": time.end_time}
            for time in start_date_obj.event_times
        ]
        end_times = [
            {"start_time": time.start_time, "end_time": time.end_time}
            for time in end_date_obj.event_times
        ]
    else:
        start_date = None
        end_date = None
        start_times = None
        end_times = None

    return start_date, end_date, start_times, end_times


def get_event_photo_url(event: Event, s3_client: S3Client):
    photo_url = None
    if event.photo:
        photo_url = s3_client.config["endpoint_url"] + f"/{s3_client.bucket_name}/{event.photo}"
    
    return photo_url


def get_event_info(event: Event, s3_client: S3Client):
    start_date, end_date, start_times, end_times = get_start_and_end_dates_and_times(event)
    
    photo_url = get_event_photo_url(event, s3_client)

    event_info = {
            "id": event.id,
            "name": event.name,
            "start_date": start_date,
            "end_date": end_date,
            "start_date_times": start_times,
            "end_date_times": end_times,
            "city": event.city,
            "visit_cost": event.visit_cost,
            "format": event.format.value,
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
            "phone_number": event.creator.phone_number,
            "vk": event.creator.vk,
            "telegram": event.creator.telegram,
            "whatsapp": event.creator.whatsapp,
        },
    }

    return creator_info


def get_time_slots_descriptions(event: Event):
    times_with_description = []
    for date in event.event_dates:
        for event_time in date.event_times:
            times_with_description.append({
                "date": date.event_date,
                "start_time": event_time.start_time,
                "end_time": event_time.end_time,
                "description": event_time.description
            })

    return times_with_description


def get_event(event: Event, s3_client: S3Client):
    start_date, end_date, start_times, end_times = get_start_and_end_dates_and_times(event)
    
    photo_url = get_event_photo_url(event, s3_client)

    total_bookings = sum(
        len(event_time.booking_time) for date in event.event_dates for event_time in date.event_times
    )

    creator_info = get_creator_info(event, s3_client)

    times_with_description = get_time_slots_descriptions(event)

    event_info = {
            "id": event.id,
            "name": event.name,
            "description": event.description,
            "start_date": start_date,
            "end_date": end_date,
            "start_date_times": start_times,
            "end_date_times": end_times,
            "city": event.city,
            "address": event.address,
            "visit_cost": event.visit_cost,
            "format": event.format.value,
            "photo_url": photo_url,
            "total_bookings": total_bookings,
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
    db: AsyncSession
):
    selected_date_id = registration_fields.event_date_time.event_date_id
    selected_time_id = registration_fields.event_date_time.event_time.time_id

    existing_booking_stmt = select(Booking).where(
        Booking.user_id == user_id,
        Booking.event_time_id == selected_time_id
    )
    existing_booking = await db.execute(existing_booking_stmt)
    if existing_booking.scalar_one_or_none() is not None:
        raise HTTPException(status_code=400, detail="You are already registered for this event at the selected time.")
    
    selected_event_time = None
    for event_date in event.event_dates:
        if event_date.id == selected_date_id:
            selected_event_time = next(
                (time for time in event_date.event_times if time.id == selected_time_id),
                None
            )
            break
    
    if selected_event_time is None:
        raise HTTPException(status_code=404, detail="Selected date or time not found")
    
    if selected_event_time.seats_number <= 0:
        raise HTTPException(status_code=400, detail="No seats available for the selected time")

    selected_event_time.seats_number -= 1
    db.add(selected_event_time)
    
    booking = Booking(user_id=user_id, event_time_id=selected_time_id)
    db.add(booking)
    await db.flush()
    
    for field_data, custom_field in zip(registration_fields.custom_fields, event.custom_fields):
        custom_value = CustomValue(
            value=field_data.title,
            custom_field_id=custom_field.id,
            booking_id=booking.id
        )
        db.add(custom_value)
    
    await db.commit()

    return {"message": "Successfully registered for the event"}


def collect_filters(filters: Optional[FilterSchema]):
    if not filters:
        return []

    conditions = []

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
        conditions.append(EventDate.event_date >= filters.date_start)
    if filters.date_end is not None:
        conditions.append(EventDate.event_date <= filters.date_end)

    if filters.format:
        conditions.append(Event.format == filters.format)

    return conditions