from pydantic import BaseModel, model_validator
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