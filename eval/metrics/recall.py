"""eval.metrics.recall — deterministic span-overlap recall@k (GATED, model-free).

``recall_at_k`` is lifted verbatim from ``scripts/run_eval._recall_at_k``; the chunk
argument is renamed ``retrieved_chunks`` because the caller (06.1-04 runner) passes
``final_state["retrieved_chunks"]`` — the 50 Qdrant candidates — NOT ``reranked_top_k``
(``RERANK_TOP_K=5`` caps the reranked window, making k>5 undefined on it). Slicing
``retrieved_chunks[:k]`` is therefore meaningful at k=5/10/30 (measured decision #2).

Interpretation (P10, honesty invariant): recall@k is a labelled REGRESSION FLOOR, not a
headline quality metric. Spike 003 measured recall@5/10/30 = 1.000 because the current
gold ``expected_sources`` are coarse 10-101-page section ranges (mean 44.5) that
span-overlap trivially satisfies. ``recall@10 >= 0.85`` guards against regression only;
citation-accuracy + faithfulness carry the real retrieval-quality signal. Do NOT
advertise the 1.00 as a quality win until the gold spans are tightened to <=2-3 pages.
"""
from __future__ import annotations


def recall_at_k(expected_sources: list[dict], retrieved_chunks: list[dict], k: int) -> float:
    """Proportion of expected source page ranges appearing in the top-k retrieved chunks.

    Args:
        expected_sources: gold page-span dicts, each ``{"page_start": int, "page_end": int}``.
        retrieved_chunks: the retrieval candidates (the 50 Qdrant hits), each a dict with a
            ``"payload"`` carrying ``page_start`` / ``page_end``. The top-k slice runs over
            THIS full candidate list, so k=5/10/30 are all meaningful.
        k: the top-k cutoff to slice ``retrieved_chunks`` at.

    Returns:
        hits / len(expected_sources) in [0.0, 1.0]; 1.0 vacuously when no expected sources.
    """
    if not expected_sources:
        return 1.0
    top_k = retrieved_chunks[:k]
    hits = 0
    for exp_src in expected_sources:
        exp_start = exp_src.get("page_start")
        exp_end = exp_src.get("page_end")
        # Malformed gold entry (no page bounds) counts as a miss, never a vacuous
        # match-all — the old [0, 9999] default could inflate the gated metric (WR-02).
        if exp_start is None or exp_end is None:
            continue
        for chunk in top_k:
            payload = chunk.get("payload", {})
            chunk_start = payload.get("page_start")
            chunk_end = payload.get("page_end")
            if chunk_start is None or chunk_end is None:
                continue  # chunk without page info can't confirm containment
            if chunk_start <= exp_end and chunk_end >= exp_start:
                hits += 1
                break
    return hits / len(expected_sources)
