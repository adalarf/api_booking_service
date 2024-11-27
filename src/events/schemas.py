from pydantic import BaseModel, model_validator, field_validator, AnyHttpUrl
from typing import List, Optional
from datetime import date, time
from .models import StatusEnum, FormatEnum
import json


class EventTimeSchema(BaseModel):
    start_time: time
    end_time: time
    seats_number: int
    description: str


class EventDateSchema(BaseModel):
    event_date: date
    event_times: List[EventTimeSchema]


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
    event_dates: List[EventDateSchema]

    @field_validator("event_dates")
    def check_unique_event_dates(cls, event_dates: List[EventDateSchema]):
        unique_dates = set()
        for event_date in event_dates:
            if event_date.event_date in unique_dates:
                raise ValueError(f"Duplicate event date: {event_date.event_date}")
            unique_dates.add(event_date.event_date)
        return event_dates

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


class EventTimeRegistrationSchema(BaseModel):
    time_id: int


class EventDateRegistrationSchema(BaseModel):
    event_date_id: int
    event_time: EventTimeRegistrationSchema


class EventRegistrationSchema(BaseModel):
    custom_fields: List[CustomFieldSchema]
    event_date_time: EventDateRegistrationSchema


class EventStartAndEndTimeSchema(BaseModel):
    start_time: time
    end_time: time


class EventInfoSchema(BaseModel):
    id: int
    name: str
    start_date: Optional[date]
    end_date: Optional[date]
    start_date_times: Optional[List[EventStartAndEndTimeSchema]]
    end_date_times: Optional[List[EventStartAndEndTimeSchema]]
    city: str
    visit_cost: float
    format: FormatEnum
    photo_url: Optional[AnyHttpUrl]


class ContactsSchema(BaseModel):
    phone_number: str
    vk: str
    telegram: str
    whatsapp: str


class CreatorSchema(BaseModel):
    first_name: str
    last_name: str
    patronymic: str
    company: str
    photo_url: Optional[AnyHttpUrl]
    contacts: ContactsSchema


class TimeSlotsDescriptionSchema(BaseModel):
    date: date
    start_time: time
    end_time: time
    description: Optional[str]


class EventSchema(BaseModel):
    id: int
    name: str
    description: str
    start_date: Optional[date]
    end_date: Optional[date]
    start_date_times: Optional[List[EventStartAndEndTimeSchema]]
    end_date_times: Optional[List[EventStartAndEndTimeSchema]]
    city: str
    address: str
    visit_cost: float
    format: FormatEnum
    photo_url: Optional[AnyHttpUrl]
    total_bookings: int
    creator: CreatorSchema
    time_slots_descriptions: Optional[List[TimeSlotsDescriptionSchema]]


class FilterSchema(BaseModel):
    city: Optional[str] = None
    search: Optional[str] = None
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    format: Optional[FormatEnum] = None