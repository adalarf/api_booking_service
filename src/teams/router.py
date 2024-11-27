from fastapi import APIRouter, Depends, UploadFile, Body
from sqlalchemy.ext.asyncio import AsyncSession
from teams.models import Team, UserTeam
from teams.schemas import CreateTeamSchema
from auth.utils import oauth_scheme
from events.utils import upload_photo, get_event_photo_url
from user_profile.utils import get_user_profile_by_email
from database import get_async_session
from s3 import S3Client, get_s3_client
from typing import Optional


router = APIRouter(
    prefix="/api/teams"
)

@router.post("/create/")
async def create_team(
    team: CreateTeamSchema = Body(...),
    token: str = Depends(oauth_scheme),
    s3_client: S3Client = Depends(get_s3_client),
    db: AsyncSession = Depends(get_async_session),
    photo: Optional[UploadFile] = UploadFile(None)
    ):
    user = await get_user_profile_by_email(token, db)

    photo_path = None
    if photo.filename:
        photo_path = await upload_photo(photo, photo.filename, s3_client)

    new_team = Team(
        name=team.name,
        description=team.description,
        photo=photo_path,
        creator_id=user.id,
    )

    db.add(new_team)
    await db.flush()

    user_team = UserTeam(
        user_id=user.id,
        team_id=new_team.id,
        is_admin=True,
    )
    db.add(user_team)
    await db.commit()

    return new_team
