from typing import Any
from uuid import UUID as PyUUID
from fastapi import Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import decode_token, get_token_from_cookie, ACCESS_COOKIE
from app.db.session import get_db
from app.db.models import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = get_token_from_cookie(request, ACCESS_COOKIE)
    payload = decode_token(token, expected_type="access")
    user_id: str = payload.get("sub")  # type: ignore[assignment]

    result = await db.execute(select(User).where(User.id == PyUUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_gemini_client(
    x_gemini_api_key: str | None = Header(None, alias="X-Gemini-API-Key"),
    x_gemini_model: str | None = Header(None, alias="X-Gemini-Model"),
) -> Any:
    from fastapi import HTTPException, status
    from app.services.gemini_service import get_gemini_service_custom
    try:
        return get_gemini_service_custom(api_key=x_gemini_api_key, model=x_gemini_model)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
