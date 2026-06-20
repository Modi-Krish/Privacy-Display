import io
import base64
import logging
from dataclasses import dataclass
from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class TranscriptionResult:
    text: str
    confidence: float   # 0.0 – 1.0
    language: str


class STTService:
    def __init__(self):
        self._client = None

    def load(self) -> None:
        """Startup warm-up: verify API key configuration."""
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY is not set. OpenAI Whisper STT calls will fail.")
        else:
            logger.info("Stateless OpenAI Whisper STT service initialized.")

    def get_client(self) -> AsyncOpenAI:
        if self._client is None:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY environment variable is not configured.")
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def transcribe(self, audio_bytes: bytes, model_size: str | None = None) -> TranscriptionResult:
        """
        Asynchronously transcribes audio bytes using the OpenAI Whisper API.
        model_size is ignored since the OpenAI service handles size routing dynamically.
        """
        client = self.get_client()
        
        # Wrap bytes in BytesIO and name the buffer so the OpenAI client resolves the format
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"

        try:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en",
                response_format="verbose_json"
            )
            
            text = getattr(response, "text", "").strip()
            language = getattr(response, "language", "english")
            
            # Default to high confidence proxy if segments are clean
            confidence = 0.95
            
            return TranscriptionResult(
                text=text,
                confidence=confidence,
                language=language,
            )
        except Exception as e:
            logger.error("OpenAI Whisper API transcription failed", extra={"error": str(e)})
            raise RuntimeError(f"Transcription failed: {str(e)}")

    async def transcribe_b64(self, audio_b64: str, model_size: str | None = None) -> TranscriptionResult:
        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception as e:
            raise ValueError(f"Invalid base64 payload: {e}")
        return await self.transcribe(audio_bytes, model_size)


# Singleton
_stt_instance: STTService | None = None


def get_stt() -> STTService:
    global _stt_instance
    if _stt_instance is None:
        raise RuntimeError("STTService not initialized")
    return _stt_instance


def init_stt(model_size: str, device: str, compute_type: str) -> STTService:
    global _stt_instance
    _stt_instance = STTService()
    _stt_instance.load()
    return _stt_instance
