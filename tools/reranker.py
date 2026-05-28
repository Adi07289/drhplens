"""
tools/reranker.py — bge-reranker-v2-m3 cross-encoder reranker wrapper.

Provides a @functools.lru_cache singleton for the FlagReranker model.
Wave 4 will additionally wrap get_reranker() with @st.cache_resource.

Model: BAAI/bge-reranker-v2-m3
  - Cross-encoder: takes (query, passage) pairs; outputs relevance scores
  - use_fp16=True: half-precision inference (faster on Apple Silicon / HF Spaces)
  - Apache-2.0 license; multilingual (handles Indian-English DRHP idioms)

Usage:
    from tools.reranker import rerank
    results = rerank("risk factors", passages, top_k=5)
    # returns [(original_index, score), ...] sorted descending by score
"""
from __future__ import annotations

import functools

try:
    from FlagEmbedding import FlagReranker as _FlagReranker

    _RERANKER_AVAILABLE = True
except ImportError:
    _RERANKER_AVAILABLE = False

MODEL_NAME = "BAAI/bge-reranker-v2-m3"


@functools.lru_cache(maxsize=1)
def get_reranker():
    """Return the cached FlagReranker singleton.

    Raises NotImplementedError if FlagEmbedding is not installed.

    First call downloads ~570 MB model weights to ~/.cache/huggingface/hub/.
    """
    if not _RERANKER_AVAILABLE:
        raise NotImplementedError(
            "FlagEmbedding is not installed. "
            "Install it via: pip install FlagEmbedding. "
            "Reranker tests are xfailed until this dep is resolved."
        )
    return _FlagReranker(MODEL_NAME, use_fp16=True)


def rerank(
    query: str,
    docs: list[str],
    top_k: int = 5,
) -> list[tuple[int, float]]:
    """Rerank a list of passages for relevance to query.

    Uses bge-reranker-v2-m3 cross-encoder to score all (query, doc) pairs,
    then returns the top_k by score in descending order.

    Args:
        query: The user question or query string.
        docs: List of passage strings to rerank (typically the top-50 dense hits).
        top_k: Number of top results to return.

    Returns:
        List of (original_index, score) tuples sorted by score descending.
        Consumer uses the original_index to look up the original document/payload.

    Raises:
        NotImplementedError: If FlagEmbedding is not installed.
    """
    if not docs:
        return []

    reranker = get_reranker()

    # Build (query, passage) pairs for cross-encoder scoring
    pairs = [[query, doc] for doc in docs]
    scores = reranker.compute_score(pairs, normalize=True)

    # Handle single-doc case (compute_score returns a float, not a list)
    if isinstance(scores, float):
        scores = [scores]

    # Sort by score descending, return (index, score) tuples
    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [(idx, float(score)) for idx, score in indexed[:top_k]]
