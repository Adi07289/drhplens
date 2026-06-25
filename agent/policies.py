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

GATE1_THRESHOLD: float = 0.0  # Calibrated value pending: run scripts/calibrate_gate1.py against tests/eval/gold_set.jsonl (n=13), then update this line with recommended value + inline comment per RESEARCH Open Question 1 procedure
"""
Reranker score threshold. Wave 5 default: 0.0 (any positive reranker score passes).
Run `python scripts/calibrate_gate1.py` to sweep -2.0..+2.0 and obtain the
calibrated value. Update this constant with the recommended value + inline comment.
Example: GATE1_THRESHOLD: float = -0.5  # Calibrated 2026-05-28 against gold_set.jsonl (n=13), correct=11/13
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

# ---------------------------------------------------------------------------
# Phase 3 — Structured signal extraction (red-flag table) tunables
#
# Single-source-of-truth constants for Phase 3. Every value below is a control
# surface to be CALIBRATED EMPIRICALLY; the calibration procedure is documented
# in eval/gold/extraction_rubric.md (created in the gold-set plan). Each carries
# a calibration comment mirroring the GATE1_THRESHOLD posture above.
# ---------------------------------------------------------------------------

NUMERIC_GROUNDING_REL_TOLERANCE: float = 0.01  # Calibrate empirically; procedure documented in eval/gold/extraction_rubric.md
"""
Relative tolerance for the per-number source-grounding reconciliation (D3-10).
A claimed number grounds against a cited-span number when
abs(claim - window) / window <= this tolerance, AFTER lakh (×1e5) / crore
(×1e7) / million (×1e6) unit normalization — so "₹11,247 crore" reconciles with
"1,12,470 lakh" instead of false-failing the exact-string subset check.
Default 0.01 (1%) absorbs disclosed-rounding noise. Calibrate against the
numeric-faithfulness eval set; document the chosen value in extraction_rubric.md.
"""

IDF_BAND_THRESHOLDS: tuple[float, float] = (2.0, 4.0)  # Calibrate empirically; procedure documented in eval/gold/extraction_rubric.md
"""
The two in-corpus IDF cutpoints that map a risk's specificity score to a band
(D3-14). With (low, high): score < low -> "industry_standard"; low <= score <
high -> "mostly_issuer_specific"; score >= high -> "issuer_specific". Defaults
are placeholders over a small n≈8 corpus (documented as small, D3-14); calibrate
once the catalogue grows and record in extraction_rubric.md.
"""

F1_NUMERIC_TOLERANCES: dict[str, float] = {  # Calibrate empirically; procedure documented in eval/gold/extraction_rubric.md
    "rpt_pct": 0.5,
    "ofs_vs_fresh": 0.5,
    "promoter_pledge_pct": 0.5,
    "debt_trajectory": 0.5,
}
"""
Per-numeric-field ABSOLUTE tolerances for the extraction F1 scorer (D3-07): a
predicted numeric value matches the gold value when abs(pred - gold) <= the
field's tolerance. Covers the four numeric red-flag fields (rpt_pct,
ofs_vs_fresh, promoter_pledge_pct, debt_trajectory); boolean (going_concern) and
set fields (customer_concentration, auditor_history) use exact / set-overlap
rules instead. Defaults are ± percentage-point placeholders; calibrate per field
against the gold set and document in extraction_rubric.md.
"""

IDF_BOILERPLATE_FUZZ_THRESHOLD: int = 85  # Calibrate empirically; procedure documented in eval/gold/extraction_rubric.md
"""
rapidfuzz token_set_ratio floor for the deterministic boilerplate clamp (D3-14).
A normalized risk statement scoring >= this against any phrase in
eval/gold/boilerplate_phrases.txt is clamped to the bottom specificity band,
regardless of its IDF score. Default 85 mirrors the existing fuzzy-match posture
(CITE_CHECK_TOKEN_RATIO=80); calibrate against the boilerplate floor list and
document in extraction_rubric.md.
"""

NUMERIC_FAITHFULNESS_GATE: float = 0.95  # Calibrate empirically; procedure documented in eval/gold/extraction_rubric.md
"""
The numeric-faithfulness RELEASE GATE (D3-12). numeric_faithfulness =
fraction of eval questions whose every emitted number grounds to a cited DRHP
span (per-number source-grounding, D3-10). The pre-deploy gate
(scripts/release_gate.py) writes a report and exits non-zero when the measured
faithfulness is < this threshold — enforcement over discipline. Locked at 0.95
per the ROADMAP cross-phase invariant; this is the threshold, not a tunable to
relax. The calibration note refers to the eval-set construction procedure.
"""
