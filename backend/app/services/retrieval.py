from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import numpy as np

from app.db.models import ResumeChunk
from app.services.embedder import get_embedder
from app.schemas.interview import ChunkView
from app.core.config import get_settings

settings = get_settings()


async def retrieve(
    question: str,
    user_id: UUID,
    db: AsyncSession,
    top_k: int | None = None,
    q_vector: np.ndarray | None = None,
) -> list[ChunkView]:
    """
    Embed the question and search the user's chunks using Supabase pgvector cosine distance.
    Returns semantic matches isolated by user_id.
    """
    k = top_k or settings.RETRIEVAL_TOP_K
    embedder = get_embedder()

    if q_vector is None:
        q_vector = await embedder.embed_one(question)

    # Use pgvector's cosine distance operator (<=>) represented by cosine_distance in SQLAlchemy
    distance_col = ResumeChunk.embedding.cosine_distance(q_vector)
    
    result = await db.execute(
        select(ResumeChunk, distance_col)
        .where(ResumeChunk.user_id == user_id)
        .order_by(distance_col)
        .limit(k)
    )
    
    chunk_views = []
    for chunk_obj, distance in result.all():
        score = 1.0 - float(distance) if distance is not None else 0.0
        chunk_views.append(
            ChunkView(
                text=chunk_obj.chunk_text,
                source=chunk_obj.source,
                section=chunk_obj.section,
                score=round(max(0.0, min(1.0, score)), 4),
            )
        )
        
    return chunk_views
