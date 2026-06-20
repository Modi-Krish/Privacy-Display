"""
Streaming STT Service — rolling-buffer approach for real-time transcription.

Strategy (Option A):
  - Accept raw 16-bit PCM audio chunks via an asyncio.Queue
  - Maintain a 2-3 second rolling buffer
  - Run faster-whisper every 500ms on the latest buffer
  - Emit partial transcript updates via a results Queue
  - Detect silence gaps via RMS energy threshold for question triggering

No new models are loaded — reuses the WhisperModel singleton from stt_service.py.
"""
import asyncio
import io
import struct
import time
import numpy as np
from typing import AsyncGenerator

from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
SAMPLE_RATE = 16_000          # Hz — must match AudioWorklet output
BYTES_PER_SAMPLE = 2          # 16-bit PCM
BUFFER_SECONDS = 2.5          # rolling window fed to Whisper
TRANSCRIBE_INTERVAL = 0.3     # seconds between Whisper runs
SILENCE_ENERGY_THRESHOLD = 0.003   # RMS below this = silence
SILENCE_DURATION_TRIGGER = 0.4     # seconds of silence to signal end-of-utterance

# ── Question detection keywords ───────────────────────────────────────────────
QUESTION_KEYWORDS = frozenset([
    "what", "why", "how", "when", "where", "who", "which", "whose", "whom",
    "explain", "describe", "compare", "tell me", "define", "elaborate",
    "can you", "could you", "would you", "do you", "is there", "are there",
])


def _has_question_signal(text: str) -> bool:
    """Return True if the transcript looks like a complete question."""
    if not text:
        return False
    lower = text.lower().strip()
    if lower.endswith("?"):
        return True
    words = lower.split()
    if not words:
        return False
    # First word is a question word
    if words[0] in QUESTION_KEYWORDS:
        return True
    # Bigram match (e.g., "tell me", "can you")
    if len(words) >= 2 and f"{words[0]} {words[1]}" in QUESTION_KEYWORDS:
        return True
    return False


def _rms_energy(pcm_bytes: bytes) -> float:
    """Compute RMS energy of raw 16-bit PCM bytes."""
    if len(pcm_bytes) < 2:
        return 0.0
    count = len(pcm_bytes) // 2
    samples = struct.unpack(f"<{count}h", pcm_bytes[:count * 2])
    rms = (sum(s * s for s in samples) / count) ** 0.5
    return rms / 32768.0   # normalize to 0-1


class StreamingSTTSession:
    """
    Manages a single real-time transcription session.
    
    Usage:
        session = StreamingSTTSession()
        await session.start()
        session.push_audio(pcm_bytes)   # call this from WS handler
        async for event in session.events():
            # event: {'type': 'partial'|'silence'|'question_detected', 'text': str}
            ...
        await session.stop()
    """

    def __init__(self):
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._event_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None

        # Rolling PCM buffer
        self._buffer = bytearray()
        self._max_buffer_bytes = int(BUFFER_SECONDS * SAMPLE_RATE * BYTES_PER_SAMPLE)

        # Silence tracking
        self._last_voice_time = time.monotonic()
        self._silence_emitted = False

        # Deduplication
        self._last_transcript = ""

    # ── Public API ─────────────────────────────────────────────────────────

    def push_audio(self, pcm_bytes: bytes) -> None:
        """Non-blocking: enqueue a raw 16-bit PCM chunk."""
        self._audio_queue.put_nowait(pcm_bytes)

    async def start(self) -> None:
        """Start the background transcription loop."""
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """Signal the session to stop and wait for cleanup."""
        self._running = False
        self._audio_queue.put_nowait(None)   # sentinel
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=3.0)
            except asyncio.TimeoutError:
                self._task.cancel()

    async def events(self) -> AsyncGenerator[dict, None]:
        """Async generator that yields transcription events."""
        while self._running or not self._event_queue.empty():
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=0.2)
                yield event
            except asyncio.TimeoutError:
                continue

    # ── Internal loop ──────────────────────────────────────────────────────

    async def _run(self) -> None:
        """Main transcription loop — drains audio queue and runs Whisper periodically."""
        asyncio.get_event_loop()
        next_transcribe_at = time.monotonic() + TRANSCRIBE_INTERVAL

        while self._running:
            # Drain all pending audio chunks (non-blocking)
            try:
                while True:
                    chunk = self._audio_queue.get_nowait()
                    if chunk is None:
                        self._running = False
                        break
                    self._buffer.extend(chunk)
                    # Trim to rolling window
                    if len(self._buffer) > self._max_buffer_bytes:
                        overflow = len(self._buffer) - self._max_buffer_bytes
                        del self._buffer[:overflow]

                    # Update silence detector
                    energy = _rms_energy(bytes(chunk))
                    if energy > SILENCE_ENERGY_THRESHOLD:
                        self._last_voice_time = time.monotonic()
                        self._silence_emitted = False
            except asyncio.QueueEmpty:
                pass

            now = time.monotonic()

            # Check for silence trigger
            silence_duration = now - self._last_voice_time
            if silence_duration >= SILENCE_DURATION_TRIGGER and not self._silence_emitted:
                if self._last_transcript:
                    self._silence_emitted = True
                    await self._event_queue.put({
                        "type": "silence",
                        "text": self._last_transcript,
                        "silence_duration": round(silence_duration, 2),
                    })

            # Run Whisper on schedule
            if now >= next_transcribe_at and len(self._buffer) > SAMPLE_RATE * BYTES_PER_SAMPLE * 0.3:
                next_transcribe_at = now + TRANSCRIBE_INTERVAL
                transcript = await self._transcribe_buffer_async(bytes(self._buffer))
                if transcript and transcript != self._last_transcript:
                    self._last_transcript = transcript
                    event_type = "question_detected" if _has_question_signal(transcript) else "partial"
                    await self._event_queue.put({
                        "type": event_type,
                        "text": transcript,
                    })

            await asyncio.sleep(0.05)

        # Final transcription pass on remaining buffer
        if len(self._buffer) > SAMPLE_RATE * BYTES_PER_SAMPLE * 0.2:
            final = await self._transcribe_buffer_async(bytes(self._buffer))
            if final and final != self._last_transcript:
                await self._event_queue.put({"type": "final", "text": final})

    async def _transcribe_buffer_async(self, pcm_bytes: bytes) -> str:
        """
        Asynchronous Whisper call via OpenAI API.
        Converts raw 16-bit PCM → float32 numpy → in-memory WAV → OpenAI Whisper.
        """
        try:
            # Convert 16-bit PCM → float32
            count = len(pcm_bytes) // 2
            if count == 0:
                return ""
            samples = np.frombuffer(pcm_bytes[:count * 2], dtype=np.int16).astype(np.float32)
            samples /= 32768.0   # normalize

            # Write to in-memory WAV
            wav_buffer = io.BytesIO()
            import wave
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes((samples * 32768).astype(np.int16).tobytes())
            wav_bytes = wav_buffer.getvalue()

            from app.services.stt_service import get_stt
            stt = get_stt()
            result = await stt.transcribe(wav_bytes)
            return result.text
        except Exception as e:
            logger.warning("Streaming transcription error", extra={"error": str(e)})
            return ""
