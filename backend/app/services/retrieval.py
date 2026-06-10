"""
Retrieval Service — semantic search over FAISS with a fallback to empty context.
"""
from uuid import UUID

import numpy as np

from app.services.vector_store import get_vector_store
from app.services.embedder import get_embedder
from app.schemas.interview import ChunkView
from app.core.config import get_settings

settings = get_settings()


async def retrieve(
    question: str,
    user_id: UUID,
    top_k: int | None = None,
    q_vector: np.ndarray | None = None,
) -> list[ChunkView]:
    """
    Embed the question and search the user's FAISS index.
    Returns [] if no index exists (caller checks is_personalized).
    """
    k = top_k or settings.RETRIEVAL_TOP_K
    embedder = get_embedder()
    store = get_vector_store()

    if q_vector is None:
        q_vector = await embedder.embed_one(question)

    raw_results = store.search(user_id, q_vector, top_k=k)

    return [
        ChunkView(
            text=r["text"],
            source=r["source"],
            section=r["section"],
            score=r["score"],
        )
        for r in raw_results
    ]
