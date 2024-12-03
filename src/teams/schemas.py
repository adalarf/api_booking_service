from pydantic import BaseModel, AnyHttpUrl, model_validator, EmailStr
from typing import Optional
import json

class CreateTeamSchema(BaseModel):
    name: str
    description: Optional[str]

    @model_validator(mode='before')
    @classmethod
    def validate_to_json(cls, value):
        if isinstance(value, str):
            return cls(**json.loads(value))
        return value


class TeamInfoSchema(BaseModel):
    name: str
    description: str
    photo_url: Optional[AnyHttpUrl]
    creator_id: int


class InvitedUserSchema(BaseModel):
    email: EmailStr