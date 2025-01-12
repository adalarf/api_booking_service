from fastapi import HTTPException
from src.auth.models import User
from src.auth.utils import get_email_from_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_profile_by_email(token: str, db: AsyncSession):
    email = await get_email_from_token(token, db)

    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user_profile = result.scalar_one_or_none()

    if user_profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return user_profile
