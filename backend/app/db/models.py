import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    String, Text, UniqueConstraint, Uuid,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── User ──────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Uuid, primary_key=True, default=_uuid)
    email         = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    is_active     = Column(Boolean, default=True, nullable=False)
    created_at    = Column(DateTime(timezone=True), default=_now, nullable=False)

    profile          = relationship("Profile", back_populates="user", uselist=False,
                                    cascade="all, delete-orphan")
    resumes          = relationship("Resume", back_populates="user",
                                    cascade="all, delete-orphan")
    projects         = relationship("Project", back_populates="user",
                                    cascade="all, delete-orphan")
    skills           = relationship("Skill", back_populates="user",
                                    cascade="all, delete-orphan")
    interview_sessions = relationship("InterviewSession", back_populates="user",
                                    cascade="all, delete-orphan")


# ── Profile ───────────────────────────────────────────────────────────────────

class Profile(Base):
    __tablename__ = "profiles"

    id        = Column(Uuid, primary_key=True, default=_uuid)
    user_id   = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"),
                       nullable=False, unique=True)
    full_name = Column(String(255), nullable=True)
    summary   = Column(Text, nullable=True)

    user = relationship("User", back_populates="profile")


# ── Resume ────────────────────────────────────────────────────────────────────

class Resume(Base):
    __tablename__ = "resumes"

    id             = Column(Uuid, primary_key=True, default=_uuid)
    user_id        = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"),
                            nullable=False, index=True)
    file_name      = Column(String(255), nullable=False)
    extracted_text = Column(Text, nullable=True)
    uploaded_at    = Column(DateTime(timezone=True), default=_now, nullable=False)

    user = relationship("User", back_populates="resumes")


# ── Project ───────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id           = Column(Uuid, primary_key=True, default=_uuid)
    user_id      = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    title        = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    technologies = Column(Text, nullable=True)   # comma-separated or JSON string

    user = relationship("User", back_populates="projects")


# ── Skill ─────────────────────────────────────────────────────────────────────

class Skill(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_name"),)

    id         = Column(Uuid, primary_key=True, default=_uuid)
    user_id    = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False)
    skill_name = Column(String(255), nullable=False)

    user = relationship("User", back_populates="skills")


# ── Interview Session ─────────────────────────────────────────────────────────

class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id         = Column(Uuid, primary_key=True, default=_uuid)
    user_id    = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    ended_at   = Column(DateTime(timezone=True), nullable=True)

    user      = relationship("User", back_populates="interview_sessions")
    questions = relationship("Question", back_populates="session",
                             cascade="all, delete-orphan")


# ── Question ──────────────────────────────────────────────────────────────────

class Question(Base):
    __tablename__ = "questions"

    id            = Column(Uuid, primary_key=True, default=_uuid)
    session_id    = Column(Uuid,
                           ForeignKey("interview_sessions.id", ondelete="CASCADE"),
                           nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    category      = Column(String(50), nullable=True)
    created_at    = Column(DateTime(timezone=True), default=_now, nullable=False)

    session  = relationship("InterviewSession", back_populates="questions")
    response = relationship("Response", back_populates="question", uselist=False,
                            cascade="all, delete-orphan")


# ── Response ──────────────────────────────────────────────────────────────────

class Response(Base):
    __tablename__ = "responses"

    id               = Column(Uuid, primary_key=True, default=_uuid)
    question_id      = Column(Uuid,
                              ForeignKey("questions.id", ondelete="CASCADE"),
                              nullable=False, unique=True)
    answer           = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    generated_prompt = Column(Text, nullable=True)

    question = relationship("Question", back_populates="response")
