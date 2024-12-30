from pydantic import BaseModel, AnyHttpUrl, model_validator, EmailStr
from typing import Optional, List
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


class TeamsInfoSchema(BaseModel):
    id: int
    name: str


class RemoveUserSchema(BaseModel):
    id: int


class TeamMemberSchema(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    patronymic: Optional[str] = None


class TeamMembersResponseSchema(BaseModel):
    team_id: int
    members: List[TeamMemberSchema]
