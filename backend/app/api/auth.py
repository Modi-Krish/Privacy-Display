import uuid
import json
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.db.session import get_db
from app.db.models import User, Device, PairingCode, Session, AuditLog
from app.core.security import (
    generate_pairing_code,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password
)
from app.core.rate_limiter import is_rate_limited
from app.core.logging import get_logger

import firebase_admin
from firebase_admin import auth as fb_auth

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

class WebLoginRequest(BaseModel):
    firebase_token: str

class PairingVerifyRequest(BaseModel):
    code: str
    device_id: str
    device_name: str | None = None

class RefreshRequest(BaseModel):
    refresh_token: str


# ── 1. Web Portal Login ───────────────────────────────────────────────────────

@router.post("/web/login")
async def web_login(req: WebLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if settings.DEBUG and not firebase_admin._apps:
            import jwt
            decoded_token = jwt.decode(req.firebase_token, options={"verify_signature": False})
        else:
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
        
        # Log new registration
        log = AuditLog(
            user_id=user.id,
            action="user_registered",
            details=json.dumps({"email": email})
        )
        db.add(log)
        await db.commit()
    else:
        # Log successful web login
        log = AuditLog(
            user_id=user.id,
            action="user_web_login",
            details=json.dumps({"email": email})
        )
        db.add(log)
        await db.commit()
    
    return {"user_id": user.id, "email": user.email}


# ── 2. Web Portal Generate Code ───────────────────────────────────────────────

@router.post("/web/pair/generate")
async def generate_code(req: WebLoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        from app.core.config import get_settings
        settings = get_settings()
        if settings.DEBUG and not firebase_admin._apps:
            import jwt
            decoded_token = jwt.decode(req.firebase_token, options={"verify_signature": False})
        else:
            decoded_token = fb_auth.verify_id_token(req.firebase_token)
        email = decoded_token.get("email")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    code_str = generate_pairing_code()
    # Validity reduced to 2 minutes
    expires = datetime.now(timezone.utc) + timedelta(minutes=2)
    
    # Cryptographically hash the code before saving
    hashed_code = hash_password(code_str)
    
    code_obj = PairingCode(
        user_id=user.id,
        code=hashed_code,
        expires_at=expires
    )
    db.add(code_obj)
    
    log = AuditLog(
        user_id=user.id,
        action="pairing_code_generated",
        details=json.dumps({"expires_at": expires.isoformat()})
    )
    db.add(log)
    
    await db.commit()
    return {"code": code_str, "expires_at": expires}


# ── 3. Desktop Verify Code ────────────────────────────────────────────────────

@router.post("/desktop/pair/verify")
async def verify_code(
    request: Request,
    req: PairingVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    ip = request.client.host if request.client else "unknown"
    
    # Enforce Rate Limiting
    # 5 attempts per minute per IP
    if await is_rate_limited(f"rate_limit:pair:ip:{ip}", 5, 60):
        # Audit rate limit breach
        log = AuditLog(
            action="rate_limit_breached_ip",
            ip_address=ip,
            device_id=req.device_id,
            details=json.dumps({"reason": "IP pairing limit exceeded (5/min)"})
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts. Try again later.")
        
    # 10 attempts per hour per device
    if await is_rate_limited(f"rate_limit:pair:dev:{req.device_id}", 10, 3600):
        log = AuditLog(
            action="rate_limit_breached_device",
            ip_address=ip,
            device_id=req.device_id,
            details=json.dumps({"reason": "Device pairing limit exceeded (10/hour)"})
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Device blocked due to too many attempts.")

    # Select all active, unused, unexpired pairing codes
    now_utc = datetime.now(timezone.utc)
    result = await db.execute(
        select(PairingCode)
        .where(PairingCode.used.is_(False))
        .where(PairingCode.expires_at > now_utc)
    )
    active_codes = result.scalars().all()
    
    matched_code_obj = None
    for code_obj in active_codes:
        if verify_password(req.code, code_obj.code):
            matched_code_obj = code_obj
            break
            
    if not matched_code_obj:
        # Audit failed pairing attempt
        log = AuditLog(
            action="failed_pairing_attempt",
            ip_address=ip,
            device_id=req.device_id,
            details=json.dumps({"reason": "Invalid pairing code"})
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired code")
        
    # Block if code has been locked
    if matched_code_obj.attempts >= 5:
        raise HTTPException(status_code=400, detail="Pairing code locked due to too many attempts")
        
    matched_code_obj.used = True
    matched_code_obj.attempts += 1
    
    # Register/Update Device
    dev_result = await db.execute(
        select(Device)
        .where(Device.device_id == req.device_id)
        .where(Device.user_id == matched_code_obj.user_id)
    )
    device = dev_result.scalar_one_or_none()
    if not device:
        device = Device(
            user_id=matched_code_obj.user_id,
            device_id=req.device_id,
            device_name=req.device_name
        )
        db.add(device)
    device.last_seen = datetime.now(timezone.utc)
    
    # Generate Session ID and Family ID for Token Rotation
    session_id = uuid.uuid4()
    family_id = uuid.uuid4()
    
    # Generate Tokens holding the session ID in claims
    access_token = create_access_token(matched_code_obj.user_id, session_id=session_id)
    refresh_token = create_refresh_token(matched_code_obj.user_id, session_id=session_id)
    
    # Bcrypt-hash the refresh token before storage
    hashed_refresh_token = hash_password(refresh_token)
    
    # Create session tracking record
    session_obj = Session(
        id=session_id,
        user_id=matched_code_obj.user_id,
        device_id=req.device_id,
        refresh_token_hash=hashed_refresh_token,
        family_id=family_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        last_used_at=datetime.now(timezone.utc)
    )
    db.add(session_obj)
    
    log = AuditLog(
        user_id=matched_code_obj.user_id,
        action="device_paired",
        ip_address=ip,
        device_id=req.device_id,
        details=json.dumps({"session_id": str(session_id), "family_id": str(family_id)})
    )
    db.add(log)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user_id": matched_code_obj.user_id
    }


# ── 4. Refresh Token Rotation (RTR) ───────────────────────────────────────────

@router.post("/desktop/refresh")
async def refresh_tokens(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(req.refresh_token, expected_type="refresh")
        user_id = payload.get("sub")
        session_id = payload.get("sid")
    except HTTPException:
        raise HTTPException(status_code=401, detail="Invalid refresh token claims")

    if not session_id or not user_id:
        raise HTTPException(status_code=401, detail="Malformed refresh token")

    # Fetch corresponding session record
    result = await db.execute(
        select(Session)
        .where(Session.id == uuid.UUID(session_id))
    )
    session_obj = result.scalar_one_or_none()
    
    if not session_obj:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Check for reuse/compromise: 
    # If the database session is already revoked, revoke the entire family lineage
    if session_obj.revoked_at is not None:
        await db.execute(
            update(Session)
            .where(Session.family_id == session_obj.family_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        # Log security violation
        log = AuditLog(
            user_id=session_obj.user_id,
            action="token_reuse_detected",
            device_id=session_obj.device_id,
            details=json.dumps({"session_id": str(session_obj.id), "family_id": str(session_obj.family_id)})
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=401, detail="Session compromised. Re-authentication required.")

    # Verify the incoming refresh token matches the hashed record
    if not verify_password(req.refresh_token, session_obj.refresh_token_hash):
        # Mismatched hash suggests token forgery or tampering. Invalidate family.
        await db.execute(
            update(Session)
            .where(Session.family_id == session_obj.family_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        log = AuditLog(
            user_id=session_obj.user_id,
            action="refresh_hash_mismatch",
            device_id=session_obj.device_id,
            details=json.dumps({"session_id": str(session_obj.id)})
        )
        db.add(log)
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid session credentials.")

    # Check absolute expiration
    if session_obj.expires_at < datetime.now(timezone.utc):
        session_obj.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        raise HTTPException(status_code=401, detail="Session expired")

    # Revoke current token from future direct use
    session_obj.revoked_at = datetime.now(timezone.utc)
    
    # Provision new rotated tokens
    new_session_id = uuid.uuid4()
    access_token = create_access_token(session_obj.user_id, session_id=new_session_id)
    new_refresh_token = create_refresh_token(session_obj.user_id, session_id=new_session_id)
    
    hashed_new_refresh = hash_password(new_refresh_token)
    
    new_session_obj = Session(
        id=new_session_id,
        user_id=session_obj.user_id,
        device_id=session_obj.device_id,
        refresh_token_hash=hashed_new_refresh,
        family_id=session_obj.family_id, # Link same lineage family
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        last_used_at=datetime.now(timezone.utc)
    )
    db.add(new_session_obj)
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token
    }


# ── 5. Logouts and Revocation ─────────────────────────────────────────────────

from app.core.deps import get_current_user  # noqa: E402

@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Invalidate active session matching request header
    auth_header = request.headers.get("authorization")
    if auth_header:
        try:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
                # Decode access token to retrieve sid
                payload = decode_token(token, expected_type="access")
                sid = payload.get("sid")
                if sid:
                    await db.execute(
                        update(Session)
                        .where(Session.id == uuid.UUID(sid))
                        .values(revoked_at=datetime.now(timezone.utc))
                    )
                    log = AuditLog(
                        user_id=current_user.id,
                        action="session_logout",
                        details=json.dumps({"session_id": sid})
                    )
                    db.add(log)
                    await db.commit()
        except Exception:
            pass
            
    return {"status": "ok"}


@router.post("/logout-all")
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Invalidate every login session associated with the user
    await db.execute(
        update(Session)
        .where(Session.user_id == current_user.id)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    
    log = AuditLog(
        user_id=current_user.id,
        action="logout_all_sessions"
    )
    db.add(log)
    await db.commit()
    
    return {"status": "ok"}


@router.delete("/devices/{device_id}")
async def revoke_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Revoke sessions associated with device
    await db.execute(
        update(Session)
        .where(Session.device_id == device_id, Session.user_id == current_user.id)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    
    # Remove device mapping
    await db.execute(
        delete(Device)
        .where(Device.device_id == device_id, Device.user_id == current_user.id)
    )
    
    log = AuditLog(
        user_id=current_user.id,
        action="device_revoked",
        device_id=device_id
    )
    db.add(log)
    await db.commit()
    
    return {"status": "ok"}
