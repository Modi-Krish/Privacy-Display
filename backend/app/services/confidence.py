"""
Confidence Scorer — blends retrieval score, classification confidence,
and response quality heuristics into a single [0, 1] float.
"""
from app.schemas.interview import ChunkView


def compute_confidence(
    chunks: list[ChunkView],
    category_confidence: float,
    answer: str,
) -> float:
    """
    Weighted blend:
      40% — best retrieval score (cosine similarity of top chunk)
      35% — classification confidence
      25% — answer quality heuristic (length & structure)
    """
    # Retrieval score
    if chunks:
        retrieval_score = max(c.score for c in chunks)
        retrieval_score = max(0.0, min(1.0, retrieval_score))
    else:
        retrieval_score = 0.0

    # Classification confidence
    class_score = max(0.0, min(1.0, category_confidence))

    # Answer quality heuristic
    word_count = len(answer.split())
    if word_count >= 80:
        quality_score = 1.0
    elif word_count >= 40:
        quality_score = 0.75
    elif word_count >= 20:
        quality_score = 0.5
    else:
        quality_score = 0.25

    composite = (
        0.40 * retrieval_score +
        0.35 * class_score +
        0.25 * quality_score
    )
    return round(composite, 3)
