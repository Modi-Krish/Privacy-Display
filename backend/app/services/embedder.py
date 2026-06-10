"""
Embedder Service — wraps sentence-transformers for vector generation.
Model is loaded once at startup and shared across requests.
"""
import asyncio
from functools import lru_cache
from typing import Any

import numpy as np


class EmbedderService:
    """
    Lazy-loaded sentence transformer. Thread-safe for concurrent async use
    because the model.encode() call is run in an executor.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model: Any = None

    def load(self) -> None:
        """Call this once during app lifespan startup."""
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(self._model_name)

    def _encode_sync(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("EmbedderService not loaded. Call load() first.")
        vectors = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.array(vectors, dtype=np.float32)

    async def embed_many(self, texts: list[str]) -> np.ndarray:
        """Async wrapper — runs encoding in thread pool to avoid blocking."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._encode_sync, texts)

    async def embed_one(self, text: str) -> np.ndarray:
        vectors = await self.embed_many([text])
        return vectors[0]


# Singleton — instantiated in main.py lifespan, injected via dependency
_embedder_instance: EmbedderService | None = None


def get_embedder() -> EmbedderService:
    if _embedder_instance is None:
        raise RuntimeError("Embedder not initialized")
    return _embedder_instance


def init_embedder(model_name: str = "all-MiniLM-L6-v2") -> EmbedderService:
    global _embedder_instance
    _embedder_instance = EmbedderService(model_name)
    _embedder_instance.load()
    return _embedder_instance
