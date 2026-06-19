"""
Gemini Service — question classification + answer generation.
"""
import asyncio
import json
import re
from typing import Literal, AsyncGenerator

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.logging import get_logger

# Define relaxed safety settings for interview context to avoid false positive blocks
RELAXED_SAFETY_SETTINGS = [
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
    types.SafetySetting(
        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    ),
]

logger = get_logger(__name__)
settings = get_settings()

QuestionCategory = Literal["Technical", "Behavioral", "Project-Based", "HR"]

# ── Real-Time Voice System Prompt ─────────────────────────────────────────────
VOICE_SYSTEM_PROMPT = """\
You are a real-time voice interview assistant.

Rules:
1. Answer IMMEDIATELY — the user is mid-conversation.
2. Keep responses concise: maximum 3 short paragraphs.
3. Prioritize speed and clarity over exhaustive detail.
4. If the transcript appears incomplete, provide your best answer based on what's available.
5. Use plain language suitable for speaking aloud.
6. Do NOT use markdown headers or bullet lists — write in flowing prose.
7. Start your answer directly — no preamble like "Great question" or "Sure!".
"""

CLASSIFICATION_PROMPT = """\
Classify the following interview question into exactly ONE of these categories:
- Technical
- Behavioral
- Project-Based
- HR

Respond with JSON only, no explanation:
{{"category": "<category>", "confidence": <0.0-1.0>}}

Question: {question}
"""


class GeminiService:
    def __init__(self, api_key: str, model: str):
        self._client = genai.Client(api_key=api_key)
        self.api_key = api_key
        self._model = model

    async def _generate(self, prompt: str, attempt: int = 0) -> str:
        """Run Gemini generation asynchronously using native SDK client."""
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2048,
                safety_settings=RELAXED_SAFETY_SETTINGS,
            ),
        )
        return response.text

    def _is_retryable(self, exc: Exception) -> bool:
        """Return True for transient 503 / overloaded / quota errors."""
        msg = str(exc).lower()
        return any(k in msg for k in ("503", "unavailable", "overloaded", "resource_exhausted", "429", "quota"))

    async def _generate_with_retry(self, prompt: str, max_attempts: int = 3) -> str:
        """Generate content with exponential-backoff retries on transient errors."""
        for attempt in range(max_attempts):
            try:
                return await self._generate(prompt)
            except Exception as e:
                if self._is_retryable(e) and attempt < max_attempts - 1:
                    wait = 2 ** attempt  # 1s, 2s, 4s…
                    logger.warning(
                        "Gemini transient error — retrying",
                        extra={"attempt": attempt + 1, "wait_s": wait, "error": str(e)},
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
        raise RuntimeError("Gemini service unavailable after retries")

    async def classify(self, question: str) -> tuple[QuestionCategory, float]:
        """Classify question type. Returns (category, confidence)."""
        prompt = CLASSIFICATION_PROMPT.format(question=question)
        try:
            raw = await self._generate_with_retry(prompt)
            # Extract JSON — Gemini may wrap in markdown
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                category = data.get("category", "Technical")
                confidence = float(data.get("confidence", 0.8))
                if category not in ("Technical", "Behavioral", "Project-Based", "HR"):
                    category = "Technical"
                return category, min(max(confidence, 0.0), 1.0)
        except Exception as e:
            logger.warning("Classification failed, defaulting to Technical", extra={"error": str(e)})
        return "Technical", 0.5

    async def generate_answer(self, prompt: str) -> str:
        """Generate answer with exponential-backoff retry."""
        return await self._generate_with_retry(prompt)

    async def generate_answer_stream(self, prompt: str):
        """Stream answer from Gemini model, with retry on transient errors."""
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response_stream = await self._client.aio.models.generate_content_stream(
                    model=self._model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        max_output_tokens=2048,
                        safety_settings=RELAXED_SAFETY_SETTINGS,
                    ),
                )
                async for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                return  # stream completed successfully
            except ValueError as ve:
                logger.error("Gemini stream generation hit a safety filter (Content has no parts)", extra={"error": str(ve)})
                raise RuntimeError(f"Safety filter blocked response: {str(ve)}")
            except Exception as e:
                if self._is_retryable(e) and attempt < max_attempts - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "Gemini stream transient error — retrying",
                        extra={"attempt": attempt + 1, "wait_s": wait, "error": str(e)},
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("Gemini stream generation failed", extra={"error": str(e)})
                    raise RuntimeError(f"Gemini stream generation failed: {str(e)}")

    async def stream_voice_answer(
        self,
        question: str,
        context: str = "",
        history: list[dict] | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Real-time voice streaming with:
        - Voice-optimized system prompt (concise, no markdown)
        - Optional RAG context injection
        - Optional conversation history (last N turns)
        - Cancellation support via cancel_event (early question detection restart)
        """
        # Build contents list with conversation history
        contents = []

        if history:
            for turn in history[-3:]:   # last 3 turns for context window efficiency
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(text=turn.get("question", ""))]
                ))
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part(text=turn.get("answer", ""))]
                ))

        # Build user message with optional RAG context
        user_text = question
        if context:
            user_text = f"Relevant context:\n{context}\n\nQuestion: {question}"

        contents.append(types.Content(
            role="user",
            parts=[types.Part(text=user_text)]
        ))

        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                response_stream = await self._client.aio.models.generate_content_stream(
                    model=self._model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=VOICE_SYSTEM_PROMPT,
                        temperature=0.5,        # faster, more consistent first token
                        max_output_tokens=512,  # 3 short paragraphs max
                        safety_settings=RELAXED_SAFETY_SETTINGS,
                    ),
                )
                async for chunk in response_stream:
                    # Check cancellation on every token
                    if cancel_event and cancel_event.is_set():
                        logger.info("Voice stream cancelled — transcript updated")
                        return
                    if chunk.text:
                        yield chunk.text
                return
            except ValueError as ve:
                logger.error("Voice stream generation hit a safety filter (Content has no parts)", extra={"error": str(ve)})
                raise RuntimeError(f"Safety filter blocked voice response: {str(ve)}")
            except Exception as e:
                if self._is_retryable(e) and attempt < max_attempts - 1:
                    wait = 1
                    logger.warning(
                        "Voice stream transient error — retrying",
                        extra={"attempt": attempt + 1, "error": str(e)},
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("Voice stream failed", extra={"error": str(e)})
                    raise RuntimeError(f"Voice stream failed: {str(e)}")


# Singleton
_gemini_instance: GeminiService | None = None


def get_gemini() -> GeminiService:
    if _gemini_instance is None:
        raise RuntimeError("GeminiService not initialized")
    return _gemini_instance


def get_gemini_service_custom(api_key: str | None = None, model: str | None = None) -> GeminiService:
    """Get GeminiService client, falling back to system defaults or singleton if config matches."""
    key = api_key or settings.GEMINI_API_KEY
    mdl = model or settings.GEMINI_MODEL

    if not key:
        raise ValueError("GEMINI_API_KEY is not set.")

    global _gemini_instance
    if _gemini_instance and _gemini_instance.api_key == key and _gemini_instance._model == mdl:
        return _gemini_instance

    return GeminiService(api_key=key, model=mdl)


def init_gemini(api_key: str, model: str) -> GeminiService:
    global _gemini_instance
    _gemini_instance = GeminiService(api_key, model)
    return _gemini_instance
