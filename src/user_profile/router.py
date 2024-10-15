from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth.models import User
from auth.utils import oauth_scheme
from user_profile.schemas import UserProfileSchema, UserProfileUpdateSchema
from user_profile.utils import get_user_profile_by_email
from database import get_async_session


router = APIRouter(
    prefix="/api/profile"
)

@router.get("/me/", response_model=UserProfileSchema)
async def get_user_profile(token: str = Depends(oauth_scheme), db: AsyncSession = Depends(get_async_session)):
    user_profile = await get_user_profile_by_email(token, db)
    return UserProfileSchema.model_validate(user_profile)


@router.put("/me/", response_model=UserProfileSchema)
@router.patch("/me/", response_model=UserProfileSchema)
async def update_user_profile(
    profile_data: UserProfileUpdateSchema,
    token: str = Depends(oauth_scheme),
    db: AsyncSession = Depends(get_async_session)
):
    user_profile = await get_user_profile_by_email(token, db)
    
    if profile_data.email:
        email_check_stmt = select(User).where(User.email == profile_data.email)
        email_check_result = await db.execute(email_check_stmt)
        existing_user = email_check_result.scalar_one_or_none()

        if existing_user and existing_user.id != user_profile.id:
            raise HTTPException(status_code=400, detail="This email is already taken.")

    updated_fields = profile_data.model_dump(exclude_unset=True)
    if updated_fields:
        for field, value in updated_fields.items():
            setattr(user_profile, field, value)
        await db.commit()
    
    await db.refresh(user_profile)

    return user_profile
