"""
FAISS Vector Store — per-user index files with atomic saves and metadata sidecars.
"""
import json
from collections import OrderedDict
from dataclasses import dataclass, asdict
from pathlib import Path
from uuid import UUID

import faiss
import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ChunkMeta:
    faiss_id: int
    text: str
    source: str     # "resume" | "project" | "skill"
    section: str
    item_id: str    # DB UUID of the originating record


class VectorStore:
    """
    Manages per-user FAISS IndexFlatIP indices.
    Vectors must be L2-normalized before insertion (cosine similarity via inner product).
    """

    def __init__(self, index_dir: str, dim: int = 384):
        self._index_dir = Path(index_dir)
        self._index_dir.mkdir(parents=True, exist_ok=True)
        self._dim = dim
        self._cache = OrderedDict()
        self._max_cache_size = 50  # Prevent memory exhaustion under load

    def _index_path(self, user_id: UUID) -> Path:
        return self._index_dir / f"{user_id}.index"

    def _meta_path(self, user_id: UUID) -> Path:
        return self._index_dir / f"{user_id}.meta.json"

    # ── Build / Replace ───────────────────────────────────────────────────────

    def build(self, user_id: UUID, vectors: np.ndarray, meta: list[ChunkMeta]) -> None:
        """
        (Re)build the user's entire index from scratch.
        Uses atomic write: write to temp file, then rename.
        """
        if vectors.shape[0] == 0:
            logger.warning("build called with 0 vectors", extra={"user_id": str(user_id)})
            return

        index = faiss.IndexFlatIP(self._dim)
        index.add(vectors.astype(np.float32))

        # Atomic save — write to temp then rename
        tmp_index = self._index_path(user_id).with_suffix(".tmp.index")
        faiss.write_index(index, str(tmp_index))
        tmp_index.rename(self._index_path(user_id))

        meta_payload = [asdict(m) for m in meta]
        tmp_meta = self._meta_path(user_id).with_suffix(".tmp.json")
        tmp_meta.write_text(json.dumps(meta_payload, indent=2), encoding="utf-8")
        tmp_meta.rename(self._meta_path(user_id))

        # Update cache with LRU eviction
        self._cache[user_id] = (index, meta_payload)
        self._cache.move_to_end(user_id)
        if len(self._cache) > self._max_cache_size:
            self._cache.popitem(last=False)

        logger.info("FAISS index built", extra={
            "user_id": str(user_id),
            "num_vectors": vectors.shape[0],
        })

    # ── Search ────────────────────────────────────────────────────────────────

    def search(self, user_id: UUID, query_vector: np.ndarray, top_k: int = 5) -> list[dict]:
        """
        Returns top-k results as dicts: {text, source, section, score}.
        Returns [] if no index exists for the user.
        """
        index_path = self._index_path(user_id)
        meta_path  = self._meta_path(user_id)

        if user_id in self._cache:
            self._cache.move_to_end(user_id)
            index, meta_list = self._cache[user_id]
        else:
            if not index_path.exists():
                logger.warning("No FAISS index for user", extra={"user_id": str(user_id)})
                return []

            index = faiss.read_index(str(index_path))
            meta_list = json.loads(meta_path.read_text(encoding="utf-8"))
            self._cache[user_id] = (index, meta_list)
            self._cache.move_to_end(user_id)
            if len(self._cache) > self._max_cache_size:
                self._cache.popitem(last=False)

        q = query_vector.reshape(1, -1).astype(np.float32)
        k = min(top_k, index.ntotal)
        scores, indices = index.search(q, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(meta_list):
                continue
            chunk = meta_list[idx]
            results.append({
                "text":    chunk["text"],
                "source":  chunk["source"],
                "section": chunk["section"],
                "score":   float(score),
            })

        return results

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete(self, user_id: UUID) -> None:
        if user_id in self._cache:
            del self._cache[user_id]
        for path in [self._index_path(user_id), self._meta_path(user_id)]:
            if path.exists():
                path.unlink()
        logger.info("FAISS index deleted", extra={"user_id": str(user_id)})

    def exists(self, user_id: UUID) -> bool:
        return self._index_path(user_id).exists()


# Singleton
_store_instance: VectorStore | None = None


def get_vector_store() -> VectorStore:
    if _store_instance is None:
        raise RuntimeError("VectorStore not initialized")
    return _store_instance


def init_vector_store(index_dir: str, dim: int = 384) -> VectorStore:
    global _store_instance
    _store_instance = VectorStore(index_dir, dim)
    return _store_instance
