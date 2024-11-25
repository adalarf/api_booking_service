from fastapi import APIRouter, Depends, HTTPException, UploadFile, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from auth.models import User
from auth.utils import oauth_scheme
from events.utils import upload_photo, get_event_photo_url
from user_profile.schemas import UserProfileSchema, UserProfileUpdateSchema
from user_profile.utils import get_user_profile_by_email
from s3 import S3Client, get_s3_client
from database import get_async_session
from typing import Optional


router = APIRouter(
    prefix="/api/profile"
)

@router.get("/me/", response_model=UserProfileSchema)
async def get_user_profile(token: str = Depends(oauth_scheme), s3_client: S3Client = Depends(get_s3_client), db: AsyncSession = Depends(get_async_session)):
    user_profile = await get_user_profile_by_email(token, db)
    user_profile.photo = get_event_photo_url(user_profile, s3_client)
    return UserProfileSchema.model_validate(user_profile)


@router.put("/me/")
@router.patch("/me/")
async def update_user_profile(
    profile_data: UserProfileUpdateSchema = Body(...),
    token: str = Depends(oauth_scheme),
    s3_client: S3Client = Depends(get_s3_client),
    photo: Optional[UploadFile] = UploadFile(None),
    db: AsyncSession = Depends(get_async_session)
):
    print(profile_data)
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

    photo_path = None
    if photo.filename:
        photo_path = await upload_photo(photo, photo.filename, s3_client)
        user_profile.photo = photo_path

    await db.commit()
    await db.refresh(user_profile)

    return {"msg": "Profile updated"}
