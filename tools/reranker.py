"""
tools/reranker.py — ONNX cross-encoder reranker wrapper (fastembed).

Swapped from FlagEmbedding/bge-reranker-v2-m3 to fastembed at the Job-A step: FlagReranker
pulls in torch, which is a dead-end on Intel macOS (torch 2.2.2 is incompatible with the
project's NumPy 2.x — see tools/embedder.py). fastembed runs cross-encoders via ONNX Runtime
— no torch. Model = Xenova/ms-marco-MiniLM-L-6-v2 (tiny, ~0.08 GB): reranking only scores
the top-N dense hits (not the whole corpus), so it stays fast on CPU. It is a quality step
down from the multilingual bge-reranker-v2-m3; re-point MODEL_NAME to BAAI/bge-reranker-base
(also fastembed/ONNX) on a faster/Linux box for a production deploy.

Usage:
    from tools.reranker import rerank
    results = rerank("risk factors", passages, top_k=5)
    # returns [(original_index, score), ...] sorted descending by score
"""
from __future__ import annotations

import functools
import os

try:
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    _RERANKER_AVAILABLE = True
except ImportError:  # pragma: no cover — present only where fastembed is absent
    _RERANKER_AVAILABLE = False

MODEL_NAME = "Xenova/ms-marco-MiniLM-L-6-v2"


@functools.lru_cache(maxsize=1)
def get_reranker():
    """Return the cached fastembed TextCrossEncoder singleton.

    Raises NotImplementedError if fastembed is not installed. First call downloads
    the ONNX weights (~0.08 GB) to the stable fastembed cache.
    """
    if not _RERANKER_AVAILABLE:
        raise NotImplementedError(
            "fastembed is not installed. Install it via: pip install fastembed."
        )
    cache_dir = os.environ.get("FASTEMBED_CACHE_DIR") or os.path.join(
        os.path.expanduser("~"), ".cache", "fastembed"
    )
    os.makedirs(cache_dir, exist_ok=True)
    return TextCrossEncoder(model_name=MODEL_NAME, cache_dir=cache_dir)


def rerank(
    query: str,
    docs: list[str],
    top_k: int = 5,
) -> list[tuple[int, float]]:
    """Rerank a list of passages for relevance to query.

    Uses the fastembed ONNX cross-encoder to score all (query, doc) pairs, then
    returns the top_k by score in descending order.

    Args:
        query: The user question or query string.
        docs: List of passage strings to rerank (typically the top-N dense hits).
        top_k: Number of top results to return.

    Returns:
        List of (original_index, score) tuples sorted by score descending. The
        consumer uses original_index to look up the original document/payload.

    Raises:
        NotImplementedError: If fastembed is not installed.
    """
    if not docs:
        return []

    reranker = get_reranker()
    # fastembed yields one relevance score per document, in input order.
    scores = list(reranker.rerank(query, docs))
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [(idx, float(score)) for idx, score in indexed[:top_k]]
