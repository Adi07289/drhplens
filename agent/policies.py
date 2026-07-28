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

GATE1_THRESHOLD: float = -3.0  # Calibrated 2026-07-24 (EVAL-03). The bge-reranker-v2 cross-encoder emits NEGATIVE logits for genuinely-relevant DRHP passages (answerable DRHP questions measured at -0.5 to -2.54; worst answerable num-033 = -2.54), so the old 0.0 refused answerable questions BEFORE the LLM. Meanwhile topical-out-of-scope questions score HIGHER (Zomato-listing +1.23, market-cap +2.81), so the reranker score CANNOT separate in-scope from out-of-scope — refusal is (and must be) done by the LLM + cite_check downstream, not gate1. Gate1 now only screens genuine garbage retrieval (e.g. an unrelated "weather" query scored -8.8). -3.0 sits below the worst answerable (-2.54) and above garbage.
"""
Reranker score threshold — a pre-LLM screen for GARBAGE retrieval only, not the
refusal antibody. The bge-reranker cross-encoder returns unbounded logits (often
negative for relevant passages), and topical out-of-scope questions can outscore
answerable ones, so out-of-scope refusal is handled by the LLM ("this DRHP does not
address X") + the deterministic cite_check, never by this score. Empty/scoreless
retrieval refuses unconditionally (gate1_check uses -inf). Re-run
`scripts/calibrate_gate1.py` if the reranker model or corpus changes.
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

# Gemini generation models, tried in order (primary first). gemini-3.5-flash grounds
# more faithfully but intermittently 503s under load; gemini-3.1-flash-lite is reliably
# available. The LLM nodes fall through this list so a 503 degrades to a working model
# instead of a refusal.
GEMINI_MODELS: tuple[str, ...] = ("gemini-3.5-flash", "gemini-3.1-flash-lite")

CITE_CHECK_TOKEN_RATIO: int = 52  # Calibrated via scripts/calibrate_cite_check.py: on a labeled grounded/hallucinated set the classes separate cleanly (grounded 60-78, hallucinated 35-46); 52 is the gap midpoint — max grounded recall while staying above every hallucination. Was 80, which rejected even gemini-3.5-flash's legitimately-grounded paraphrases.
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

CITATION_ACCURACY_GATE: float = 0.95
"""
The citation-accuracy RELEASE GATE (EVAL-01 / 06.1-05). citation_accuracy =
the fraction of cited pages/spans that genuinely contain the stated claim
("did the cited page actually contain the claim") — the project's custom,
deterministic (non-LLM) retrieval-attribution metric. A regression below this
threshold is a HARD CI FAILURE per the CLAUDE.md project rule ("Treat
regression in citation accuracy as a hard CI failure"); the pre-deploy gate
(scripts/release_gate.py) reads the committed eval_summary.json and exits
non-zero when citation_accuracy < this threshold. Locked at 0.95
(literature-backed for high-stakes financial RAG) — enforced, not a tunable to
relax.
"""

RECALL_AT_10_GATE: float = 0.85
"""
The recall@10 RELEASE GATE (EVAL-01 / 06.1-05) — a labelled REGRESSION FLOOR,
never a headline quality metric (P10). recall@10 = the fraction of gold
questions whose expected page-span(s) appear within the top-10 retrieved
candidates (deterministic span-overlap, computed over the 50 Qdrant candidates,
not the rerank-capped top-5). This 0.85 floor is ratified against spike 003's
measured 1.00 baseline (measured decision #4 / .planning/spikes/003-recall-baseline):
it is SATURATED at 1.00 because the current gold set's expected_sources are
coarse section-level page ranges (mean 44.5 pages), so it is a low-signal
regression tripwire set just below real performance — never self-blocking, never
trivially low, and NEVER advertised as a quality win. The pre-deploy gate exits
non-zero when recall@10 < this threshold — enforced, not a tunable to relax.
"""
