from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from typing import Optional
import re


class UserProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    phone_number: Optional[str] = None
    company_name: Optional[str] = None
    vk: Optional[str] = None
    telegram: Optional[str] = None
    whatsapp: Optional[str] = None


class UserProfileUpdateSchema(BaseModel):
    first_name: str = None
    last_name: str = None
    patronymic: str = None
    email: EmailStr
    age: int = None
    city: str = None
    phone_number: str = None
    company_name: str = None
    vk: str = None
    telegram: str = None
    whatsapp: str = None

    @field_validator('phone_number')
    def validate_phone_number(cls, value: str):
        phone_regex = r'^\+?\d{10,15}$'
        if value and not re.match(phone_regex, value):
            raise ValueError('Invalid phone number format. Use international format like +1234567890')
        return value
