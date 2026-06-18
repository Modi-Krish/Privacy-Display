from typing import Any
from uuid import UUID as PyUUID
from fastapi import Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    
    email = "default@example.com"
    user = await db_service.get_user_by_email(email, db=db)
    if not user:
        user = await db_service.create_user(email=email, password_hash="nopassword", db=db)

    if user is None or not user.is_active:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Default user not found or inactive",
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
