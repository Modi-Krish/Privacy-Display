"""
Interview API — session management and question processing.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.deps import get_current_user, get_gemini_client
from app.db.session import get_db
from app.db.models import User, InterviewSession, Question
from app.schemas.interview import (
    QuestionRequest, InterviewResponse, SessionOut, SessionEndOut, SessionEndRequest,
)
from app.services.interview_orchestrator import process_question
from app.services.stt_service import get_stt
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/interview", tags=["interview"])


# ── Start Session ─────────────────────────────────────────────────────────────

@router.post("/start", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def start_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = InterviewSession(user_id=current_user.id)
    db.add(session)
    await db.flush()
    return SessionOut(
        session_id=session.id,
        started_at=session.started_at.isoformat(),
    )


# ── Submit Question ───────────────────────────────────────────────────────────

@router.post("/question", response_model=InterviewResponse)
async def submit_question(
    body: QuestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    gemini_client: GeminiService = Depends(get_gemini_client),
    x_whisper_model_size: str | None = Header(None, alias="X-Whisper-Model-Size"),
):
    # Validate session belongs to user
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == body.session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    if session.ended_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Session already ended")

    # Determine question text
    transcription_confidence: float | None = None

    if body.audio_b64:
        stt = get_stt()
        try:
            transcription = await stt.transcribe_b64(body.audio_b64, model_size=x_whisper_model_size)
            question_text = transcription.text
            transcription_confidence = transcription.confidence
        except Exception as e:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Audio transcription failed: {str(e)}",
            )
    elif body.question:
        question_text = body.question.strip()
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Provide either 'question' (text) or 'audio_b64'",
        )

    if not question_text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Empty question text")

    # Run full pipeline
    try:
        response = await process_question(
            question_text=question_text,
            user_id=current_user.id,
            session_id=body.session_id,
            db=db,
            gemini_client=gemini_client,
            transcription_confidence=transcription_confidence,
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))

    return response


# ── End Session ───────────────────────────────────────────────────────────────

@router.post("/end", response_model=SessionEndOut)
async def end_session(
    body: SessionEndRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == body.session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    session.ended_at = datetime.now(timezone.utc)

    # Count questions
    count_result = await db.execute(
        select(func.count()).select_from(Question).where(Question.session_id == session.id)
    )
    total = count_result.scalar() or 0

    return SessionEndOut(
        session_id=session.id,
        ended_at=session.ended_at.isoformat(),
        total_questions=total,
    )
