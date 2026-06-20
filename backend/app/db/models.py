import uuid
import json
from datetime import datetime, timezone
import numpy as np

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint, Uuid,
)
from sqlalchemy.types import UserDefinedType, TypeDecorator
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.core.encryption import encrypt_string, decrypt_string


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Custom SQL Types ──────────────────────────────────────────────────────────

class EncryptedString(TypeDecorator):
    """
    Transparently encrypts sensitive values before inserting into the DB
    and decrypts them after retrieval. Falls back to impl (Text).
    """
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_string(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_string(value)


class Vector(UserDefinedType):
    """
    Custom Vector type that maps to 'VECTOR(dim)' in PostgreSQL (pgvector)
    and falls back to JSON text storage in SQLite (for local development/tests).
    """
    def __init__(self, dim: int):
        self.dim = dim

    def get_col_spec(self, **kw):
        return f"VECTOR({self.dim})"

    def bind_processor(self, dialect):
        if dialect.name == "sqlite":
            def process(value):
                return json.dumps(value.tolist() if hasattr(value, "tolist") else value) if value is not None else None
            return process
        else:
            def process(value):
                if value is None:
                    return None
                if hasattr(value, "tolist"):
                    value = value.tolist()
                return f"[{','.join(map(str, value))}]"
            return process

    def result_processor(self, dialect, coltype):
        if dialect.name == "sqlite":
            def process(value):
                return np.array(json.loads(value), dtype=np.float32) if value is not None else None
            return process
        else:
            def process(value):
                if value is None:
                    return None
                cleaned = value.strip("[]")
                if not cleaned:
                    return np.array([], dtype=np.float32)
                return np.array([float(x) for x in cleaned.split(",")], dtype=np.float32)
            return process


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
    extracted_text = Column(EncryptedString, nullable=True) # Encrypted
    uploaded_at    = Column(DateTime(timezone=True), default=_now, nullable=False)

    user = relationship("User", back_populates="resumes")


# ── Resume Chunk (pgvector chunks) ───────────────────────────────────────────

class ResumeChunk(Base):
    __tablename__ = "resume_chunks"

    id           = Column(Uuid, primary_key=True, default=_uuid)
    user_id      = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id    = Column(Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=True, index=True)
    chunk_text   = Column(EncryptedString, nullable=False) # Encrypted
    embedding    = Column(Vector(384), nullable=False) # pgvector column fallback
    source       = Column(String(50), nullable=False)
    section      = Column(String(255), nullable=False)
    item_id      = Column(String(255), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True) # SHA-256 deduplication hash


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
    question_text = Column(EncryptedString, nullable=False) # Encrypted
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
    answer           = Column(EncryptedString, nullable=True) # Encrypted
    confidence_score = Column(Float, nullable=True)
    generated_prompt = Column(EncryptedString, nullable=True) # Encrypted

    question = relationship("Question", back_populates="response")


# ── Auth & Devices ────────────────────────────────────────────────────────────

class Device(Base):
    __tablename__ = "devices"

    id          = Column(Uuid, primary_key=True, default=_uuid)
    user_id     = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id   = Column(String(255), nullable=False, unique=True, index=True)
    device_name = Column(String(255), nullable=True)
    created_at  = Column(DateTime(timezone=True), default=_now, nullable=False)
    last_seen   = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")


class PairingCode(Base):
    __tablename__ = "pairing_codes"

    id         = Column(Uuid, primary_key=True, default=_uuid)
    user_id    = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code       = Column(String(255), nullable=False, unique=True, index=True) # Holds bcrypt hash
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used       = Column(Boolean, default=False, nullable=False)
    attempts   = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    user = relationship("User")


class Session(Base):
    """
    User login sessions for Desktop clients.
    Supports Refresh Token Rotation (RTR).
    """
    __tablename__ = "sessions"

    id                 = Column(Uuid, primary_key=True, default=_uuid)
    user_id            = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id          = Column(String(255), nullable=False, index=True)
    refresh_token_hash = Column(Text, nullable=False, unique=True) # Bcrypt hash
    family_id          = Column(Uuid, nullable=False, index=True) # RTR Lineage identifier
    revoked_at         = Column(DateTime(timezone=True), nullable=True) # Set on reuse detection or signout
    last_used_at       = Column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at         = Column(DateTime(timezone=True), nullable=False)
    created_at         = Column(DateTime(timezone=True), default=_now, nullable=False)

    user = relationship("User")


# ── Cloud Sync & Dashboard Additions ──────────────────────────────────────────

class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id             = Column(Uuid, primary_key=True, default=_uuid)
    resume_id      = Column(Uuid, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    file_name      = Column(String(255), nullable=False)
    extracted_text = Column(EncryptedString, nullable=True) # Encrypted
    uploaded_at    = Column(DateTime(timezone=True), default=_now, nullable=False)

    resume = relationship("Resume")


class SessionMessage(Base):
    __tablename__ = "session_messages"

    id           = Column(Uuid, primary_key=True, default=_uuid)
    session_id   = Column(Uuid, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    message_type = Column(String(50), nullable=False)  # "question", "retrieved_context", "answer"
    content      = Column(EncryptedString, nullable=False) # Encrypted
    created_at   = Column(DateTime(timezone=True), default=_now, nullable=False)

    session = relationship("InterviewSession")


class BrowserState(Base):
    __tablename__ = "browser_states"

    id             = Column(Uuid, primary_key=True, default=_uuid)
    user_id        = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    pinned_tabs    = Column(EncryptedString, nullable=True) # Encrypted JSON
    allowed_domains= Column(EncryptedString, nullable=True) # Encrypted JSON
    blocked_domains= Column(EncryptedString, nullable=True) # Encrypted JSON
    updated_at     = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User")


class UserSetting(Base):
    __tablename__ = "user_settings"

    id              = Column(Uuid, primary_key=True, default=_uuid)
    user_id         = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    theme           = Column(String(50), default="dark")
    overlay_mode    = Column(String(50), default="default")
    hotkeys         = Column(EncryptedString, nullable=True) # Encrypted JSON
    ai_preferences  = Column(EncryptedString, nullable=True) # Encrypted JSON
    updated_at      = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    user = relationship("User")


class Analytics(Base):
    __tablename__ = "analytics"

    id           = Column(Uuid, primary_key=True, default=_uuid)
    user_id      = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type   = Column(String(255), nullable=False)
    event_data   = Column(EncryptedString, nullable=True) # Encrypted JSON
    created_at   = Column(DateTime(timezone=True), default=_now, nullable=False)

    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id           = Column(Uuid, primary_key=True, default=_uuid)
    user_id      = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    action       = Column(String(255), nullable=False)
    ip_address   = Column(String(50), nullable=True)
    device_id    = Column(String(255), nullable=True)
    details      = Column(EncryptedString, nullable=True) # Encrypted JSON details
    created_at   = Column(DateTime(timezone=True), default=_now, nullable=False)

    user = relationship("User")
