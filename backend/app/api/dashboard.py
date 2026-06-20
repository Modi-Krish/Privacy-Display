import uuid
import json
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.db.models import User, InterviewSession, Question, Response, Device, SessionMessage, Resume, UserSetting, BrowserState
from app.core.redis import get_cache, set_cache, delete_cache
from pydantic import BaseModel

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"user_stats:{current_user.id}"
    cached = await get_cache(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    # Total sessions
    sessions_count = await db.scalar(
        select(func.count()).select_from(InterviewSession).where(InterviewSession.user_id == current_user.id)
    )
    
    # Active devices
    devices_count = await db.scalar(
        select(func.count()).select_from(Device).where(Device.user_id == current_user.id)
    )
    
    # Total Questions
    questions_count = await db.scalar(
        select(func.count()).select_from(Question)
        .join(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
    )

    # Total Answers Generated
    answers_count = await db.scalar(
        select(func.count()).select_from(Response)
        .join(Question).join(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .where(Response.answer.isnot(None))
    )
    
    # Calculate total interview hours
    sessions_result = await db.execute(
        select(InterviewSession).where(InterviewSession.user_id == current_user.id)
    )
    sessions = sessions_result.scalars().all()
    total_seconds = 0
    for s in sessions:
        if s.ended_at and s.started_at:
            total_seconds += (s.ended_at - s.started_at).total_seconds()
            
    stats_data = {
        "total_sessions": sessions_count or 0,
        "total_questions": questions_count or 0,
        "total_answers": answers_count or 0,
        "total_interview_hours": round(total_seconds / 3600, 2),
        "active_devices": devices_count or 0
    }
    
    await set_cache(cache_key, json.dumps(stats_data), ttl=300)
    return stats_data

@router.get("/sessions")
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Optimized query to avoid N+1 query loops
    result = await db.execute(
        select(InterviewSession, func.count(Question.id))
        .outerjoin(Question)
        .where(InterviewSession.user_id == current_user.id)
        .group_by(InterviewSession.id)
        .order_by(InterviewSession.started_at.desc())
    )
    
    response_sessions = []
    for s, q_count in result.all():
        response_sessions.append({
            "id": s.id,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "questions_count": q_count or 0
        })
        
    return response_sessions

@router.get("/sessions/{session_id}")
async def get_session_details(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.id == session_id, InterviewSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    msg_result = await db.execute(
        select(SessionMessage)
        .where(SessionMessage.session_id == session.id)
        .order_by(SessionMessage.created_at.asc())
    )
    messages = msg_result.scalars().all()
    
    # Optimized query to load question along with response using joinedload (avoids N+1 loops)
    q_result = await db.execute(
        select(Question)
        .options(joinedload(Question.response))
        .where(Question.session_id == session.id)
        .order_by(Question.created_at.asc())
    )
    questions = q_result.scalars().all()
    
    q_data = []
    for q in questions:
        r = q.response
        q_data.append({
            "id": q.id,
            "question_text": q.question_text,
            "category": q.category,
            "created_at": q.created_at,
            "answer": r.answer if r else None,
            "confidence_score": r.confidence_score if r else None
        })
        
    return {
        "session": {
            "id": session.id,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
        },
        "timeline": [
            {
                "id": m.id,
                "type": m.message_type,
                "content": m.content,
                "created_at": m.created_at
            } for m in messages
        ],
        "qa_pairs": q_data
    }

@router.get("/search")
async def global_search(
    query: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search across questions, answers, and resumes using PostgreSQL FTS with SQLite fallback.
    """
    is_sqlite = db.bind.dialect.name == "sqlite"
    
    if is_sqlite:
        search_term = f"%{query}%"
        # Search questions
        q_result = await db.execute(
            select(Question)
            .join(InterviewSession)
            .where(InterviewSession.user_id == current_user.id)
            .where(Question.question_text.ilike(search_term))
        )
        questions = q_result.scalars().all()

        # Search answers
        r_result = await db.execute(
            select(Response, Question)
            .join(Question)
            .join(InterviewSession)
            .where(InterviewSession.user_id == current_user.id)
            .where(Response.answer.ilike(search_term))
        )
        
        # Search Resumes
        res_result = await db.execute(
            select(Resume)
            .where(Resume.user_id == current_user.id)
            .where(Resume.extracted_text.ilike(search_term))
        )
        resumes = res_result.scalars().all()
    else:
        # PostgreSQL Full-Text Search using @@ operator and plainto_tsquery
        ts_query = func.plainto_tsquery('english', query)
        
        q_result = await db.execute(
            select(Question)
            .join(InterviewSession)
            .where(InterviewSession.user_id == current_user.id)
            .where(func.to_tsvector('english', Question.question_text).op('@@')(ts_query))
        )
        questions = q_result.scalars().all()

        r_result = await db.execute(
            select(Response, Question)
            .join(Question)
            .join(InterviewSession)
            .where(InterviewSession.user_id == current_user.id)
            .where(func.to_tsvector('english', Response.answer).op('@@')(ts_query))
        )
        
        res_result = await db.execute(
            select(Resume)
            .where(Resume.user_id == current_user.id)
            .where(func.to_tsvector('english', Resume.extracted_text).op('@@')(ts_query))
        )
        resumes = res_result.scalars().all()

    answers = []
    for resp, q in r_result:
        answers.append({
            "response_id": resp.id,
            "answer": resp.answer,
            "question_id": q.id,
            "question_text": q.question_text,
            "session_id": q.session_id
        })

    return {
        "questions": [{"id": q.id, "text": q.question_text, "session_id": q.session_id} for q in questions],
        "answers": answers,
        "resumes": [{"id": r.id, "file_name": r.file_name} for r in resumes]
    }

class UserSettingUpdate(BaseModel):
    theme: str | None = None
    overlay_mode: str | None = None
    hotkeys: str | None = None
    ai_preferences: str | None = None

@router.get("/settings")
async def get_user_settings(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cache_key = f"user_settings:{current_user.id}"
    cached = await get_cache(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    result = await db.execute(select(UserSetting).where(UserSetting.user_id == current_user.id))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = UserSetting(user_id=current_user.id)
        db.add(setting)
        await db.commit()
        
    setting_data = {
        "id": str(setting.id),
        "user_id": str(setting.user_id),
        "theme": setting.theme,
        "overlay_mode": setting.overlay_mode,
        "hotkeys": setting.hotkeys,
        "ai_preferences": setting.ai_preferences,
        "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
    }
    await set_cache(cache_key, json.dumps(setting_data), ttl=3600)
    return setting_data

@router.post("/settings")
async def update_user_settings(payload: UserSettingUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserSetting).where(UserSetting.user_id == current_user.id))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = UserSetting(user_id=current_user.id)
        db.add(setting)
    
    if payload.theme is not None: setting.theme = payload.theme
    if payload.overlay_mode is not None: setting.overlay_mode = payload.overlay_mode
    if payload.hotkeys is not None: setting.hotkeys = payload.hotkeys
    if payload.ai_preferences is not None: setting.ai_preferences = payload.ai_preferences
    
    await db.commit()
    
    # Invalidate settings cache
    cache_key = f"user_settings:{current_user.id}"
    await delete_cache(cache_key)
    
    return {
        "id": str(setting.id),
        "user_id": str(setting.user_id),
        "theme": setting.theme,
        "overlay_mode": setting.overlay_mode,
        "hotkeys": setting.hotkeys,
        "ai_preferences": setting.ai_preferences,
        "updated_at": setting.updated_at.isoformat() if setting.updated_at else None
    }

class BrowserStateUpdate(BaseModel):
    pinned_tabs: str | None = None
    allowed_domains: str | None = None
    blocked_domains: str | None = None

@router.get("/browser_state")
async def get_browser_state(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    cache_key = f"browser_state:{current_user.id}"
    cached = await get_cache(cache_key)
    if cached:
        try:
            return json.loads(cached)
        except Exception:
            pass

    result = await db.execute(select(BrowserState).where(BrowserState.user_id == current_user.id))
    state = result.scalar_one_or_none()
    if not state:
        state = BrowserState(user_id=current_user.id)
        db.add(state)
        await db.commit()
        
    state_data = {
        "id": str(state.id),
        "user_id": str(state.user_id),
        "pinned_tabs": state.pinned_tabs,
        "allowed_domains": state.allowed_domains,
        "blocked_domains": state.blocked_domains,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None
    }
    await set_cache(cache_key, json.dumps(state_data), ttl=3600)
    return state_data

@router.post("/browser_state")
async def update_browser_state(payload: BrowserStateUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BrowserState).where(BrowserState.user_id == current_user.id))
    state = result.scalar_one_or_none()
    if not state:
        state = BrowserState(user_id=current_user.id)
        db.add(state)
        
    if payload.pinned_tabs is not None: state.pinned_tabs = payload.pinned_tabs
    if payload.allowed_domains is not None: state.allowed_domains = payload.allowed_domains
    if payload.blocked_domains is not None: state.blocked_domains = payload.blocked_domains
    
    await db.commit()
    
    # Invalidate cache
    cache_key = f"browser_state:{current_user.id}"
    await delete_cache(cache_key)
    
    return {
        "id": str(state.id),
        "user_id": str(state.user_id),
        "pinned_tabs": state.pinned_tabs,
        "allowed_domains": state.allowed_domains,
        "blocked_domains": state.blocked_domains,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None
    }

@router.get("/devices")
async def get_devices(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.user_id == current_user.id))
    devices = result.scalars().all()
    
    devs = []
    for d in devices:
        devs.append({
            "id": d.id,
            "device_id": d.device_id,
            "device_name": d.device_name,
            "last_seen": d.last_seen,
            "created_at": d.created_at,
            "session_count": 0
        })
    return devs

