"""
agent/policies.py — Single source of truth for all tunable constants.

These constants are the control surface for Wave 5 calibration. Editing one value
here propagates to every node that imports it — no node hard-codes a threshold.

Locked values per RESEARCH Open Questions 1, 4, 5 + D-09 + Pattern 3:
  GATE1_THRESHOLD = 0.0          # Open Question 1: reranker positive → pass; calibrate in Wave 5
  MAX_REGENERATE_ATTEMPTS = 1    # D-09: hard-block-and-regenerate; one retry then refuse
  MAX_SUB_QUESTIONS = 4          # Open Question 4: decompose caps at 4 sub-questions
  CITE_CHECK_TOKEN_RATIO = 80    # Pattern 3: fuzzy-match threshold
  RELAXED_SEARCH_LIMIT = 20      # Open Question 5: reformulation search window
  RELAXED_SEARCH_TOP_SECTIONS = 2  # Open Question 5: top-2 unique section chips
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Phase 1 single-IPO scope
# ---------------------------------------------------------------------------

DRHP_ID_DEFAULT: str = "swiggy_2024_11"
"""Phase 1 single-IPO default. Phase 2 introduces dynamic DRHP selection."""

# ---------------------------------------------------------------------------
# Retrieval constants
# ---------------------------------------------------------------------------

RETRIEVE_LIMIT: int = 50
"""Initial dense-retrieval result count fed to the reranker."""

RERANK_TOP_K: int = 5
"""Top-K reranked chunks passed as context to the LLM generate node."""

# ---------------------------------------------------------------------------
# Gate 1 — pre-LLM retrieval score floor (D-05)
# ---------------------------------------------------------------------------

GATE1_THRESHOLD: float = 0.0
"""
Reranker score threshold. Open Question 1: starts at 0.0 so any positive
reranker score passes Gate 1. Wave 5 calibrates against the gold eval set.
"""

# ---------------------------------------------------------------------------
# Scrub / regenerate budget (D-09)
# ---------------------------------------------------------------------------

MAX_REGENERATE_ATTEMPTS: int = 1
"""
Maximum number of generate-node invocations before the scrubber refuses.
D-09 hard-block-and-regenerate: first hit increments attempts to 1 (retry);
second hit increments to 2, which exceeds this limit → refuse.
"""

# ---------------------------------------------------------------------------
# Decompose node (Open Question 4)
# ---------------------------------------------------------------------------

MAX_SUB_QUESTIONS: int = 4
"""Upper bound on sub-questions from the decompose node. Instructor enforces
this via the SubQuestions.questions Field(max_length=4) constraint."""

# ---------------------------------------------------------------------------
# Cite-check algorithm (RESEARCH Pattern 3)
# ---------------------------------------------------------------------------

CITE_CHECK_TOKEN_RATIO: int = 80
"""
token_set_ratio threshold for the deterministic cite-check. A claim's text must
achieve >= 80% fuzzy-token overlap with the cited chunk window to be grounded.
"""

CITE_CHECK_SPAN_TOLERANCE_CHARS: int = 50
"""
Window extension (±50 chars) applied around span_offsets when building the
cite-check text window. Allows for minor off-by-one span alignment.
"""

# ---------------------------------------------------------------------------
# Refuse-with-reformulation (Open Question 5)
# ---------------------------------------------------------------------------

RELAXED_SEARCH_LIMIT: int = 20
"""
Qdrant search limit for the relaxed (no score threshold) reformulation query.
Returns more candidates so the dedup step has enough unique sections.
"""

RELAXED_SEARCH_TOP_SECTIONS: int = 2
"""
Number of unique section names to surface as reformulation chip suggestions.
Bounded to 2 per Open Question 5 (UI-SPEC chip cap is 3; we emit at most 2).
"""
