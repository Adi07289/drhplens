"""
tools/embedder.py — bge-m3 embedding wrapper.

Provides a @functools.lru_cache singleton for the SentenceTransformer model.
Wave 4 will additionally wrap get_embedder() with @st.cache_resource when
imported under Streamlit, to survive Streamlit reruns.

Model: BAAI/bge-m3
  - Output dimension: 1024
  - normalize_embeddings=True (unit L2 norm — Qdrant cosine distance)
  - Supports dense, sparse, and multi-vector; we use dense only in Phase 1

CPU performance (HF Spaces 2vCPU):
  - Query encoding: ~200 ms (max_length=512)
  - Batch encoding: batch_size=4, ~3 sec/batch on CPU (RESEARCH §A3)

First call downloads ~1.1 GB model weights to ~/.cache/huggingface/hub/.
Subsequent calls load from cache (<1 sec warm).

Usage:
    from tools.embedder import embed_query, embed_batch
    vec = embed_query("What are the risk factors?")  # list[float], len=1024
    vecs = embed_batch(["text 1", "text 2"])          # list[list[float]]
"""
from __future__ import annotations

import functools

# Attempt to import SentenceTransformer at module level so that tests can
# patch 'tools.embedder.SentenceTransformer' at the module boundary.
# When sentence-transformers is not installed (e.g. CI without heavy deps),
# a sentinel None is placed here; tests must patch it before calling
# get_embedder(), which is exactly what the unit tests do.
try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover — present only in CI without torch
    SentenceTransformer = None  # type: ignore[assignment,misc]

MODEL_NAME = "BAAI/bge-m3"
EMBEDDING_DIM = 1024


@functools.lru_cache(maxsize=1)
def get_embedder():  # type: ignore[return]
    """Return the cached SentenceTransformer model singleton.

    @functools.lru_cache ensures the model is loaded at most once per process.
    In Streamlit (Wave 4), this is additionally wrapped with @st.cache_resource
    to survive reruns without reloading weights.

    The model runs on CPU (device="cpu"). Apple Silicon MPS is NOT used here
    because the offline ingest pipeline runs in a conda/x86 environment; the
    Streamlit app on HF Spaces also runs on CPU.
    """
    if SentenceTransformer is None:
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Run: pip install sentence-transformers"
        )
    return SentenceTransformer(MODEL_NAME, device="cpu")


def embed_query(text: str) -> list[float]:
    """Encode a single query string to a 1024-float normalized vector.

    Args:
        text: The query text to encode. max_length=512 is sufficient for
              plain-English questions and reduces CPU latency.

    Returns:
        A Python list of 1024 floats with L2 norm ~= 1.0
        (normalize_embeddings=True ensures this).
    """
    model = get_embedder()
    vector = model.encode(
        text,
        max_length=512,
        normalize_embeddings=True,
    )
    return vector.tolist()


def embed_batch(texts: list[str], batch_size: int = 4) -> list[list[float]]:
    """Encode a list of strings to 1024-float normalized vectors.

    batch_size=4 is the CPU sweet-spot on HF Spaces 2vCPU during offline ingest
    (per RESEARCH §A3). Larger batches increase memory pressure without CPU speedup.

    Args:
        texts: List of strings to encode (e.g. chunk_text values).
        batch_size: Encoding batch size. Default 4 for CPU. Use 32+ for GPU.

    Returns:
        List of lists, shape (len(texts), 1024). Each row is L2-normalized.
    """
    if not texts:
        return []
    model = get_embedder()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return [v.tolist() for v in vectors]
