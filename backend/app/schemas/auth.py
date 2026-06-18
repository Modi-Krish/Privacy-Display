from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID
from datetime import datetime


# ── Register ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Responses ─────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: UUID
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    message: str
    user: UserOut


# ── Profile ───────────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    full_name: str | None = None
    summary: str | None = None


class ProfileOut(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str | None
    summary: str | None

    model_config = {"from_attributes": True}

