from pydantic import BaseModel, model_validator, field_validator, AnyHttpUrl
from typing import List, Optional
from datetime import date, time
from .models import StatusEnum, FormatEnum
import json


class EventDateTimeSchema(BaseModel):
    start_date: date
    end_date: date
    start_time: time
    end_time: time
    seats_number: Optional[int] = None


class CustomFieldSchema(BaseModel):
    title: str


class EventFileSchema(BaseModel):
    file_path: str
    description: str


class EventCreateSchema(BaseModel):
    name: str
    description: str
    visit_cost: float
    city: str | None = None
    address: str | None = None
    status: StatusEnum
    format: FormatEnum
    custom_fields: List[CustomFieldSchema]
    event_dates_times: List[EventDateTimeSchema]

    @model_validator(mode='before')
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class EventCreateResponseSchema(BaseModel):
    msg: str
    event_id: int
    registration_link: str


class EmailSchema(BaseModel):
    email: str

class EventInviteSchema(BaseModel):
    event_id: int
    users_emails: List[EmailSchema]


class EventRegistrationSchema(BaseModel):
    custom_fields: List[CustomFieldSchema]
    event_date_time_id: int


class EventStartTimeSchema(BaseModel):
    start_time: time


class EventEndTimeSchema(BaseModel):
    end_time: time


class EventInfoSchema(BaseModel):
    id: int
    name: str
    start_date: Optional[date]
    end_date: Optional[date]
    start_time: Optional[time]
    end_time: Optional[time]
    city: str
    visit_cost: float
    format: FormatEnum
    state: str
    photo_url: Optional[AnyHttpUrl]


class ContactsSchema(BaseModel):
    email: str
    phone_number: Optional[str]
    vk: Optional[str]
    telegram: Optional[str]
    whatsapp: Optional[str]


class CreatorSchema(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    patronymic: Optional[str]
    company: Optional[str]
    photo_url: Optional[AnyHttpUrl]
    contacts: Optional[ContactsSchema]


class TimeSlotsDescriptionSchema(BaseModel):
    id: int
    start_date: date
    end_date: date
    start_time: time
    end_time: time
    seats_number: Optional[int]
    bookings_count: Optional[int]


class EventSchema(BaseModel):
    id: int
    name: str
    description: str
    start_date: Optional[date]
    end_date: Optional[date]
    start_time: Optional[time]
    end_time: Optional[time]
    city: str
    address: str
    visit_cost: float
    status: StatusEnum
    format: FormatEnum
    state: str
    photo_url: Optional[AnyHttpUrl]
    schedule_url: Optional[AnyHttpUrl]
    creator: CreatorSchema
    time_slots_descriptions: Optional[List[TimeSlotsDescriptionSchema]]


class FilterSchema(BaseModel):
    city: Optional[str] = None
    search: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    format: Optional[FormatEnum] = None


class MessageSchema(BaseModel):
    theme: str
    message: str
