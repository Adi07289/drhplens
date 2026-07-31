"""Unit tests for the deterministic span-overlap metrics (06.1-01 Task 2).

``recall_at_k`` and ``citation_accuracy`` are pure, model-free page-range span-overlap
functions lifted from ``scripts/run_eval.py``. They must import with NO agent/qdrant/LLM
dependency, and ``recall_at_k`` must slice over the FULL candidate list
(``retrieved_chunks`` — the 50 Qdrant candidates) so k=5/10/30 are meaningful — NOT over
the 5-capped reranked window (spike 003, measured decision #2; ``RERANK_TOP_K=5``).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from eval.metrics.citation import citation_accuracy
from eval.metrics.recall import recall_at_k

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _chunk(page_start: int, page_end: int) -> dict:
    """A minimal Qdrant-style chunk carrying only the span payload the metrics read."""
    return {"payload": {"page_start": page_start, "page_end": page_end}}


# ---------------------------------------------------------------------------
# recall_at_k
# ---------------------------------------------------------------------------


def test_recall_empty_expected_is_vacuously_one():
    assert recall_at_k([], [_chunk(1, 2)], k=5) == 1.0


def test_recall_span_present_in_top_k_is_one():
    expected = [{"page_start": 30, "page_end": 40}]
    chunks = [_chunk(35, 35)] + [_chunk(200 + i, 200 + i) for i in range(9)]
    assert recall_at_k(expected, chunks, k=5) == 1.0


def test_recall_k_slice_operates_over_full_candidate_list():
    # The single overlapping chunk sits at index 7 — past the top-5, inside the top-10.
    # This proves the k slice runs over the full 50-candidate list, not a 5-capped one
    # (the whole point of computing recall over retrieved_chunks, not reranked_top_k).
    expected = [{"page_start": 30, "page_end": 40}]
    chunks = [_chunk(200 + i, 200 + i) for i in range(30)]
    chunks[7] = _chunk(35, 35)  # the only overlapping chunk, at index 7
    assert recall_at_k(expected, chunks, k=5) == 0.0  # absent from the top-5
    assert recall_at_k(expected, chunks, k=10) == 1.0  # present within the top-10
    assert recall_at_k(expected, chunks, k=30) == 1.0  # present within the top-30


def test_recall_is_fraction_hits_over_expected_sources():
    present = {"page_start": 30, "page_end": 40}
    absent = {"page_start": 500, "page_end": 510}
    chunks = [_chunk(35, 35)] + [_chunk(200 + i, 200 + i) for i in range(9)]
    # one of two expected spans is retrieved within the top-5 -> 0.5
    assert recall_at_k([present, absent], chunks, k=5) == 0.5


# ---------------------------------------------------------------------------
# citation_accuracy
# ---------------------------------------------------------------------------


def test_citation_empty_expected_is_vacuously_one():
    assert citation_accuracy([], [_chunk(1, 2)]) == 1.0


def test_citation_all_spans_overlap_is_one():
    expected = [
        {"page_start": 30, "page_end": 40},
        {"page_start": 100, "page_end": 110},
    ]
    chunks = [_chunk(35, 38), _chunk(105, 108)]
    assert citation_accuracy(expected, chunks) == 1.0


def test_citation_one_span_without_overlap_is_proportional():
    expected = [
        {"page_start": 30, "page_end": 40},
        {"page_start": 500, "page_end": 510},
    ]
    chunks = [_chunk(35, 38)]
    assert citation_accuracy(expected, chunks) == 0.5


def test_citation_scans_all_chunks_no_k_cap():
    # The only overlapping chunk sits well past any top-5 window; citation-accuracy
    # asks "did the cited page contain the claim" over ALL chunks, so it must find it.
    expected = [{"page_start": 30, "page_end": 40}]
    chunks = [_chunk(200 + i, 200 + i) for i in range(20)]
    chunks[15] = _chunk(35, 35)
    assert citation_accuracy(expected, chunks) == 1.0


def test_citation_overlap_boundary_is_inclusive():
    # Overlap rule: chunk_start <= exp_end AND chunk_end >= exp_start.
    # Adjacent-but-touching ranges count as overlap.
    expected = [{"page_start": 30, "page_end": 40}]
    assert citation_accuracy(expected, [_chunk(40, 50)]) == 1.0  # touches at exp_end
    assert citation_accuracy(expected, [_chunk(20, 30)]) == 1.0  # touches at exp_start
    assert citation_accuracy(expected, [_chunk(41, 50)]) == 0.0  # just past -> no overlap


# ---------------------------------------------------------------------------
# Purity: no agent/qdrant/LLM import (isolated subprocess so sibling test imports
# in this pytest session can't pollute the sys.modules check).
# ---------------------------------------------------------------------------


def test_metrics_import_without_agent_qdrant_or_llm():
    code = (
        "import sys\n"
        "import eval.metrics.recall, eval.metrics.citation\n"
        "heavy = {'agent', 'qdrant_client', 'deepeval', 'torch', 'langfuse', 'ragas'}\n"
        "pulled = heavy & set(sys.modules)\n"
        "assert not pulled, pulled\n"
        "print('clean')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    assert result.returncode == 0, result.stderr
    assert "clean" in result.stdout


# ── WR-02 hardening: a bound-less (malformed) gold entry must NOT vacuously match ──────
def test_bound_less_expected_source_is_a_miss_not_a_vacuous_hit():
    """A gold entry missing page bounds counts as a miss, never a match-all — so a
    mislabeled entry can't silently inflate the HARD-GATED citation / recall metrics
    (code-review WR-02). Well-formed entries are unaffected."""
    from eval.metrics import citation_accuracy, recall_at_k

    chunks = [{"payload": {"page_start": 5, "page_end": 9}}]
    # well-formed overlap -> hit (behavior preserved)
    assert citation_accuracy([{"page_start": 6, "page_end": 7}], chunks) == 1.0
    assert recall_at_k([{"page_start": 6, "page_end": 7}], chunks, 5) == 1.0
    # missing bounds -> miss (was a vacuous 1.0 before the fix)
    assert citation_accuracy([{}], chunks) == 0.0
    assert citation_accuracy([{"page_start": 6}], chunks) == 0.0
    assert recall_at_k([{}], chunks, 5) == 0.0
    # a chunk without page info can't confirm containment
    assert citation_accuracy([{"page_start": 6, "page_end": 7}], [{"payload": {}}]) == 0.0
