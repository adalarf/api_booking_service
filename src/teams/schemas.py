from pydantic import BaseModel, AnyHttpUrl
from typing import Optional

class CreateTeamSchema(BaseModel):
    name: str
    description: Optional[str]


class TeamInfoSchema(BaseModel):
    name: str
    description: str
    photo_url: Optional[AnyHttpUrl]
    creator_id: int