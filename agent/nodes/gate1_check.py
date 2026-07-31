"""
agent/nodes/gate1_check.py — Pre-LLM retrieval-score gate (D-05 Gate 1).

Reads the maximum reranker score from reranked_top_k and compares it against
GATE1_THRESHOLD. If the score is below the threshold, the graph routes to
refuse_with_reformulation without ever calling the LLM.

Pure Python: no external calls. Wave 5 adds a Langfuse span around this node.
"""
from __future__ import annotations

import re

from agent.policies import GATE1_THRESHOLD
from agent.state import GraphState
from app.observability.trace_decorators import attach_gate1_metadata_to_span

# ---------------------------------------------------------------------------
# Out-of-scope content screen (TRUST-04 / P1) — first-line deterministic guard.
#
# The reranker score CANNOT gate topical out-of-scope questions: a DRHP is filed
# PRE-listing, so "how did the stock perform on listing day" / "current market cap
# today" are unanswerable, yet they mention the company + peers and score HIGH
# (swiggy-012 = +1.23). The LLM sometimes answers them by grounding on the DRHP's
# peer discussion, and cite_check can't catch a plausibly-grounded off-topic answer.
# This screen refuses the clear post-listing / real-time class deterministically,
# BEFORE the LLM. It is a first-line heuristic, not a complete OOS solution — the
# general case still needs an answer-relevance judge (documented follow-up).
# Patterns are conservative: 0 false positives across the full numeric gold set +
# swiggy-001..011 (verified 2026-07-25). "expected listing date" / "how did revenue
# perform" / "proposed to be listed" deliberately do NOT match.
# ---------------------------------------------------------------------------

_OUT_OF_SCOPE_PATTERNS = (
    r"listing[\s\-]?day",
    r"\bpost[\s\-]?listing\b",
    r"\blisting\s+(gain|gains|pop|performance|price)\b",
    r"\b(after|since|upon|on)\s+(its\s+|the\s+)?listing\b",
    r"\bcurrent(ly)?\b.{0,30}\b(price|market\s?cap|capitali|valuation|worth|trading|share\s?price)\b",
    r"\bmarket\s?cap(itali[sz]ation)?\b.{0,20}\b(today|now|current)\b",
    r"\b(today|right now|as of today|latest)\b.{0,30}\b(price|market\s?cap|valuation|worth|trading|share\s?price)\b",
    r"\bcompare[d]?\s+(to|with)\b.{0,40}\blisting\b",
    r"\bhow\s+did\b.{0,40}\b(share\s?price|stock|list)\b",
    r"\btrading\s+(at|now)\b",
)
_OUT_OF_SCOPE_RE = re.compile("|".join(_OUT_OF_SCOPE_PATTERNS), re.IGNORECASE)


def is_out_of_scope(question: str) -> bool:
    """True for clearly post-listing / real-time questions a pre-listing DRHP cannot answer."""
    return bool(_OUT_OF_SCOPE_RE.search(question or ""))


def run(state: GraphState) -> GraphState:
    """Compute max reranker score and set gate1_passed.

    state["gate1_max_score"] is stored for Langfuse trace consumers (Wave 5)
    and for threshold calibration against the gold eval set (Wave 5).

    Args:
        state: GraphState with state["reranked_top_k"] populated by rerank node.

    Returns:
        Updated GraphState with:
          - gate1_max_score: float — the highest reranker score seen
          - gate1_passed: bool — True iff max_score >= GATE1_THRESHOLD
    """
    reranked = state.get("reranked_top_k", [])

    # Empty / scoreless retrieval must ALWAYS refuse, independent of the threshold
    # (float(-inf) < any finite GATE1_THRESHOLD). This is what makes it safe to
    # lower the threshold to admit relevant-but-negative reranker logits.
    if not reranked:
        max_score = float("-inf")
    else:
        max_score = max(c.get("rerank_score", float("-inf")) for c in reranked)

    # Content-level out-of-scope screen (TRUST-04): the reranker score can't gate a
    # topical post-listing / real-time question (it scores high), so refuse it here
    # regardless of score. Refusal then flows through the existing gate1 refusal path.
    out_of_scope = is_out_of_scope(state.get("question", ""))
    gate1_passed = (max_score >= GATE1_THRESHOLD) and not out_of_scope

    # Attach Gate 1 metadata to Langfuse span (no-op when disabled).
    attach_gate1_metadata_to_span(max_score, GATE1_THRESHOLD, gate1_passed)

    return {
        **state,
        "gate1_max_score": max_score,
        "gate1_passed": gate1_passed,
    }
