"""
Unit tests for tools/embedder.py and the storage/vector.py ChunkPayload schema.

Wave 2 — implements all 7 test cases from 01-03-PLAN.md Task 1 <behavior>.

Tests marked @pytest.mark.slow require bge-m3 model download (~1.1 GB).
Run normally with: pytest tests/unit/test_embedder.py -m "not slow"
Run all including model: pytest tests/unit/test_embedder.py --run-slow
"""
from __future__ import annotations

import math
import os
from unittest.mock import MagicMock, patch

import pytest

from tools.embedder import EMBEDDING_DIM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_embedder(dim: int = EMBEDDING_DIM):
    """Return a mock fastembed TextEmbedding producing deterministic dim-d vectors.

    fastembed's ``embed(texts)`` returns a GENERATOR of (unnormalized) np arrays in
    input order; the ``tools.embedder`` wrapper L2-normalizes them. The fake mirrors
    that contract so the wrapper's normalization is exercised, not bypassed.
    """
    import numpy as np

    class FakeModel:
        def embed(self, texts, *, batch_size=32, **kwargs):
            for text in texts:
                rng = sum(ord(c) for c in text) % 997  # deterministic seed from text
                # Deliberately UN-normalized (magnitude 2.0) so the wrapper's
                # _normalize is what brings the vector to unit norm.
                yield np.full(dim, 2.0 + rng * 0.0001, dtype=np.float32)

    return FakeModel()


# ---------------------------------------------------------------------------
# Test 1: Singleton identity
# ---------------------------------------------------------------------------


def test_get_embedder_returns_singleton_across_calls() -> None:
    """get_embedder() is get_embedder() — lru_cache ensures same object identity."""
    from tools.embedder import get_embedder

    fake = _make_fake_embedder()
    with patch("tools.embedder.TextEmbedding", return_value=fake):
        # Clear the cache before testing
        get_embedder.cache_clear()
        a = get_embedder()
        b = get_embedder()
        assert a is b, "get_embedder() must return the same object on repeated calls (lru_cache)"
        get_embedder.cache_clear()


# ---------------------------------------------------------------------------
# Test 2: embed_query returns 1024-dim vector
# ---------------------------------------------------------------------------


def test_embed_query_returns_1024_dim() -> None:
    """embed_query('test') must return a list of exactly 1024 floats."""
    from tools.embedder import embed_query, get_embedder

    fake = _make_fake_embedder()
    with patch("tools.embedder.TextEmbedding", return_value=fake):
        get_embedder.cache_clear()
        vec = embed_query("test")
        assert isinstance(vec, list), "embed_query must return a Python list"
        assert len(vec) == EMBEDDING_DIM, f"Expected {EMBEDDING_DIM}-dim vector, got {len(vec)}"
        get_embedder.cache_clear()


# ---------------------------------------------------------------------------
# Test 3: embed_query is normalized (L2 norm ≈ 1.0)
# ---------------------------------------------------------------------------


def test_embed_query_normalized() -> None:
    """embed_query result must be L2-normalized: norm in [0.99, 1.01]."""
    from tools.embedder import embed_query, get_embedder

    fake = _make_fake_embedder()
    with patch("tools.embedder.TextEmbedding", return_value=fake):
        get_embedder.cache_clear()
        vec = embed_query("normalize me")
        norm = math.sqrt(sum(x * x for x in vec))
        assert 0.99 <= norm <= 1.01, f"Expected L2 norm ≈ 1.0, got {norm:.6f}"
        get_embedder.cache_clear()


# ---------------------------------------------------------------------------
# Test 4: embed_query is deterministic
# ---------------------------------------------------------------------------


def test_embed_query_deterministic() -> None:
    """Same input must produce the same output on consecutive calls."""
    from tools.embedder import embed_query, get_embedder

    fake = _make_fake_embedder()
    with patch("tools.embedder.TextEmbedding", return_value=fake):
        get_embedder.cache_clear()
        v1 = embed_query("deterministic test input")
        v2 = embed_query("deterministic test input")
        assert v1 == v2, "embed_query must return identical results for identical inputs"
        get_embedder.cache_clear()


# ---------------------------------------------------------------------------
# Test 5: embed_batch returns correct shape
# ---------------------------------------------------------------------------


def test_embed_batch_shape() -> None:
    """embed_batch(['a','b','c']) must return a 3x1024 list-of-lists."""
    from tools.embedder import embed_batch, get_embedder

    fake = _make_fake_embedder()
    with patch("tools.embedder.TextEmbedding", return_value=fake):
        get_embedder.cache_clear()
        vecs = embed_batch(["a", "b", "c"])
        assert len(vecs) == 3, f"Expected 3 vectors, got {len(vecs)}"
        for i, v in enumerate(vecs):
            assert isinstance(v, list), f"Vector {i} must be a list"
            assert len(v) == EMBEDDING_DIM, f"Vector {i} must be {EMBEDDING_DIM}-dim, got {len(v)}"
        get_embedder.cache_clear()


# ---------------------------------------------------------------------------
# Test 6: ChunkPayload field names match RetrievedChunkRef
# ---------------------------------------------------------------------------


def test_chunk_payload_field_names_match_retrieved_chunk_ref() -> None:
    """ChunkPayload fields must round-trip into RetrievedChunkRef without renaming.

    This is the cross-phase contract test (PITFALL 4 + storage-bus invariant).
    If this test breaks, the cite-check node in Wave 3 will silently drop citations.
    """
    from agent.schemas import RetrievedChunkRef
    from storage.vector import ChunkPayload

    # Create a ChunkPayload with all required fields
    cp = ChunkPayload(
        chunk_id="abc-uuid",
        drhp_id="swiggy_2024_11",
        section="Risk Factors",
        page_start=1,
        page_end=2,
        printed_page_label="ii",
        chunk_text="The company faces regulatory risks...",
        span_offsets=(0, 10),
    )

    # Round-trip into RetrievedChunkRef using the same field names directly
    ref = RetrievedChunkRef(
        chunk_id=cp.chunk_id,
        page_start=cp.page_start,
        page_end=cp.page_end,
        section=cp.section,
        span_offsets=cp.span_offsets,
        printed_page_label=cp.printed_page_label,
    )

    # Verify fields match
    assert ref.chunk_id == cp.chunk_id
    assert ref.page_start == cp.page_start
    assert ref.page_end == cp.page_end
    assert ref.section == cp.section
    assert ref.span_offsets == list(cp.span_offsets)  # RetrievedChunkRef span_offsets is list[int]
    assert ref.printed_page_label == cp.printed_page_label

    # Verify JSON serialization works (no unexpected fields)
    data = ref.model_dump()
    assert data["chunk_id"] == "abc-uuid"
    assert data["page_start"] == 1


# ---------------------------------------------------------------------------
# Test 7: COLLECTION_NAME constant
# ---------------------------------------------------------------------------


def test_qdrant_collection_name_constant() -> None:
    """storage.vector.COLLECTION_NAME must equal 'drhp_chunks'."""
    from storage.vector import COLLECTION_NAME

    assert COLLECTION_NAME == "drhp_chunks", (
        f"Expected COLLECTION_NAME == 'drhp_chunks', got '{COLLECTION_NAME}'"
    )


# ---------------------------------------------------------------------------
# Slow tests (require real bge-m3 model download ~1.1 GB)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.skipif(
    not os.environ.get("RUN_SLOW_EMBED"),
    reason="requires ~1.3 GB ONNX model download; set RUN_SLOW_EMBED=1 to run",
)
def test_real_embed_query_1024_dim() -> None:
    """Integration: embed_query with the real fastembed model (BAAI/bge-large-en-v1.5)
    returns a 1024-dim L2-normalized vector.

    Downloads the ONNX weights (~1.3 GB) on first run. Opt-in:
        RUN_SLOW_EMBED=1 pytest tests/unit/test_embedder.py -k real_embed
    """
    from tools.embedder import EMBEDDING_DIM, embed_query, get_embedder

    get_embedder.cache_clear()
    vec = embed_query("What are the risk factors for Swiggy IPO?")
    assert len(vec) == EMBEDDING_DIM, f"Expected {EMBEDDING_DIM}-dim, got {len(vec)}"
    norm = math.sqrt(sum(x * x for x in vec))
    assert 0.99 <= norm <= 1.01, f"Expected L2 norm ≈ 1.0, got {norm:.6f}"
