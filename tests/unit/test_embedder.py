"""
Stub: tools/embedder.py — BAAI/bge-m3 embedding wrapper.

Validates that the bge-m3 embedder:
- Returns 1024-dimensional vectors (bge-m3 output dimension)
- Returns L2-normalized vectors (normalize_embeddings=True)
- Is deterministic: same input → same output

Wave 2 owns this implementation (INGEST-03).
"""
from __future__ import annotations

import pytest

pytest.importorskip("sentence_transformers", reason="sentence-transformers ships in Wave 2 environment")


@pytest.mark.xfail(reason="Wave 2 owns this — implements tools/embedder.py with bge-m3", strict=False)
def test_bge_m3_returns_1024_dim_normalized() -> None:
    """embed_query('test') must return a list of 1024 floats; L2 norm must be ~1.0."""
    assert False, "Wave 2 must implement: call embed_query, assert len==1024 and norm~=1.0"
