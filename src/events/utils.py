from fastapi import UploadFile, Body
from events.models import Event, EventFile, CustomField, EventDate, EventTime
from events.schemas import EventCreateSchema, EmailSchema
from cryptography.fernet import Fernet
from typing import List, Optional
from email.message import EmailMessage
from config import REGISTATION_LINK_CIPHER_KEY, EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_HOST, EMAIL_PORT
import shutil
import secrets
import aiosmtplib


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


def create_registration_link(event_id: str):
    secret = secrets.token_urlsafe()
    registration_link = f"/api/event/{event_id}/{secret}/register"
    return registration_link


def encrypt_registration_link(link: str):
    return cipher.encrypt(link.encode()).decode()


def decrypt_registration_link(encrypted_link: str) -> str:
    return cipher.decrypt(encrypted_link.encode()).decode()


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
