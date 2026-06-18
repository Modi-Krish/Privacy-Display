"""
Speech-to-Text Service — Faster-Whisper wrapper.
Model loaded once at startup, inference run in thread pool.
"""
import asyncio
import base64
import io
import tempfile
import os
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class TranscriptionResult:
    text: str
    confidence: float   # 0.0 – 1.0
    language: str


class STTService:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._models: dict[str, Any] = {}

    def load(self) -> None:
        """Prefetch/load default model size."""
        self._get_model(self._model_size)

    def _get_model(self, model_size: str):
        if model_size not in self._models:
            from faster_whisper import WhisperModel
            import os
            
            model_path = os.path.join(settings.MODEL_DIR, f"faster-whisper-{model_size}")
            if os.path.exists(model_path):
                load_arg = model_path
            else:
                load_arg = model_size
                
            logger.info("Loading Whisper model", extra={"model_size": model_size, "path": load_arg})
            self._models[model_size] = WhisperModel(
                load_arg,
                device=self._device,
                compute_type=self._compute_type,
                download_root=settings.MODEL_DIR
            )
        return self._models[model_size]

    def _transcribe_sync(self, audio_bytes: bytes, model_size: str) -> TranscriptionResult:
        """Synchronous transcription — runs in thread pool."""
        model = self._get_model(model_size)
        audio_file = io.BytesIO(audio_bytes)

        segments, info = model.transcribe(audio_file, language="en")
        text_parts = []
        avg_logprob_sum = 0.0
        seg_count = 0
        for seg in segments:
            text_parts.append(seg.text.strip())
            avg_logprob_sum += seg.avg_logprob
            seg_count += 1

        text = " ".join(text_parts).strip()
        # Convert avg_logprob (-inf to 0) to a 0–1 confidence heuristic
        if seg_count > 0:
            avg_logprob = avg_logprob_sum / seg_count
            confidence = max(0.0, min(1.0, 1.0 + avg_logprob))
        else:
            confidence = 0.0

        return TranscriptionResult(
            text=text,
            confidence=round(confidence, 3),
            language=info.language,
        )

    async def transcribe(self, audio_bytes: bytes, model_size: str | None = None) -> TranscriptionResult:
        loop = asyncio.get_event_loop()
        size = model_size or self._model_size
        return await loop.run_in_executor(None, self._transcribe_sync, audio_bytes, size)

    async def transcribe_b64(self, audio_b64: str, model_size: str | None = None) -> TranscriptionResult:
        audio_bytes = base64.b64decode(audio_b64)
        return await self.transcribe(audio_bytes, model_size)


# Singleton
_stt_instance: STTService | None = None


def get_stt() -> STTService:
    if _stt_instance is None:
        raise RuntimeError("STTService not initialized")
    return _stt_instance


def init_stt(model_size: str, device: str, compute_type: str) -> STTService:
    global _stt_instance
    _stt_instance = STTService(model_size, device, compute_type)
    _stt_instance.load()
    return _stt_instance
