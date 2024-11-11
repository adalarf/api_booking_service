from fastapi import UploadFile, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from events.models import Event, EventFile, CustomField, EventDate, EventTime, Booking, CustomValue
from events.schemas import EventCreateSchema, EmailSchema, EventRegistrationSchema
from cryptography.fernet import Fernet
from typing import List, Optional
from email.message import EmailMessage
from config import REGISTATION_LINK_CIPHER_KEY, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_HOST, EMAIL_PORT
import shutil
import secrets
import aiosmtplib
import base64


cipher = Fernet(REGISTATION_LINK_CIPHER_KEY.encode())


def upload_photo(photo: Optional[UploadFile] = None):
    if photo and photo.filename:
        photo.filename = photo.filename.lower()
        photo_path = f"media/{photo.filename}"

        with open(photo_path, 'wb+') as buffer:
            shutil.copyfileobj(photo.file, buffer)

        return photo_path
    
    return None


def upload_files_for_event(files: Optional[List[UploadFile]] = None,
                       files_descriptions: Optional[List[str]] = None):
    event_files = []
    if files:
        for index, file in enumerate(files):
            file.filename = file.filename.lower()
            file_path = f"media/{file.filename}"

            with open(file_path, "wb+") as buffer:
                shutil.copyfileobj(file.file, buffer)

            file_description = files_descriptions[index] if index < len(files_descriptions) else None
            new_file = EventFile(file_path=file_path, description=file_description)
                
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
                seats_number=event_time.seats_number
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


def get_event_info(event: Event):
    if event.event_dates:
        start_date = min(date.event_date for date in event.event_dates)
        end_date = max(date.event_date for date in event.event_dates)
    else:
        start_date = None
        end_date = None
    
    event_info = {
            "name": event.name,
            "start_date": start_date,
            "end_date": end_date,
            "city": event.city,
            "visit_cost": event.visit_cost,
            "format": event.format.value,
        }
    
    return event_info

def get_events(events: List[Event]):
    event_list = []
    for event in events:
        if event.event_dates:
            start_date = min(date.event_date for date in event.event_dates)
            end_date = max(date.event_date for date in event.event_dates)
        else:
            start_date = None
            end_date = None

        event_list.append({
            "id": event.id,
            "name": event.name,
            "start_date": start_date,
            "end_date": end_date,
            "city": event.city,
            "visit_cost": event.visit_cost,
            "format": event.format.value,
        })

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
