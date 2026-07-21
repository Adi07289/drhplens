"""
tools/embedder.py — local ONNX embedding wrapper (fastembed / bge-large-en-v1.5).

Backend swapped from sentence-transformers/bge-m3 to fastembed at the Job-A live-ingest
step. Reason: PyTorch is capped at 2.2.2 on Intel macOS (the last x86-64 wheel) and is
incompatible with the project's NumPy 2.x (the pandas 3.0 / mlflow / shap Phase-5 stack),
so the torch-based bge-m3 path is a dead-end in this local environment. fastembed runs BGE
models via ONNX Runtime — no torch, no NumPy-2 conflict.

Model choice = BAAI/bge-small-en-v1.5 (384-dim, quantized ONNX). Benchmarked on this
CPU: bge-large-en-v1.5 (full ONNX) ran at ~0.2 chunks/s (>1.5 h for the 1.3k-chunk Swiggy
DRHP — unusable and single-core-bound); bge-base-en-v1.5 ~1.3/s (~17 min); bge-small's
quantized model hits ~4.6/s (~5 min) — the only model that ingests in a practical window
on this hardware. The Swiggy corpus is English, so the English-only model is fine; retrieval
quality is lower than bge-large, so re-embed with bge-base/large on a faster/Linux box for a
production deploy (both ingest + retrieval read EMBEDDING_DIM, so bump this module + the
storage.vector collection dim together and re-ingest).

The public interface is unchanged, so both ingest (embed_batch) and retrieval (embed_query)
stay consistent with a single embedding model:

    from tools.embedder import embed_query, embed_batch, EMBEDDING_DIM
    vec  = embed_query("What are the risk factors?")  # list[float], len == EMBEDDING_DIM
    vecs = embed_batch(["text 1", "text 2"])          # list[list[float]]

Model: BAAI/bge-small-en-v1.5 (quantized ONNX via fastembed)
  - Output dimension: 384 (storage.vector.EMBEDDING_DIM must match)
  - L2-normalized (unit norm — Qdrant cosine distance)

First call downloads the ONNX model weights (~0.13 GB) to the stable fastembed cache;
subsequent calls load from cache.
"""
from __future__ import annotations

import functools
import math
import os

# Import at module level so tests can patch 'tools.embedder.TextEmbedding' at the
# module boundary. When fastembed is not installed (e.g. a minimal CI env), a
# sentinel None is placed here and get_embedder() raises a clear install hint.
try:
    from fastembed import TextEmbedding
except ImportError:  # pragma: no cover — present only where fastembed is absent
    TextEmbedding = None  # type: ignore[assignment,misc]

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384


@functools.lru_cache(maxsize=1)
def get_embedder():  # type: ignore[return]
    """Return the cached fastembed TextEmbedding singleton.

    @functools.lru_cache ensures the ONNX model is loaded at most once per process.
    In Streamlit this is additionally wrapped with @st.cache_resource to survive reruns.
    """
    if TextEmbedding is None:
        raise RuntimeError(
            "fastembed is not installed. Run: pip install fastembed"
        )
    # Persist the ONNX weights in a stable cache (not the ephemeral $TMPDIR, which
    # macOS can purge and where an interrupted download leaves a broken snapshot).
    cache_dir = os.environ.get("FASTEMBED_CACHE_DIR") or os.path.join(
        os.path.expanduser("~"), ".cache", "fastembed"
    )
    os.makedirs(cache_dir, exist_ok=True)
    return TextEmbedding(model_name=MODEL_NAME, cache_dir=cache_dir)


def _normalize(vec: list[float]) -> list[float]:
    """L2-normalize to unit norm (Qdrant cosine). Safe on already-normalized vectors."""
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def embed_query(text: str) -> list[float]:
    """Encode a single query string to an EMBEDDING_DIM-float L2-normalized vector."""
    model = get_embedder()
    vector = next(iter(model.embed([text])))
    return _normalize(vector.tolist())


def embed_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """Encode a list of strings to EMBEDDING_DIM-float L2-normalized vectors.

    Returns a list of lists, shape (len(texts), EMBEDDING_DIM). Each row is L2-normalized.
    fastembed streams results in input order, so the output aligns with ``texts``.
    """
    if not texts:
        return []
    model = get_embedder()
    return [_normalize(v.tolist()) for v in model.embed(texts, batch_size=batch_size)]
