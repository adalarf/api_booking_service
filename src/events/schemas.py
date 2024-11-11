from pydantic import BaseModel, model_validator, field_validator
from typing import List
from datetime import date, time
from .models import ThemeEnum, StatusEnum, FormatEnum
import json


class EventTimeSchema(BaseModel):
    start_time: time
    end_time: time
    seats_number: int


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
    theme: ThemeEnum
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
