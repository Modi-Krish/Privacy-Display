import uuid
from typing import Any
from fastapi import Depends, Request, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import decode_token
from app.services.firebase_admin_service import verify_firebase_token
from app.services.db_service import get_db_service

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    auth_header = request.headers.get("authorization")
    if not auth_header:
        # Check cookie fallback
        try:
            from app.core.security import get_token_from_cookie, ACCESS_COOKIE
            token = get_token_from_cookie(request, ACCESS_COOKIE)
        except Exception:
            raise credentials_exc
    else:
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise credentials_exc
        token = parts[1]

    db_service = get_db_service()
    
    # 1. Try custom JWT validation (Desktop client)
    try:
        payload = decode_token(token, expected_type="access")
        sub = payload.get("sub")
        if sub:
            try:
                user_id = uuid.UUID(sub)
            except ValueError:
                raise credentials_exc
            
            user = await db_service.get_user_by_id(user_id, db=db)
            if user and user.is_active:
                return user
    except Exception:
        # Decryption or validation failed, try Firebase token fallback
        pass

    # 2. Try Firebase ID token validation (Web dashboard)
    try:
        decoded_token = verify_firebase_token(token)
        email = decoded_token.get("email")
        if not email:
            raise credentials_exc
            
        user = await db_service.get_user_by_email(email, db=db)
        if not user:
            # Auto-provision user on first successful Web login
            user = await db_service.create_user(email=email, password_hash="firebase_auth", db=db)
            
        if user and user.is_active:
            return user
    except Exception:
        raise credentials_exc

    raise credentials_exc


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

