from pydantic import BaseModel


class UserRegisterSchema(BaseModel):
    first_name: str
    last_name: str
    patronymic: str
    email: str
    password: str


class UserLoginSchema(BaseModel):
    email: str
    password: str
