from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, AnyHttpUrl
from typing import Optional
from datetime import date
import re

class UserProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[date] = None
    city: Optional[str] = None
    phone_number: Optional[str] = None
    company_name: Optional[str] = None
    vk: Optional[str] = None
    telegram: Optional[str] = None
    whatsapp: Optional[str] = None
    photo: Optional[AnyHttpUrl] = None


class UserProfileUpdateSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic: Optional[str] = None
    email: Optional[EmailStr] = None
    birth_date: Optional[date] = None
    city: Optional[str] = None
    phone_number: Optional[str] = None
    company_name: Optional[str] = None
    vk: Optional[str] = None
    telegram: Optional[str] = None
    whatsapp: Optional[str] = None

    @field_validator('phone_number')
    def validate_phone_number(cls, value: str):
        phone_regex = r'^\+?\d{10,15}$'
        if value and not re.match(phone_regex, value):
            raise ValueError('Invalid phone number format. Use international format like +1234567890')
        return value
