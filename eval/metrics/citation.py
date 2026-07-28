"""eval.metrics.citation — deterministic span-overlap citation-accuracy (GATED, model-free).

``citation_accuracy`` is lifted verbatim from ``scripts/run_eval._citation_accuracy``. It
scans ALL chunks (no top-k slice) because the metric asks "did the cited page actually
contain the claim" — the project's custom citation metric (CLAUDE.md; a citation-accuracy
regression is a hard CI failure). Spike 003 flags this (finer-grained than section-range
recall) as the metric that should carry the real retrieval-quality weight; the release
gate blocks at citation_accuracy >= 0.95. Pure, model-free page-range span overlap.
"""
from __future__ import annotations


def citation_accuracy(expected_sources: list[dict], chunks: list[dict]) -> float:
    """Proportion of expected page ranges that overlap ANY returned chunk (no k cap).

    Args:
        expected_sources: gold page-span dicts, each ``{"page_start": int, "page_end": int}``.
        chunks: the returned chunks scanned in full, each a dict with a ``"payload"`` carrying
            ``page_start`` / ``page_end``.

    Returns:
        hits / len(expected_sources) in [0.0, 1.0]; 1.0 vacuously when no expected sources.
    """
    if not expected_sources:
        return 1.0
    hits = 0
    for exp_src in expected_sources:
        exp_start = exp_src.get("page_start", 0)
        exp_end = exp_src.get("page_end", 9999)
        for chunk in chunks:
            payload = chunk.get("payload", {})
            chunk_start = payload.get("page_start", 0)
            chunk_end = payload.get("page_end", 0)
            if chunk_start <= exp_end and chunk_end >= exp_start:
                hits += 1
                break
    return hits / len(expected_sources)
