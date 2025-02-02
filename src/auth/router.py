from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from src.auth.schemas import UserRegisterSchema, UserLoginSchema, ChangePasswordSchema
from src.auth.utils import verify_password, get_password_hash, create_access_token, is_token_revoked, revoke_token, oauth_scheme
from src.auth.models import User
from src.user_profile.utils import get_user_profile_by_email
from src.database import get_async_session
from src.config import ACCESS_TOKEN_EXPIRE_MINUTES, SECRET_KEY, ALGORITHM
import jwt


router = APIRouter(
    prefix="/api/auth"
)

@router.post("/register/")
async def register_user(user: UserRegisterSchema, db: AsyncSession = Depends(get_async_session)):
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        password=hashed_password,
    )

    db.add(new_user)
    await db.commit()
    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    return {"msg": "User registered successfully", "access_token": access_token, "token_type": "bearer"}


@router.post("/login/")
async def login_user(user: UserLoginSchema, db: AsyncSession = Depends(get_async_session)):
    result = await db.execute(select(User).where(User.email == user.email))
    selected_user = result.scalar()
    if not selected_user or not verify_password(user.password, selected_user.password):
        raise HTTPException(status_code=400, detail="Incorrect name or password")
    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(data={"sub": selected_user.email}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout/")
async def logout_user(token: str = Depends(oauth_scheme), db: AsyncSession = Depends(get_async_session)):
    if await is_token_revoked(db, token):
        raise HTTPException(status_code=400, detail="Token already revoked")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        expires_at = datetime.fromtimestamp(payload["exp"])
        await revoke_token(db, token, expires_at)
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid token")
    
    return {"msg": "Successfully loged out"}


@router.post("/change-password/")
async def change_password(password: ChangePasswordSchema, token: str = Depends(oauth_scheme), db: AsyncSession = Depends(get_async_session)):
    user = await get_user_profile_by_email(token, db)

    hashed_password = get_password_hash(password.password)
    user.password = hashed_password

    await db.commit()

    return {"msg": "Password was changed"}
