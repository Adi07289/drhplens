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
from rapidfuzz import fuzz

from agent.nodes.cite_check import cite_check, _normalize
from agent.policies import CITE_CHECK_TOKEN_RATIO
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


# ---------------------------------------------------------------------------
# EVAL-03 / Job 2 — numeric grounding must not be gated behind prose overlap.
#
# A concise numeric answer legitimately shares few tokens with a dense financial
# window (the DRHP states figures in millions; the answer is one short sentence),
# so the prose fuzzy gate false-rejects a genuinely-grounded number. The numeric
# reconciliation antibody must decide numeric claims; the prose gate remains the
# sole antibody for purely-qualitative claims.
# ---------------------------------------------------------------------------

# A long, dense financial window: contains the target magnitude in MILLIONS but
# shares almost no other tokens with a short crore-denominated claim, so the
# prose token_set_ratio lands well below CITE_CHECK_TOKEN_RATIO.
_DENSE_MILLIONS_WINDOW = (
    "The following selected financial information has been derived from the "
    "restated consolidated summary statements and should be read together with "
    "the auditor's examination report and the notes appended thereto: "
    "112,473.90 as tabulated across the respective reporting periods presented "
    "herein, subject to rounding and reclassification under applicable Indian "
    "accounting standards and the relevant regulatory disclosure requirements."
)


def test_numeric_claim_grounds_despite_low_prose_overlap():
    """The Job-2 fix (live failure mode): the DRHP states figures in millions, so
    the agent emits a concise millions-denominated sentence that shares almost no
    tokens with the dense window — the number matches, but the prose gate alone
    would false-reject it. It must ground on the numeric match."""
    claim_text = "Revenue from operations was ₹112,473.90 million"
    # Precondition: the prose gate alone would reject this (documents the scenario).
    ratio = fuzz.token_set_ratio(_normalize(claim_text), _normalize(_DENSE_MILLIONS_WINDOW))
    assert ratio < CITE_CHECK_TOKEN_RATIO, (
        f"test scenario invalid: prose ratio {ratio} should be below the gate "
        f"{CITE_CHECK_TOKEN_RATIO}"
    )
    answer = _make_answer([
        _make_claim(text=claim_text, span_offsets=(0, len(_DENSE_MILLIONS_WINDOW)))
    ])
    retrieved = {"chunk_001": _DENSE_MILLIONS_WINDOW}
    all_grounded, failures = cite_check(answer, retrieved)
    assert all_grounded is True, failures


def test_numeric_claim_crore_vs_million_window_grounds_low_prose():
    """Unit reconciliation must also survive the decouple: a crore-denominated
    claim grounds against the same magnitude written in millions even when prose
    overlap is below the gate (11,247.39 crore == 112,473.90 million)."""
    window = (
        "Set forth below are selected line items derived from the restated "
        "consolidated statement of profit and loss, all amounts stated in "
        "112,473.90 million unless otherwise indicated, prepared under the "
        "applicable recognition and measurement principles and reviewed by the "
        "statutory auditors as part of their examination engagement herein."
    )
    claim_text = "Revenue from operations was ₹11,247.39 crore"
    ratio = fuzz.token_set_ratio(_normalize(claim_text), _normalize(window))
    assert ratio < CITE_CHECK_TOKEN_RATIO, f"scenario invalid: ratio {ratio}"
    answer = _make_answer([_make_claim(text=claim_text, span_offsets=(0, len(window)))])
    all_grounded, failures = cite_check(answer, {"chunk_001": window})
    assert all_grounded is True, failures


def test_low_prose_number_swap_still_fails():
    """Decoupling must NOT let a hallucinated number through: a non-reconciling
    number in a low-prose window stays ungrounded (P2 antibody intact)."""
    claim_text = "Revenue from operations was ₹99,999.99 crore"  # != 112,473.90 million
    answer = _make_answer([
        _make_claim(
            claim_id="c_swap01",
            text=claim_text,
            span_offsets=(0, len(_DENSE_MILLIONS_WINDOW)),
        )
    ])
    retrieved = {"chunk_001": _DENSE_MILLIONS_WINDOW}
    all_grounded, failures = cite_check(answer, retrieved)
    assert all_grounded is False
    assert any("c_swap01" in f for f in failures)


def test_low_prose_qualitative_claim_still_blocked():
    """A purely-qualitative claim (no numbers) with low prose overlap still fails
    via the prose gate — the qualitative antibody is unchanged by the fix."""
    claim_text = "The company has expanded into European retail markets"
    answer = _make_answer([
        _make_claim(
            claim_id="c_qual01",
            text=claim_text,
            span_offsets=(0, len(_DENSE_MILLIONS_WINDOW)),
        )
    ])
    retrieved = {"chunk_001": _DENSE_MILLIONS_WINDOW}
    all_grounded, failures = cite_check(answer, retrieved)
    assert all_grounded is False
    assert any("c_qual01" in f for f in failures)
