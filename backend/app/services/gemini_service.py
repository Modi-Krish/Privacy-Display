"""
Gemini Service — question classification + answer generation.
"""
import asyncio
import json
import re
from typing import Literal

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

QuestionCategory = Literal["Technical", "Behavioral", "Project-Based", "HR"]

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

    async def _generate(self, prompt: str) -> str:
        """Run Gemini generation asynchronously using native SDK client."""
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=1024,
            ),
        )
        return response.text

    async def classify(self, question: str) -> tuple[QuestionCategory, float]:
        """Classify question type. Returns (category, confidence)."""
        prompt = CLASSIFICATION_PROMPT.format(question=question)
        try:
            raw = await self._generate(prompt)
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
        """Generate answer with one retry on failure."""
        for attempt in range(2):
            try:
                return await self._generate(prompt)
            except Exception as e:
                logger.warning(
                    "Gemini generation failed",
                    extra={"attempt": attempt + 1, "error": str(e)},
                )
                if attempt == 0:
                    await asyncio.sleep(0.5)  # brief pause before retry

        raise RuntimeError("Gemini service unavailable after retry")


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
