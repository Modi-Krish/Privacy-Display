"""
Standalone audio transcription endpoint + health + rate-limit middleware.
This file is imported by main.py — it adds the audio router and any
Phase 6 middleware that main.py mounts.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel

from app.core.deps import get_current_user
from app.db.models import User
from app.services.stt_service import get_stt

router = APIRouter(prefix="/audio", tags=["audio"])


class TranscribeRequest(BaseModel):
    audio_b64: str


class TranscribeResponse(BaseModel):
    text: str
    confidence: float
    language: str


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(
    body: TranscribeRequest,
    current_user: User = Depends(get_current_user),
    x_whisper_model_size: str | None = Header(None, alias="X-Whisper-Model-Size"),
):
    """Standalone STT endpoint for manual testing."""
    stt = get_stt()
    try:
        result = await stt.transcribe_b64(body.audio_b64, model_size=x_whisper_model_size)
        return TranscribeResponse(
            text=result.text,
            confidence=result.confidence,
            language=result.language,
        )
    except Exception as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Transcription failed: {e}")
