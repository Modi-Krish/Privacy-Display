from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import User, Device, PairingCode, Session
from app.core.security import (
    generate_pairing_code,
    create_access_token,
    create_refresh_token,
    decode_token
)

import firebase_admin
from firebase_admin import auth as fb_auth

router = APIRouter(prefix="/auth", tags=["auth"])

class WebLoginRequest(BaseModel):
    firebase_token: str

class PairingVerifyRequest(BaseModel):
    code: str
    device_id: str
    device_name: str | None = None

class RefreshRequest(BaseModel):
    refresh_token: str

# 1. Web Portal Login
@router.post("/web/login")
async def web_login(req: WebLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        decoded_token = fb_auth.verify_id_token(req.firebase_token)
        email = decoded_token.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="No email in Firebase token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase token: {e}")
    
    # Get or create user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        user = User(email=email, password_hash="firebase_auth")
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return {"user_id": user.id, "email": user.email}

# 2. Web Portal Generate Code
@router.post("/web/pair/generate")
async def generate_code(req: WebLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        decoded_token = fb_auth.verify_id_token(req.firebase_token)
        email = decoded_token.get("email")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    code_str = generate_pairing_code()
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    
    code_obj = PairingCode(
        user_id=user.id,
        code=code_str,
        expires_at=expires
    )
    db.add(code_obj)
    await db.commit()
    return {"code": code_str, "expires_at": expires}

# 3. Desktop Verify Code
@router.post("/desktop/pair/verify")
async def verify_code(req: PairingVerifyRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PairingCode)
        .where(PairingCode.code == req.code)
        .where(PairingCode.used == False)
    )
    code_obj = result.scalar_one_or_none()
    
    if not code_obj:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
        
    expires_at = code_obj.expires_at.replace(tzinfo=timezone.utc) if code_obj.expires_at.tzinfo is None else code_obj.expires_at
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Code expired")
        
    if code_obj.attempts >= 5:
        raise HTTPException(status_code=400, detail="Too many attempts")
        
    code_obj.used = True
    code_obj.attempts += 1
    
    # Register/Update Device
    dev_result = await db.execute(
        select(Device)
        .where(Device.device_id == req.device_id)
        .where(Device.user_id == code_obj.user_id)
    )
    device = dev_result.scalar_one_or_none()
    if not device:
        device = Device(
            user_id=code_obj.user_id,
            device_id=req.device_id,
            device_name=req.device_name
        )
        db.add(device)
    device.last_seen = datetime.now(timezone.utc)
    
    # Generate Tokens
    access_token = create_access_token(code_obj.user_id)
    refresh_token = create_refresh_token(code_obj.user_id)
    
    # Create Session
    session_obj = Session(
        user_id=code_obj.user_id,
        device_id=req.device_id,
        refresh_token_hash=refresh_token, # Should hash in prod, using raw for simplicity
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(session_obj)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": code_obj.user_id
    }

# 4. Refresh Token
@router.post("/desktop/refresh")
async def refresh_tokens(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(req.refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
        
    # verify session
    result = await db.execute(
        select(Session)
        .where(Session.refresh_token_hash == req.refresh_token)
        .where(Session.expires_at > datetime.now(timezone.utc))
    )
    session_obj = result.scalar_one_or_none()
    if not session_obj:
        raise HTTPException(status_code=401, detail="Session expired or revoked")
        
    access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)
    
    session_obj.refresh_token_hash = new_refresh_token
    session_obj.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token
    }
