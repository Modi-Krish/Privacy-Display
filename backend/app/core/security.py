from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt
from fastapi import HTTPException, Request, status

from app.core.config import get_settings

settings = get_settings()


# ── Password Hashing ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── Pairing Codes ─────────────────────────────────────────────────────────────

def generate_pairing_code() -> str:
    import secrets
    # Generate a cryptographically secure token with 128-bit entropy (16 bytes)
    return secrets.token_urlsafe(16)


# ── JWT ───────────────────────────────────────────────────────────────────────

def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: UUID, session_id: UUID | None = None) -> str:
    payload = {"sub": str(user_id), "type": "access"}
    if session_id:
        payload["sid"] = str(session_id)
    return _create_token(
        payload,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: UUID, session_id: UUID | None = None) -> str:
    payload = {"sub": str(user_id), "type": "refresh"}
    if session_id:
        payload["sid"] = str(session_id)
    return _create_token(
        payload,
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != expected_type:
            raise credentials_exc
        return payload
    except JWTError:
        raise credentials_exc


# ── Cookie Helpers ────────────────────────────────────────────────────────────

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"

def get_cookie_defaults() -> dict[str, Any]:
    return dict(
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )


def set_auth_cookies(response: Any, user_id: UUID) -> None:
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    defaults = get_cookie_defaults()

    response.set_cookie(
        ACCESS_COOKIE, access,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **defaults,
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **defaults,
    )


def clear_auth_cookies(response: Any) -> None:
    defaults = get_cookie_defaults()
    response.delete_cookie(ACCESS_COOKIE, httponly=defaults["httponly"], samesite=defaults["samesite"], secure=defaults["secure"])
    response.delete_cookie(REFRESH_COOKIE, httponly=defaults["httponly"], samesite=defaults["samesite"], secure=defaults["secure"])


def get_token_from_cookie(request: Request, cookie_name: str) -> str:
    token = request.cookies.get(cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return token
