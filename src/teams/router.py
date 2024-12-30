from fastapi import APIRouter, Depends, UploadFile, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from teams.models import Team, UserTeam
from teams.schemas import CreateTeamSchema, InvitedUserSchema, TeamsInfoSchema, RemoveUserSchema, TeamMembersResponseSchema
from auth.models import User
from auth.utils import oauth_scheme
from events.utils import upload_photo, create_registration_link, decrypt_registration_link
from teams.utils import get_team, send_invite_to_team_email
from user_profile.utils import get_user_profile_by_email
from database import get_async_session
from s3 import S3Client, get_s3_client
from typing import Optional, List


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
        return "Invalid or expired registration link"
    
    if user_team.user_id:
        return "User is already part of the team"
    
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

    if not team:
        return "Team doesn't exist"
    
    new_user_team = UserTeam(
        user_id = user.id,
        team_id = team.id,
    )

    db.add(new_user_team)
    await db.commit()

    return {"msg": "Successfully joined the team"}


@router.post("/my/", response_model=List[TeamsInfoSchema])
async def get_my_teams(
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user = await get_user_profile_by_email(token, db)

    stmt = select(Team).join(UserTeam).where(UserTeam.user_id == user.id,
                                             UserTeam.is_admin == True)
    stmt_result = await db.execute(stmt)
    teams = stmt_result.scalars().all()
    response = []
    for team in teams:
        team_info = TeamsInfoSchema(id=team.id, name=team.name)
        response.append(team_info)
    
    return response


@router.post("/participate/", response_model=List[TeamsInfoSchema])
async def get_my_teams(
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user = await get_user_profile_by_email(token, db)

    stmt = select(Team).join(UserTeam).where(UserTeam.user_id == user.id,
                                             UserTeam.is_admin == False)
    stmt_result = await db.execute(stmt)
    teams = stmt_result.scalars().all()
    response = []
    for team in teams:
        team_info = TeamsInfoSchema(id=team.id, name=team.name)
        response.append(team_info)
    
    return response


@router.get("/members/{team_id}/", response_model=TeamMembersResponseSchema)
async def get_team_members(
    team_id: int,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
    ):
    user = await get_user_profile_by_email(token, db)
    
    stmt = select(UserTeam).where(UserTeam.team_id == team_id,
                                  UserTeam.user_id == user.id)
    stmt_result = await db.execute(stmt)
    user_team = stmt_result.scalar_one_or_none()

    if not user_team:
        raise HTTPException(detail="Team doesn't exist or user isn't member", status_code=404)
    
    stmt_members = (
        select(User.id, User.first_name, User.last_name, User.patronymic)
        .join(UserTeam, User.id == UserTeam.user_id)
        .where(UserTeam.team_id == team_id)
    )
    result = await db.execute(stmt_members)
    members = result.all()

    return {
        "team_id": team_id,
        "members": [
            {"id": member.id, 
             "first_name": member.first_name,
             "last_name": member.last_name,
             "patronymic": member.patronymic}
             for member in members
        ]
    }
    



@router.delete("/remove/{team_id}/")
async def remove_from_team(
    team_id: int,
    removed_user: RemoveUserSchema,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
    ):
    user = await get_user_profile_by_email(token, db)
    
    stmt = select(UserTeam).where(UserTeam.team_id == team_id,
                                  UserTeam.user_id == user.id,
                                  UserTeam.is_admin == True)
    stmt_result = await db.execute(stmt)
    admin_team = stmt_result.scalar_one_or_none()

    if not admin_team:
        raise HTTPException(detail="User isn't creator", status_code=404)
    
    stmt = select(UserTeam).where(UserTeam.team_id == team_id,
                                  UserTeam.user_id == removed_user.id,
                                  UserTeam.is_admin == False)
    stmt_result = await db.execute(stmt)
    user_team_removed = stmt_result.scalar_one_or_none()

    if not user_team_removed:
        raise HTTPException(detail="User is team creator or isn't team member", status_code=404)
    
    await db.delete(user_team_removed)
    await db.commit()

    return {"msg": "User was removed"}


@router.delete("/exit/{team_id}/")
async def exit_from_team(
    team_id: int,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user = await get_user_profile_by_email(token, db)
    
    stmt = select(UserTeam).where(UserTeam.team_id == team_id,
                                  UserTeam.user_id == user.id,
                                  UserTeam.is_admin == False)
    stmt_result = await db.execute(stmt)
    user_team_exited = stmt_result.scalar_one_or_none()

    if not user_team_exited:
        raise HTTPException(detail="User is team creator or isn't team member", status_code=404)
    
    await db.delete(user_team_exited)
    await db.commit()

    return {"msg": "Exit from team was successfull"}


@router.delete("/delete/{team_id}/")
async def delete_team(
    team_id: int,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user = await get_user_profile_by_email(token, db)
    
    stmt = select(Team).join(UserTeam).where(UserTeam.team_id == team_id,
                                             UserTeam.user_id == user.id,
                                             UserTeam.is_admin == True)
    stmt_result = await db.execute(stmt)
    admin_team = stmt_result.scalar_one_or_none()

    if not admin_team:
        raise HTTPException(detail="User isn't creator", status_code=404)
    
    await db.delete(admin_team)
    await db.commit()

    return {"msg": "Team was deleted"}