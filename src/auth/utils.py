from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.models import RevokedToken
from sqlalchemy import delete, select, insert
from sqlalchemy.exc import NoResultFound
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException
from src.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


oauth_scheme = OAuth2PasswordBearer(tokenUrl="login/")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def revoke_token(db: AsyncSession, token: str, expires_at: datetime):
    stmt = insert(RevokedToken).values(token=token, expires_at=expires_at)
    await db.execute(stmt)
    await db.commit()


async def is_token_revoked(db: AsyncSession, token:str):
    stmt = select(RevokedToken).where(RevokedToken.token == token)
    try:
        result = await db.execute(stmt)
        result.scalar_one()
        return True
    except NoResultFound:
        return False


async def clean_revoked_tokens(db: AsyncSession):
    threshold = datetime.utcnow() - timedelta(days=7)
    stmt = delete(RevokedToken).where(RevokedToken.revoked_at < threshold)
    await db.execute(stmt)
    await db.commit()


async def get_email_from_token(token: str, db: AsyncSession) -> str:
    if await is_token_revoked(db, token):
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return email