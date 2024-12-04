from sqlalchemy import Column, String, Integer, Enum, Float, Date, Time, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import enum


class StatusEnum(enum.Enum):
    open = "open"
    close = "close"


class FormatEnum(enum.Enum):
    accelerator = "Акселератор"
    workshop = "Воркшоп"
    meeting = "Встреча"
    exhibition = "Выставка"
    open_day = "День открытых дверей"
    conference = "Конференция"
    round_table = "Круглый стол"
    lecture = "Лекция"
    master_class = "Мастер-класс"
    methoda = "Метода"
    meetup = "Митап"
    panel_discussion = "Панельная дискуссия"
    pitch = "Питч"
    seminar = "Семинар"
    competition = "Соревнование"
    gathering = "Собрание"
    strategic_session = "Стратегическая сессия"
    foresight = "Форсайт"
    forum = "Форум"
    hackathon = "Хакатон"

    def __str__(self):
        return self.value


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    visit_cost = Column(Float, nullable=False)
    city = Column(String, nullable=True)
    address = Column(String, nullable=True)
    status = Column(Enum(StatusEnum), nullable=False)
    format = Column(Enum(FormatEnum, native_enum=False), nullable=False)
    photo = Column(String, nullable=True)
    registration_link = Column(String, nullable=True)
    creator_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    custom_fields = relationship("CustomField", back_populates="event_custom_field")
    event_dates = relationship("EventDate", back_populates="event_initiator")
    creator = relationship("User", back_populates="created_event")
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
    description = Column(String, nullable=True)

    date_id = Column(Integer, ForeignKey("event_date.id"))
    event_date_times = relationship("EventDate", back_populates="event_times")
    booking_time = relationship("Booking", back_populates="booking_date_time")


class CustomField(Base):
    __tablename__ = "custom_field"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    
    event_id = Column(Integer, ForeignKey("event.id"))
    event_custom_field = relationship("Event", back_populates="custom_fields")
    custom_values = relationship("CustomValue", back_populates="custom_fields_for_values", uselist=False)


class EventFile(Base):
    __tablename__ = "event_file"

    id = Column(Integer, primary_key=True)
    file_path = Column(String, nullable=False)
    description = Column(String, nullable=True)

    event_id = Column(Integer, ForeignKey("event.id"))
    event_files = relationship("Event", back_populates="files")


class Booking(Base):
    __tablename__ = "booking"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    event_time_id = Column(Integer, ForeignKey("event_time.id"))

    booking_values = relationship("CustomValue", back_populates="booking_custom_values")
    user_bookings = relationship("User", back_populates="bookings")
    booking_date_time = relationship("EventTime", back_populates="booking_time")


class CustomValue(Base):
    __tablename__ = "custom_value"

    id = Column(Integer, primary_key=True)
    value = Column(String, nullable=False)

    custom_field_id = Column(Integer, ForeignKey("custom_field.id"), unique=True)
    booking_id = Column(Integer, ForeignKey("booking.id"))

    custom_fields_for_values = relationship("CustomField", back_populates="custom_values")
    booking_custom_values = relationship("Booking", back_populates="booking_values")
