"""
Interview Orchestrator — the core async pipeline.
Wires all AI services together with asyncio.gather() for maximum concurrency.
"""
import asyncio
import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import InterviewSession, Question, Response
from app.schemas.interview import ChunkView, InterviewResponse
from app.services.embedder import get_embedder
from app.services.gemini_service import GeminiService
from app.services.retrieval import retrieve
from app.services.prompt_builder import build_prompt
from app.services.confidence import compute_confidence
from app.services.vector_store import get_vector_store
from app.core.logging import get_logger

logger = get_logger(__name__)


async def process_question(
    question_text: str,
    user_id: UUID,
    session_id: UUID,
    db: AsyncSession,
    gemini_client: GeminiService,
    transcription_confidence: float | None = None,
) -> InterviewResponse:
    """
    Full pipeline: question → classification + embedding (parallel)
    → retrieval → prompt → Gemini → score → DB log → response.
    """
    t_start = time.monotonic()

    embedder = get_embedder()
    store = get_vector_store()

    # ── Step 1: Classify + Embed concurrently ─────────────────────────────────
    (category, cat_confidence), q_vector = await asyncio.gather(
        gemini_client.classify(question_text),
        embedder.embed_one(question_text),
    )

    # ── Step 2: Retrieve relevant context ────────────────────────────────────
    chunks: list[ChunkView] = await retrieve(question_text, user_id, q_vector=q_vector)
    is_personalized = len(chunks) > 0

    # ── Step 3: Build prompt ──────────────────────────────────────────────────
    final_prompt = build_prompt(question_text, category, chunks)

    # ── Step 4: Generate answer ───────────────────────────────────────────────
    answer = await gemini_client.generate_answer(final_prompt)

    # ── Step 5: Score + Log concurrently ─────────────────────────────────────
    confidence = compute_confidence(chunks, cat_confidence, answer)

    # Persist to DB
    question_record = Question(
        session_id=session_id,
        question_text=question_text,
        category=category,
    )
    db.add(question_record)
    await db.flush()  # get question_record.id

    response_record = Response(
        question_id=question_record.id,
        answer=answer,
        confidence_score=confidence,
        generated_prompt=final_prompt,
    )
    db.add(response_record)
    # commit handled by get_db() dependency

    latency_ms = int((time.monotonic() - t_start) * 1000)

    logger.info("interview.question.processed", extra={
        "user_id": str(user_id),
        "session_id": str(session_id),
        "question_id": str(question_record.id),
        "category": category,
        "chunks_retrieved": len(chunks),
        "confidence": confidence,
        "latency_ms": latency_ms,
        "is_personalized": is_personalized,
    })

    return InterviewResponse(
        session_id=session_id,
        question_id=question_record.id,
        question_text=question_text,
        category=category,
        category_confidence=cat_confidence,
        retrieved_context=chunks,
        generated_prompt=final_prompt,
        answer=answer,
        confidence_score=confidence,
        transcription_confidence=transcription_confidence,
        is_personalized=is_personalized,
        latency_ms=latency_ms,
    )
