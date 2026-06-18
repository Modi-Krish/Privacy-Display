"""
Backend integration tests — run with: pytest tests/ -v
Requires: pip install pytest pytest-asyncio httpx
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
import numpy as np

from app.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── Health ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"



# ── Chunker ───────────────────────────────────────────────────────────────────

def test_chunker_basic():
    from app.services.chunker import chunk_text
    chunks = chunk_text("word " * 600, "resume", "general", "test-id", chunk_size=512, overlap=64)
    assert len(chunks) >= 1
    for c in chunks:
        assert len(c.text.split()) <= 512 + 5   # allow slight overshoot
        assert c.source == "resume"


def test_chunker_empty():
    from app.services.chunker import chunk_text
    chunks = chunk_text("", "resume", "general", "test-id")
    assert chunks == []


def test_chunker_invalid_params():
    import pytest
    from app.services.chunker import chunk_text
    with pytest.raises(ValueError):
        chunk_text("word " * 10, "resume", "general", "test-id", chunk_size=50, overlap=50)


# ── Confidence Scorer ─────────────────────────────────────────────────────────

def test_confidence_high():
    from app.services.confidence import compute_confidence
    from app.schemas.interview import ChunkView
    chunks = [ChunkView(text="t", source="resume", section="general", score=0.92)]
    score = compute_confidence(chunks, 0.95, "word " * 100)
    assert score >= 0.7


def test_confidence_no_chunks():
    from app.services.confidence import compute_confidence
    score = compute_confidence([], 0.5, "word " * 10)
    assert 0.0 <= score <= 1.0


# ── Prompt Builder ────────────────────────────────────────────────────────────

def test_prompt_builder_with_context():
    from app.services.prompt_builder import build_prompt
    from app.schemas.interview import ChunkView
    chunks = [ChunkView(text="Built RAG pipeline", source="resume", section="projects", score=0.88)]
    prompt = build_prompt("Tell me about your projects", "Project-Based", chunks)
    assert "Built RAG pipeline" in prompt
    assert "Project-Based" in prompt
    assert "Tell me about your projects" in prompt


def test_prompt_builder_no_context():
    from app.services.prompt_builder import build_prompt
    prompt = build_prompt("Tell me about yourself", "HR", [])
    assert "Tell me about yourself" in prompt
    assert "HR" in prompt


# ── Vector Store ──────────────────────────────────────────────────────────────

def test_vector_store_build_search_delete(tmp_path):
    from app.services.vector_store import VectorStore, ChunkMeta
    import uuid

    store = VectorStore(str(tmp_path), dim=8)
    user_id = uuid.uuid4()

    vectors = np.random.rand(5, 8).astype(np.float32)
    # Normalize
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms

    meta = [ChunkMeta(faiss_id=i, text=f"chunk {i}", source="resume", section="general", item_id=str(uuid.uuid4()))
            for i in range(5)]

    store.build(user_id, vectors, meta)
    assert store.exists(user_id)

    results = store.search(user_id, vectors[0], top_k=3)
    assert len(results) == 3
    assert results[0]["score"] >= results[-1]["score"]  # sorted descending

    store.delete(user_id)
    assert not store.exists(user_id)

    empty = store.search(user_id, vectors[0], top_k=3)
    assert empty == []


# ── Resume Parser ─────────────────────────────────────────────────────────────

def test_is_scanned_pdf_short():
    from app.services.resume_parser import is_scanned_pdf
    assert is_scanned_pdf("abc") is True
    assert is_scanned_pdf("word " * 20) is False
