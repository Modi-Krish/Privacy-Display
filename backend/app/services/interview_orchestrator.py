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
    from app.services.db_service import get_db_service
    db_service = get_db_service()

    question_record = await db_service.create_question(
        session_id=session_id,
        question_text=question_text,
        category=category,
        db=db
    )

    response_record = await db_service.create_response(
        question_id=question_record.id,
        answer=answer,
        confidence_score=confidence,
        generated_prompt=final_prompt,
        db=db
    )

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


async def stream_question_pipeline(
    question_text: str,
    user_id: UUID,
    session_id: UUID,
    db: AsyncSession,
    gemini_client: GeminiService,
    transcription_confidence: float | None = None,
):
    """
    Streaming pipeline: starts classification in background, retrieves context,
    triggers Gemini generator stream, wait 5 seconds (thinking delay),
    yields first line, then streams the remaining tokens immediately.
    """
    t_start = time.monotonic()

    embedder = get_embedder()
    store = get_vector_store()

    # 1. Start classification in background (do not block)
    classify_task = asyncio.create_task(gemini_client.classify(question_text))

    # 2. Embed and retrieve context
    q_vector = await embedder.embed_one(question_text)
    chunks = await retrieve(question_text, user_id, q_vector=q_vector)
    is_personalized = len(chunks) > 0

    # 3. Build prompt
    final_prompt = build_prompt(question_text, "Technical", chunks)

    # 4. Create Question record in DB
    from app.services.db_service import get_db_service
    db_service = get_db_service()

    question_record = await db_service.create_question(
        session_id=session_id,
        question_text=question_text,
        category="Technical",
        db=db
    )
    question_id = question_record.id

    # Yield initial info event immediately
    yield {
        "event": "info",
        "data": {
            "question_id": str(question_id),
            "question_text": question_text,
            "retrieved_context": [
                {
                    "text": chunk.text,
                    "source": chunk.source,
                    "section": chunk.section,
                    "score": float(chunk.score)
                } for chunk in chunks
            ],
            "generated_prompt": final_prompt,
        }
    }

    # 5. Start Gemini generation stream
    gen_stream = gemini_client.generate_answer_stream(final_prompt)

    # Accumulate stream tokens in a background task
    tokens = []
    stream_done = False
    stream_error = None

    async def collect_tokens():
        nonlocal stream_done, stream_error
        try:
            async for token in gen_stream:
                tokens.append(token)
        except Exception as e:
            stream_error = e
        finally:
            stream_done = True

    collect_task = asyncio.create_task(collect_tokens())

    # 6. (Removed artificial thinking delay)

    # Retrieve background classification result
    try:
        category, cat_confidence = await classify_task
    except Exception as e:
        logger.warning("Background classification failed", extra={"error": str(e)})
        category, cat_confidence = "Technical", 0.5

    # Update Question category in DB
    await db_service.update_question_category(question_id, category, db=db)

    # Wait for initial tokens if none received yet
    while not tokens and not stream_done:
        await asyncio.sleep(0.05)

    if stream_error and not tokens:
        raise stream_error

    tokens_consumed_count = 0

    # Stream any new incoming tokens immediately
    while not stream_done:
        if len(tokens) > tokens_consumed_count:
            new_tokens = tokens[tokens_consumed_count:]
            tokens_consumed_count = len(tokens)
            yield {
                "event": "token",
                "data": "".join(new_tokens)
            }
        await asyncio.sleep(0.05)

    # Yield final new tokens if any
    if len(tokens) > tokens_consumed_count:
        new_tokens = tokens[tokens_consumed_count:]
        yield {
            "event": "token",
            "data": "".join(new_tokens)
        }

    # If the stream died due to an error, raise it now so the user sees it
    if stream_error:
        raise stream_error

    # 7. Finalize and log Response to DB
    final_answer = "".join(tokens)
    confidence = compute_confidence(chunks, cat_confidence, final_answer)

    await db_service.create_response(
        question_id=question_id,
        answer=final_answer,
        confidence_score=confidence,
        generated_prompt=final_prompt,
        db=db
    )

    latency_ms = int((time.monotonic() - t_start) * 1000)

    logger.info("interview.question.stream.processed", extra={
        "user_id": str(user_id),
        "session_id": str(session_id),
        "question_id": str(question_id),
        "category": category,
        "latency_ms": latency_ms,
    })

    yield {
        "event": "done",
        "data": {
            "category": category,
            "category_confidence": cat_confidence,
            "confidence_score": confidence,
            "is_personalized": is_personalized,
            "latency_ms": latency_ms,
        }
    }
