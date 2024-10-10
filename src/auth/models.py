from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    patronymic = Column(String, nullable=True)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)


class RevokedToken(Base):
    __tablename__ = "revoked_token"

    id = Column(Integer, primary_key=True)
    token = Column(String, nullable=False, unique=True)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
