from sqlalchemy import Column, String, Integer, Enum, Float, Date, Time, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import enum


class ThemeEnum(enum.Enum):
    learning = "learning"
    management = "management"


class StatusEnum(enum.Enum):
    open = "open"
    close = "close"


class FormatEnum(enum.Enum):
    lecture = "lecture"
    seminar = "seminar"
    workshop = "workshop"
    master_class = "master_class"
    competition = "competition"
    meeting = "meeting"
    conference = "conference"
    panel_discussion = "panel_discussion"
    round_table = "round_table"
    pitch = "pitch"
    hackathon = "hackathon"
    online = "online"


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    theme = Column(Enum(ThemeEnum), nullable=False)
    description = Column(String, nullable=False)
    visit_cost = Column(Float, nullable=False)
    city = Column(String, nullable=True)
    address = Column(String, nullable=True)
    status = Column(Enum(StatusEnum), nullable=False)
    format = Column(Enum(FormatEnum), nullable=False)
    photo = Column(String, nullable=True)
    registration_link = Column(String, nullable=True)

    custom_fields = relationship("CustomField", back_populates="event_custom_field")
    event_dates = relationship("EventDate", back_populates="event_initiator")
    creator = relationship("User", back_populates="created_event", uselist=False)
    files = relationship("EventFile", back_populates="event_files")


class EventDate(Base):
    __tablename__ = "event_date"

    id = Column(Integer, primary_key=True)
    event_date = Column(Date, nullable=False)

    event_id = Column(Integer, ForeignKey("event.id"))
    event_initiator = relationship("Event", back_populates="event_dates")
    event_times = relationship("EventTime", back_populates="event_date_times")


class EventTime(Base):
    __tablename__ = "event_time"

    id = Column(Integer, primary_key=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    seats_number = Column(Integer, nullable=False)

    date_id = Column(Integer, ForeignKey("event_date.id"))
    event_date_times = relationship("EventDate", back_populates="event_times")


class CustomField(Base):
    __tablename__ = "custom_field"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    
    event_id = Column(Integer, ForeignKey("event.id"))
    event_custom_field = relationship("Event", back_populates="custom_fields")


class EventFile(Base):
    __tablename__ = "event_file"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    description = Column(String, nullable=True)

    event_id = Column(Integer, ForeignKey("event.id"))
    event_files = relationship("Event", back_populates="files")
