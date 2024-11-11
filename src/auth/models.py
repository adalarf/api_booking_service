from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    patronymic = Column(String, nullable=True)
    email = Column(String, nullable=False, unique=True)
    age = Column(Integer, nullable=True)
    city = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    vk = Column(String, nullable=True)
    telegram = Column(String, nullable=True)
    whatsapp = Column(String, nullable=True)
    password = Column(String, nullable=False)

    event_id = Column(Integer, ForeignKey("event.id"), unique=True)
    created_event = relationship("Event", back_populates="creator")

    bookings = relationship("Booking", back_populates="user_bookings", uselist=False)


class RevokedToken(Base):
    __tablename__ = "revoked_token"

    id = Column(Integer, primary_key=True)
    token = Column(String, nullable=False, unique=True)
    revoked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
