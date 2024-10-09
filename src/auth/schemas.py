from pydantic import BaseModel, EmailStr, field_validator


class UserRegisterSchema(BaseModel):
    first_name: str
    last_name: str
    patronymic: str
    email: EmailStr
    password: str

    @field_validator('password')
    def validate_password(cls, value: str):
        if len(value) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(char.isdigit() for char in value):
            raise ValueError('Password must contain at least one number')
        if not any(char.isalpha() for char in value):
            raise ValueError('Password must contain at least one letter')
        return value


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str
