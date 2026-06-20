"""
Interview API — session management and question processing.
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_gemini_client
from app.db.session import get_db
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
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    session = await db_service.create_interview_session(current_user.id, db=db)
    return SessionOut(
        session_id=session.id,
        started_at=session.started_at.isoformat(),
    )


# ── Submit Question ───────────────────────────────────────────────────────────

@router.post("/question", response_model=InterviewResponse)
async def submit_question(
    body: QuestionRequest,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    gemini_client: GeminiService = Depends(get_gemini_client),
    x_whisper_model_size: str | None = Header(None, alias="X-Whisper-Model-Size"),
):
    # Check daily AI response quota
    from app.core.quotas import check_ai_quota
    await check_ai_quota(current_user.id)

    # Validate session belongs to user
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    session = await db_service.get_interview_session(body.session_id, current_user.id, db=db)
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


from fastapi.responses import StreamingResponse  # noqa: E402
import json  # noqa: E402
from app.core.logging import get_logger  # noqa: E402

logger = get_logger(__name__)

@router.post("/question/stream")
async def submit_question_stream(
    body: QuestionRequest,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    gemini_client: GeminiService = Depends(get_gemini_client),
    x_whisper_model_size: str | None = Header(None, alias="X-Whisper-Model-Size"),
):
    # Check daily AI response quota
    from app.core.quotas import check_ai_quota
    await check_ai_quota(current_user.id)

    # Validate session belongs to user
    from app.services.db_service import get_db_service
    db_service = get_db_service()
    session = await db_service.get_interview_session(body.session_id, current_user.id, db=db)
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

    # Import orchestrator stream pipeline
    from app.services.interview_orchestrator import stream_question_pipeline

    async def sse_generator():
        try:
            async for chunk in stream_question_pipeline(
                question_text=question_text,
                user_id=current_user.id,
                session_id=body.session_id,
                db=db,
                gemini_client=gemini_client,
                transcription_confidence=transcription_confidence,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error("SSE stream error", extra={"error": str(e)})
            yield f"data: {json.dumps({'event': 'error', 'detail': str(e)})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


# ── End Session ───────────────────────────────────────────────────────────────

@router.post("/end", response_model=SessionEndOut)
async def end_session(
    body: SessionEndRequest,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.services.db_service import get_db_service
    from app.core.redis import delete_cache
    db_service = get_db_service()
    session = await db_service.get_interview_session(body.session_id, current_user.id, db=db)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")

    ended_at = datetime.now(timezone.utc)
    await db_service.end_interview_session(session.id, ended_at, db=db)

    # Invalidate dashboard stats cache
    await delete_cache(f"user_stats:{current_user.id}")

    # Count questions
    total = await db_service.get_question_count(session.id, db=db)

    return SessionEndOut(
        session_id=session.id,
        ended_at=ended_at.isoformat(),
        total_questions=total,
    )
