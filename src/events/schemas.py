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
    title: Optional[str]


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
    online_link: Optional[AnyHttpUrl] = None
    custom_fields: Optional[List[CustomFieldSchema]] = []
    event_dates_times: List[EventDateTimeSchema]

    @model_validator(mode='before')
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value

class UpdateEventDateTimeSchema(BaseModel):
    id: Optional[int] = None
    start_date: date
    end_date: date
    start_time: time
    end_time: time
    seats_number: Optional[int] = None


class UpdateCustomFieldSchema(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None


class EventUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    visit_cost: Optional[float] = None
    city: Optional[str] = None
    address: Optional[str] = None
    status: Optional[StatusEnum] = None
    format: Optional[FormatEnum] = None
    custom_fields: Optional[List[UpdateCustomFieldSchema]] = []
    event_dates_times: Optional[List[UpdateEventDateTimeSchema]] = []

    @model_validator(mode='before')
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class FilledCustomFieldsResponseSchema(BaseModel):
    filled_custom_fields: Optional[List[int]] = []


class EventCreateResponseSchema(BaseModel):
    msg: str
    event_id: int
    event_link: str


class EmailSchema(BaseModel):
    email: str


class EventInviteSchema(BaseModel):
    event_id: int
    users_emails: List[EmailSchema]


class CustomFieldsRegistrationSchema(BaseModel):
    title: str
    value: str


class EventRegistrationSchema(BaseModel):
    custom_fields: Optional[List[CustomFieldsRegistrationSchema]] = []
    event_date_time_id: int
    expiration_days: Optional[int] = None

    @field_validator("expiration_days", mode="before")
    def validate_expiration_days(cls, value):
        allowed_values = [15, 30, 60, 90]
        if value is not None and value not in allowed_values:
            raise ValueError(f"Expiration days must be one of {allowed_values}")
        return value


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

class CustomFieldAndValueSchema(BaseModel):
    field_title: str
    field_value: str


class MemberSchema(BaseModel):
    id: int
    first_name: Optional[str]
    last_name: Optional[str]
    patronymic: Optional[str]
    email: str
    phone_number: Optional[str]
    vk: Optional[str]
    telegram: Optional[str]
    whatsapp: Optional[str]
    photo: Optional[AnyHttpUrl]
    custom_fields: List[CustomFieldAndValueSchema]


class EventDateTimeMembersSchema(BaseModel):
    id: int
    start_date: str
    end_date: str
    start_time: str
    end_time: str
    seats_number: Optional[int]
    bookings_count: Optional[int]
    members: List[MemberSchema]


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
    online_link: Optional[AnyHttpUrl] = None
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


class ChangeOnlineLinkSchema(BaseModel):
    online_link: AnyHttpUrl


class TeamInvitationSchema(BaseModel):
    team_id: int