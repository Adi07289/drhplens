"""
Unit tests for agent/nodes/cite_check.py — deterministic non-LLM cite-check (TRUST-04).

Implements RESEARCH Pattern 3 invariants:
- token_set_ratio >= 80 (rapidfuzz)
- numeric subset check (PITFALL P2: number-swap detection)
- span_offsets ±50 char tolerance
- NO LLM-judge fallback (SKELETON §D invariant)
"""
from __future__ import annotations

import inspect

import pytest

from agent.nodes.cite_check import cite_check, _normalize
from agent.schemas import Claim, GroundedAnswer, RetrievedChunkRef


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source(
    chunk_id: str = "chunk_001",
    span_offsets: tuple[int, int] = (0, 50),
) -> RetrievedChunkRef:
    return RetrievedChunkRef(
        chunk_id=chunk_id,
        page_start=5,
        page_end=6,
        section="Issue Details",
        span_offsets=span_offsets,
    )


def _make_claim(
    claim_id: str = "c_abc123",
    text: str = "The issue size is ₹11,300 crores",
    chunk_id: str = "chunk_001",
    span_offsets: tuple[int, int] = (0, 50),
) -> Claim:
    return Claim(
        claim_id=claim_id,
        text=text,
        source_chunk_id=chunk_id,
        drhp_page=5,
        section="Issue Details",
        verbatim_span=text,
        span_offsets=span_offsets,
        sources=[_make_source(chunk_id=chunk_id, span_offsets=span_offsets)],
    )


def _make_answer(claims: list[Claim]) -> GroundedAnswer:
    prose = " ".join(f"{c.text} {{{{{c.claim_id}}}}}" for c in claims)
    return GroundedAnswer(answer_prose=prose, claims=claims)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_unsupported_claim_rejected():
    """Wave 0 xfail flip: claim text with no match in cited chunk → ungrounded."""
    answer = _make_answer([_make_claim(text="The CEO is Elon Musk", span_offsets=(0, 20))])
    retrieved = {"chunk_001": "Sriharsha Majety and Nandan Reddy are the founders of Swiggy."}
    all_grounded, failures = cite_check(answer, retrieved)
    assert all_grounded is False
    assert any("c_abc123" in f for f in failures)


def test_exact_match_grounded():
    """Claim text identical to a substring of the cited window → grounded."""
    claim_text = "The issue size is ₹11,300 crores"
    answer = _make_answer([_make_claim(text=claim_text, span_offsets=(0, len(claim_text)))])
    retrieved = {
        "chunk_001": f"The issue size is ₹11,300 crores comprising fresh issue and OFS."
    }
    all_grounded, failures = cite_check(answer, retrieved)
    assert all_grounded is True
    assert failures == []


def test_paraphrase_within_ratio_threshold():
    """Near-identical claim text with same numbers → grounded (high token overlap)."""
    # Use very similar text to ensure token_set_ratio >= 80
    answer = _make_answer([
        _make_claim(
            text="The issue size is 11300 crores fresh issue",
            span_offsets=(0, 50),
        )
    ])
    retrieved = {
        "chunk_001": (
            "The total issue size is 11300 crores comprising a fresh issue "
            "and an offer for sale."
        )
    }
    all_grounded, failures = cite_check(answer, retrieved)
    assert all_grounded is True


def test_number_swap_rejected_PITFALL_P2():
    """PITFALL P2: same text structure but wrong number → ungrounded (numeric subset fails)."""
    answer = _make_answer([_make_claim(text="Issue size is ₹11300 crores", span_offsets=(0, 30))])
    retrieved = {"chunk_001": "Issue size is ₹11500 crores comprising fresh issue and OFS."}
    all_grounded, failures = cite_check(answer, retrieved)
    assert all_grounded is False
    assert any("P2" in f or "numeric" in f.lower() for f in failures)


def test_span_offsets_window_tolerance():
    """Claim text 30 chars before span_offsets[0] → still grounded (±50 char tolerance)."""
    # chunk_text has the relevant content at chars 30-80
    chunk_text = "Preamble text here. " + "The issue size is ₹11,300 crores." + " more text"
    # span_offsets points to chars 50-80 (slightly off from where "The issue" starts at 20)
    answer = _make_answer([
        _make_claim(
            text="The issue size is ₹11,300 crores",
            span_offsets=(50, 80),  # ± tolerance of 50 will extend to 0..130, covering the text
        )
    ])
    retrieved = {"chunk_001": chunk_text}
    all_grounded, failures = cite_check(answer, retrieved)
    assert all_grounded is True


def test_normalization_handles_unicode_and_whitespace():
    """NFKC + whitespace collapse normalizes unicode variants → grounded."""
    claim_text = "Issue size is ₹11,300 cr."
    window_text = "Issue size\nis\n₹11,300 cr."  # newlines in chunk
    answer = _make_answer([_make_claim(text=claim_text, span_offsets=(0, len(window_text)))])
    retrieved = {"chunk_001": window_text}
    all_grounded, failures = cite_check(answer, retrieved)
    assert all_grounded is True


def test_no_llm_judge_fallback():
    """SKELETON §D invariant: cite_check.py must not contain LLM client import statements."""
    import ast
    from pathlib import Path

    src = Path("agent/nodes/cite_check.py").read_text()
    tree = ast.parse(src)

    # Collect all import names from actual import statements
    imported_names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_names.append(node.module)

    for forbidden in ("openai", "genai", "instructor", "groq"):
        for name in imported_names:
            assert forbidden not in name, (
                f"cite_check.py must not import {forbidden!r} (SKELETON §D: no LLM-judge fallback). "
                f"Found in import: {name!r}"
            )


def test_chunk_id_missing_from_retrieval_set_fails_check():
    """Claim cites a chunk_id not in retrieved_chunks → ungrounded with 'not in retrieved set'."""
    answer = _make_answer([_make_claim(chunk_id="chunk_999", span_offsets=(0, 30))])
    retrieved = {"chunk_001": "Some chunk text."}  # chunk_999 is NOT here
    all_grounded, failures = cite_check(answer, retrieved)
    assert all_grounded is False
    assert any("not in retrieved set" in f for f in failures)
