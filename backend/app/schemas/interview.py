from pydantic import BaseModel, field_validator
from uuid import UUID
from typing import Literal


# ── Retrieved Chunk ───────────────────────────────────────────────────────────

class ChunkView(BaseModel):
    text: str
    source: str                    # "resume" | "project" | "skill"
    section: str                   # "education" | "experience" | "projects" | "skills"
    score: float                   # cosine similarity 0.0 – 1.0


# ── Interview Session ─────────────────────────────────────────────────────────

class SessionOut(BaseModel):
    session_id: UUID
    started_at: str


# ── Question Request ──────────────────────────────────────────────────────────

class QuestionRequest(BaseModel):
    session_id: UUID
    question: str | None = None     # text path
    audio_b64: str | None = None    # audio path (base64 encoded audio bytes)

    @field_validator("question", "audio_b64", mode="before")
    @classmethod
    def at_least_one(cls, v, info):
        # Full validation done in the router
        return v


# ── Interview Response ────────────────────────────────────────────────────────

class InterviewResponse(BaseModel):
    session_id: UUID
    question_id: UUID
    question_text: str
    category: Literal["Technical", "Behavioral", "Project-Based", "HR"]
    category_confidence: float
    retrieved_context: list[ChunkView]
    generated_prompt: str
    answer: str
    confidence_score: float
    transcription_confidence: float | None   # None when text input used
    is_personalized: bool                    # False if no FAISS index found
    latency_ms: int


# ── Session End ───────────────────────────────────────────────────────────────

class SessionEndRequest(BaseModel):
    session_id: UUID


class SessionEndOut(BaseModel):
    session_id: UUID
    ended_at: str
    total_questions: int
