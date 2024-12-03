from fastapi import APIRouter, Depends, UploadFile, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from teams.models import Team, UserTeam
from teams.schemas import CreateTeamSchema, InvitedUserSchema
from auth.utils import oauth_scheme
from events.utils import upload_photo, create_registration_link, decrypt_registration_link
from teams.utils import get_team, send_invite_to_team_email
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



@router.post("/create-link/{team_id}/")
async def create_link_for_registration(team_id: int,
                             token: str = Depends(oauth_scheme),
                             db: AsyncSession = Depends(get_async_session)):
    team = await get_team(team_id, db)
    
    if team.registration_link:
        return {"registraion_link": {team.registration_link}}
    
    registration_link = create_registration_link(team_id)
    team.registration_link = registration_link

    await db.commit()

    return {"registration_link": f"/api/teams/join-invitation/{team.registration_link}/"}


@router.post("/invite/{team_id}/")
async def invite_in_team(team_id: int,
                         invited_user_email: InvitedUserSchema,
                         token: str = Depends(oauth_scheme),
                         db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)
    team = await get_team(team_id, db)

    registration_link = create_registration_link(team_id)
    new_user_team = UserTeam(
        team_id=team_id,
        registration_link=registration_link
    )
    db.add(new_user_team)
    await db.commit()

    if user.id != team.creator_id and user not in team.members:
        return {"msg": "User is not a member of the team"}
    
    await send_invite_to_team_email(new_user_team.registration_link, team.name, invited_user_email)
    return {"msg": "Invite link was send"}


@router.post("/join-link/{registration_link}/")
async def join_to_team_through_registration_link(
    registration_link: str,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)

    stmt = select(UserTeam).where(
        UserTeam.registration_link == registration_link
    )
    result = await db.execute(stmt)
    user_team = result.scalar_one_or_none()

    if not user_team:
        raise "Invalid or expired registration link"
    
    if user_team.user_id:
        raise "User is already part of the team"
    
    user_team.user_id = user.id
    user_team.registration_link = None

    stmt_team = select(Team).where(Team.id == user_team.team_id)
    result_team = await db.execute(stmt_team)
    team = result_team.scalar_one_or_none()

    if not team:
        raise "Team not found"

    await db.commit()
    await db.refresh(user_team)

    return {"msg": "Successfully joined the team"}


@router.post("/join-invitation/{registration_link}/")
async def join_to_team_through_invitation(
    registration_link: str,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)

    stmt = select(Team).where(Team.registration_link == registration_link)
    stmt_result = await db.execute(stmt)
    team = stmt_result.scalar_one_or_none()

    new_user_team = UserTeam(
        user_id = user.id,
        team_id = team.id,
    )

    db.add(new_user_team)
    await db.commit()

    return {"msg": "Successfully joined the team"}
    