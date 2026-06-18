"""
Real-Time Voice WebSocket Endpoint.

Single endpoint: /api/ws/realtime

Architecture — three concurrent async pipelines per connection:
  Pipeline 1: Audio chunks → StreamingSTT → partial transcripts
  Pipeline 2: Transcript updates → RAG retrieval (parallel, non-blocking)
  Pipeline 3: Question detection → Gemini streaming (cancellable, restartable)

Auth: Localhost-only guard (no token auth for desktop Electron app).
"""
import asyncio
import base64
import json
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.websockets import WebSocketState

from app.core.logging import get_logger
from app.services.streaming_stt import StreamingSTTSession, _has_question_signal
from app.services.gemini_service import get_gemini_service_custom
from app.services.prompt_builder import build_realtime_prompt

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["realtime"])

# ── Minimum transcript length before triggering Gemini ─────────────────────
MIN_TRIGGER_WORDS = 3

# ── How much transcript change triggers a Gemini restart ───────────────────
# If new transcript adds N+ words compared to what was sent to Gemini, restart.
RESTART_WORD_DELTA = 5


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


def _is_localhost(websocket: WebSocket) -> bool:
    """Allow only connections from localhost."""
    client = websocket.client
    if client is None:
        return True  # allow if we can't determine (e.g. test clients)
    host = client.host
    return host in ("127.0.0.1", "::1", "localhost")


class RealtimeSession:
    """
    Manages one client's real-time voice session.
    Coordinates the three async pipelines.
    """

    def __init__(self, websocket: WebSocket, gemini_api_key: str, gemini_model: str, user_id: str):
        self.ws = websocket
        self.gemini_api_key = gemini_api_key
        self.gemini_model = gemini_model
        self.user_id = user_id

        # STT session
        self.stt_session = StreamingSTTSession()

        # State
        self.conversation_history: list[dict] = []
        self.current_question: str = ""          # last question sent to Gemini
        self.current_answer_tokens: list[str] = []
        self.is_generating = False

        # Cancellation for early question detection restart
        self.cancel_event = asyncio.Event()

        # Task handles
        self._stt_task: asyncio.Task | None = None
        self._gemini_task: asyncio.Task | None = None
        self._rag_cache: dict[str, str] = {}     # question_hash → context string

    async def send(self, msg: dict) -> None:
        """Send a JSON message to the client, safely."""
        try:
            if self.ws.client_state == WebSocketState.CONNECTED:
                await self.ws.send_text(json.dumps(msg))
        except Exception as e:
            logger.warning("WS send failed", extra={"error": str(e)})

    async def run(self) -> None:
        """Main session coroutine — starts STT and drives audio ingestion."""
        await self.stt_session.start()
        self._stt_task = asyncio.create_task(self._stt_pipeline())

        try:
            async for message in self.ws.iter_text():
                await self._handle_client_message(message)
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected")
        except Exception as e:
            logger.error("WebSocket session error", extra={"error": str(e)})
        finally:
            await self._cleanup()

    async def _handle_client_message(self, raw: str) -> None:
        """Process a single message from the client."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await self.send({"type": "error", "detail": "Invalid JSON"})
            return

        msg_type = msg.get("type")

        if msg_type == "audio_chunk":
            # Decode base64 PCM and push to STT
            data_b64 = msg.get("data", "")
            if data_b64:
                try:
                    pcm_bytes = base64.b64decode(data_b64)
                    self.stt_session.push_audio(pcm_bytes)
                except Exception as e:
                    logger.warning("Audio decode error", extra={"error": str(e)})

        elif msg_type == "text_question":
            # Direct text input (bypasses STT) — for testing / keyboard mode
            question = msg.get("text", "").strip()
            if question:
                await self.send({"type": "transcript_final", "text": question})
                await self._trigger_gemini(question)

        elif msg_type == "ping":
            await self.send({"type": "pong"})

        elif msg_type == "end_stream":
            await self.stt_session.stop()

        elif msg_type == "set_gemini_key":
            # Allow runtime API key update (from settings page)
            self.gemini_api_key = msg.get("key", self.gemini_api_key)

    async def _stt_pipeline(self) -> None:
        """
        Pipeline 1+2: Consumes STT events and triggers Gemini when appropriate.
        Also kicks off RAG retrieval in parallel.
        """
        async for event in self.stt_session.events():
            event_type = event.get("type")
            text = event.get("text", "")

            if event_type == "partial":
                # Send live transcript update to UI
                await self.send({"type": "transcript_partial", "text": text})

                # Early question detection: if transcript looks complete,
                # start Gemini immediately without waiting for silence
                if _has_question_signal(text) and _word_count(text) >= MIN_TRIGGER_WORDS:
                    await self._maybe_trigger_or_restart(text)

                # Kick off RAG retrieval in background for any substantial text
                if _word_count(text) >= MIN_TRIGGER_WORDS:
                    asyncio.create_task(self._prefetch_rag(text))

            elif event_type == "question_detected":
                await self.send({"type": "transcript_partial", "text": text})
                await self._maybe_trigger_or_restart(text)

            elif event_type == "silence":
                # Pause detected — trigger if we have a question and aren't already answering
                if text and _word_count(text) >= MIN_TRIGGER_WORDS:
                    await self.send({"type": "transcript_final", "text": text})
                    await self._maybe_trigger_or_restart(text)

            elif event_type == "final":
                await self.send({"type": "transcript_final", "text": text})

    async def _maybe_trigger_or_restart(self, new_transcript: str) -> None:
        """
        Core early-detection logic:
        - If not generating: start immediately.
        - If generating with a similar question: let it continue.
        - If transcript changed significantly (N+ new words): cancel & restart.
        """
        if not self.is_generating:
            await self._trigger_gemini(new_transcript)
            return

        # Already generating — check if restart is warranted
        prev_words = _word_count(self.current_question)
        new_words = _word_count(new_transcript)
        delta = new_words - prev_words

        if delta >= RESTART_WORD_DELTA:
            logger.info(
                "Restarting Gemini — transcript expanded",
                extra={"prev_words": prev_words, "new_words": new_words, "delta": delta},
            )
            await self.send({
                "type": "answer_restart",
                "reason": "Transcript updated",
                "new_question": new_transcript,
            })
            # Signal cancellation to the running stream
            self.cancel_event.set()

            # Wait briefly for the running task to notice the cancellation
            if self._gemini_task and not self._gemini_task.done():
                try:
                    await asyncio.wait_for(
                        asyncio.shield(self._gemini_task), timeout=0.3
                    )
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    self._gemini_task.cancel()

            # Reset and restart
            self.cancel_event.clear()
            self.current_answer_tokens.clear()
            await self._trigger_gemini(new_transcript)

    async def _trigger_gemini(self, question: str) -> None:
        """Launch Gemini generation in a background task."""
        if self.is_generating:
            return  # guard: _maybe_trigger_or_restart handles restarts

        self.current_question = question
        self.current_answer_tokens.clear()
        self.is_generating = True

        t_start = time.monotonic()
        await self.send({"type": "answer_start", "question": question})

        self._gemini_task = asyncio.create_task(
            self._gemini_pipeline(question, t_start)
        )

    async def _gemini_pipeline(self, question: str, t_start: float) -> None:
        """
        Pipeline 3: Stream Gemini answer tokens to the client.
        Uses RAG context if already fetched, otherwise fire-and-forget context lookup.
        """
        try:
            gemini = get_gemini_service_custom(
                api_key=self.gemini_api_key,
                model=self.gemini_model,
            )

            # Get any pre-fetched RAG context
            context = self._rag_cache.get(self._question_key(question), "")

            # Stream tokens
            first_token = True
            full_answer = []

            async for token in gemini.stream_voice_answer(
                question=question,
                context=context,
                history=self.conversation_history,
                cancel_event=self.cancel_event,
            ):
                if self.cancel_event.is_set():
                    break

                if first_token:
                    latency_ms = int((time.monotonic() - t_start) * 1000)
                    await self.send({
                        "type": "answer_first_token",
                        "latency_ms": latency_ms,
                    })
                    first_token = False

                full_answer.append(token)
                self.current_answer_tokens.append(token)
                await self.send({"type": "answer_token", "token": token})

            # Only save to history if not cancelled
            if not self.cancel_event.is_set():
                total_latency = int((time.monotonic() - t_start) * 1000)
                complete_answer = "".join(full_answer)
                self.conversation_history.append({
                    "question": question,
                    "answer": complete_answer,
                })
                # Keep history bounded
                if len(self.conversation_history) > 10:
                    self.conversation_history = self.conversation_history[-10:]

                await self.send({
                    "type": "answer_done",
                    "question": question,
                    "answer": complete_answer,
                    "latency_ms": total_latency,
                })

        except Exception as e:
            logger.error("Gemini pipeline error", extra={"error": str(e)})
            await self.send({
                "type": "error",
                "detail": f"Generation failed: {str(e)}",
            })
        finally:
            self.is_generating = False

    async def _prefetch_rag(self, question: str) -> None:
        """
        Pipeline 2 (background): Run RAG retrieval in parallel with STT.
        Result is cached so Gemini can pick it up when it fires.
        """
        key = self._question_key(question)
        if key in self._rag_cache:
            return

        try:
            from app.services.embedder import get_embedder
            from app.services.retrieval import retrieve
            from app.schemas.interview import ChunkView

            embedder = get_embedder()
            q_vector = await embedder.embed_one(question)

            # Parse user_id safely
            try:
                uid = UUID(self.user_id)
            except (ValueError, AttributeError):
                uid = UUID("00000000-0000-0000-0000-000000000000")

            chunks = await retrieve(question, uid, q_vector=q_vector)
            context = build_realtime_prompt(question, chunks)
            self._rag_cache[key] = context

            # If Gemini hasn't started yet for this question, it will pick this up
            # If it already started, the next restart will benefit
            logger.debug(
                "RAG prefetch complete",
                extra={"question_words": _word_count(question), "chunks": len(chunks)},
            )
        except Exception as e:
            logger.warning("RAG prefetch failed (non-fatal)", extra={"error": str(e)})
            self._rag_cache[key] = ""

    def _question_key(self, question: str) -> str:
        """Simple cache key: first 60 chars of question."""
        return question[:60].lower().strip()

    async def _cleanup(self) -> None:
        """Stop all background tasks cleanly."""
        self.cancel_event.set()
        await self.stt_session.stop()
        if self._gemini_task and not self._gemini_task.done():
            self._gemini_task.cancel()
            try:
                await self._gemini_task
            except asyncio.CancelledError:
                pass
        logger.info("RealtimeSession cleaned up")


# ── WebSocket Route ──────────────────────────────────────────────────────────

@router.websocket("/realtime")
async def realtime_endpoint(
    websocket: WebSocket,
    api_key: str = Query(default=""),
    model: str = Query(default=""),
    user_id: str = Query(default="default"),
):
    """
    Real-time voice WebSocket endpoint.
    
    Query params:
      api_key  — Gemini API key (falls back to server config)
      model    — Gemini model name (falls back to server config)
      user_id  — user identifier for RAG retrieval (defaults to 'default')
    
    Localhost-only: rejects connections from non-local hosts.
    """
    # Localhost guard
    if not _is_localhost(websocket):
        await websocket.close(code=1008, reason="Remote connections not allowed")
        return

    await websocket.accept()
    logger.info("Real-time WebSocket connected", extra={"user_id": user_id})

    # Resolve Gemini config
    from app.core.config import get_settings
    settings = get_settings()
    resolved_key = api_key or settings.GEMINI_API_KEY
    resolved_model = model or settings.GEMINI_MODEL

    if not resolved_key:
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "No Gemini API key configured. Set it in Settings.",
        }))
        await websocket.close(code=1011)
        return

    # Announce readiness
    await websocket.send_text(json.dumps({
        "type": "ready",
        "model": resolved_model,
    }))

    session = RealtimeSession(
        websocket=websocket,
        gemini_api_key=resolved_key,
        gemini_model=resolved_model,
        user_id=user_id,
    )
    await session.run()
