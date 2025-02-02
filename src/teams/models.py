from sqlalchemy import Column, String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from src.database import Base


class Team(Base):
    __tablename__ = "team"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    photo = Column(String, nullable=True)
    creator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    registration_link = Column(String, nullable=True)

    creator = relationship("User", back_populates="created_teams")
    members = relationship("UserTeam", back_populates="team", cascade="all, delete")


class UserTeam(Base):
    __tablename__ = "user_team"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    team_id = Column(Integer, ForeignKey("team.id", ondelete="CASCADE"), nullable=False)
    is_admin = Column(Boolean, default=False)
    registration_link = Column(String, nullable=True)

    user = relationship("User", back_populates="user_teams")
    team = relationship("Team", back_populates="members")