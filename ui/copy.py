"""
DRHPLens user-visible copy strings.

Every string constant in this module is scrubber-checked at import time
(TRUST-03 anchor). If any constant contains a banned token, this module
raises AssertionError at import time — before any HTTP request is served.

This makes it impossible for a copy edit that introduces a banned token to
reach production silently. It is a feature, not a bug.

All strings sourced verbatim from 01-UI-SPEC.md §Copywriting Contract.
Do NOT paraphrase — the legal-review precedent for Phase 6 depends on copy
stability from Phase 1.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

HERO_HEADING: str = "Ask DRHPLens about Swiggy."
"""Home page hero heading (Display 28px). Single sentence, no exclamation.

DEPRECATED naming (kept for Phase 1 test/back-compat — see
test_copy_no_banned_tokens.py spot-check): this is now just the Swiggy-filled
form of HERO_HEADING_TEMPLATE. Phase 2 snapshot pages use
HERO_HEADING_TEMPLATE.format(issuer=...) directly (FLAG-COPY-TEMPLATING).
"""

HERO_HEADING_TEMPLATE: str = "Ask DRHPLens about {issuer}."
"""Issuer-parameterized hero heading. .format(issuer=...) per snapshot page."""

HERO_SUBHEADING: str = (
    "One Indian IPO. One prospectus. Ask anything. "
    "Every answer cites the page it came from."
)
"""Issuer-agnostic; reused verbatim on every snapshot page (no templating needed)."""

# ---------------------------------------------------------------------------
# Question input
# ---------------------------------------------------------------------------

QUESTION_PLACEHOLDER: str = (
    "Ask about Swiggy's risk factors, financials, promoter holdings, "
    "or use of proceeds…"
)
"""DEPRECATED naming (kept for Phase 1 back-compat) — Swiggy-filled form of
QUESTION_PLACEHOLDER_TEMPLATE. Phase 2 snapshot pages use the template directly."""

QUESTION_PLACEHOLDER_TEMPLATE: str = (
    "Ask about {issuer}'s risk factors, financials, promoter holdings, "
    "or use of proceeds…"
)
"""Issuer-parameterized question placeholder. .format(issuer=...) per snapshot page."""

# ---------------------------------------------------------------------------
# Modal
# ---------------------------------------------------------------------------

MODAL_CTA: str = "I understand — open DRHPLens"
"""Primary CTA in the first-use disclaimer modal."""

# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

EMPTY_STATE_HEADING: str = "Nothing asked yet."

EMPTY_STATE_BODY: str = (
    'Try one of these to start: '
    '"What does Swiggy say about its path to profitability?" · '
    '"Who are the promoters and what is their post-issue holding?" · '
    '"What is the use of proceeds breakdown?"'
)
"""DEPRECATED naming (kept for Phase 1 back-compat) — Swiggy-filled form of
EMPTY_STATE_BODY_TEMPLATE."""

EMPTY_STATE_BODY_TEMPLATE: str = (
    'Try one of these to start: '
    '"What does {issuer} say about its path to profitability?" · '
    '"Who are the promoters and what is their post-issue holding?" · '
    '"What is the use of proceeds breakdown?"'
)
"""Issuer-parameterized empty-state body. .format(issuer=...) per snapshot page."""

# ---------------------------------------------------------------------------
# Loading states
# ---------------------------------------------------------------------------

COLD_START_COPY: str = (
    "Warming up. The Hugging Face Space was asleep "
    "— first load takes 30–60 seconds while the index loads. "
    "Subsequent questions will be fast."
)

LOADING_ANSWER_COPY: str = (
    "Reading Swiggy's DRHP and checking every claim against the source…"
)
"""DEPRECATED naming (kept for Phase 1 back-compat) — Swiggy-filled form of
LOADING_ANSWER_COPY_TEMPLATE."""

LOADING_ANSWER_COPY_TEMPLATE: str = (
    "Reading {issuer}'s DRHP and checking every claim against the source…"
)
"""Issuer-parameterized loading copy. .format(issuer=...) per snapshot page."""

# ---------------------------------------------------------------------------
# Refusal states
# ---------------------------------------------------------------------------

REFUSAL_NO_GROUNDING_TEMPLATE: str = (
    "This DRHP does not address {topic}. "
    "Try asking about {suggestion1} or {suggestion2} "
    "— the prospectus does cover those."
)
"""Use .format(topic=..., suggestion1=..., suggestion2=...) to interpolate."""

REFUSAL_PARTIAL_GROUNDING_TEMPLATE: str = (
    "The DRHP addresses parts of your question. "
    "{grounded_answer}. "
    "It does not address {missing_part} — consider asking that separately."
)
"""Use .format(grounded_answer=..., missing_part=...) to interpolate."""

REFUSAL_BANNED_TOKEN_COPY: str = (
    "Couldn't return that answer because it would have implied investment advice. "
    "DRHPLens describes; it doesn't advise. "
    "Try a more specific question about what the DRHP says."
)

# ---------------------------------------------------------------------------
# Error states
# ---------------------------------------------------------------------------

ERROR_QDRANT_UNREACHABLE: str = (
    "The DRHP index is temporarily unreachable. "
    "This is a free-tier infrastructure hiccup, not a problem with your question. "
    "Try again in a minute."
)

ERROR_LLM_TIMEOUT: str = (
    "The reading step timed out. "
    "Try the same question again — it usually goes through on retry."
)

ERROR_RATE_LIMIT: str = (
    "DRHPLens has hit today's free-tier reading limit. "
    "Come back tomorrow, or check the methodology page for what the project covers."
)

# ---------------------------------------------------------------------------
# Per-answer disclaimer
# ---------------------------------------------------------------------------

PER_ANSWER_DISCLAIMER: str = "Informational only — not advice."

# ---------------------------------------------------------------------------
# Methodology stub
# ---------------------------------------------------------------------------

METHODOLOGY_STUB_HEADING: str = "Methodology"

METHODOLOGY_STUB_BODY: str = (
    "DRHPLens is a portfolio project for an Indian-IPO DRHP decoder. "
    "Phase 1 ships cited Q&A over one hand-loaded prospectus (Swiggy, Nov 2024). "
    "The full methodology — model card, eval dashboards, failure gallery "
    "— lands in Phase 6. "
    "For now: see the public repository for source code, the roadmap, "
    "and the design decisions behind every page."
)

# ---------------------------------------------------------------------------
# Phase 2 — Catalogue page copy (02-UI-SPEC.md §Copywriting Contract)
# ---------------------------------------------------------------------------

CATALOGUE_HERO_HEADING: str = "Indian IPOs, read honestly."

CATALOGUE_HERO_SUBHEADING: str = (
    "Browse recent mainboard IPOs. Open any one to see what its prospectus "
    "actually says — every field cites the page it came from."
)

CATALOGUE_CARD_OPEN_NOW_TAG: str = "Open now"
"""Small, text-only tag for currently-open IPOs — NO color, NO badge fill."""

CATALOGUE_CARD_ARIA_LABEL_TEMPLATE: str = (
    "{issuer}, {sector}, listed {date}, issue size {size}. Open snapshot."
)
"""Card screen-reader label. .format(issuer=..., sector=..., date=..., size=...)."""

CATALOGUE_EMPTY_HEADING: str = "No IPOs loaded yet."

CATALOGUE_EMPTY_BODY: str = (
    "The catalogue is still being ingested. Check back shortly, or read the "
    "methodology page for what's covered."
)

# ---------------------------------------------------------------------------
# Phase 2 — Snapshot page copy (02-UI-SPEC.md §Copywriting Contract)
# ---------------------------------------------------------------------------

SNAPSHOT_BREADCRUMB_BACK: str = "← All IPOs"

SNAPSHOT_BLOCK_HEADING_BUSINESS: str = "Business"
SNAPSHOT_BLOCK_HEADING_FINANCIALS: str = "Key Financials"
SNAPSHOT_BLOCK_HEADING_RISKS: str = "Risk Factors"
SNAPSHOT_BLOCK_HEADING_USE_OF_PROCEEDS: str = "Use of Proceeds"
SNAPSHOT_BLOCK_HEADING_PROMOTER: str = "Promoters & Management"

SPLIT_BAR_CAPTION_TEMPLATE: str = (
    "Of the total issue, {fresh_pct}% is a fresh issue (money to the company) "
    "and {ofs_pct}% is an Offer for Sale (shares offered by existing shareholders)."
)
"""Split-bar caption. .format(fresh_pct=..., ofs_pct=...)."""

SPLIT_BAR_PURE_FRESH: str = "Fresh 100% · No OFS"
SPLIT_BAR_PURE_OFS: str = "OFS 100% · No fresh capital raised"

RISK_COUNTER_TEMPLATE: str = "Risk {n} of {m}"
"""Descriptive, not evaluative. .format(n=..., m=...)."""

FIELD_NOT_DISCLOSED_NOTE: str = "Not disclosed in this DRHP."
"""P2-L8 honesty note — rendered instead of a fabricated value or a guess."""

FINANCIALS_MISSING_CELL: str = "—"
"""Em dash for a missing financials cell; pair with aria-label='Not disclosed in this DRHP'."""

SNAPSHOT_PRECOMPUTING_HEADING: str = "This snapshot is still being prepared."

SNAPSHOT_PRECOMPUTING_BODY_TEMPLATE: str = (
    "We're reading {issuer}'s DRHP and checking every field against the source. "
    "This IPO will be ready shortly — you can still ask questions below."
)
"""Issuer-parameterized precomputing-state body. .format(issuer=...)."""

SNAPSHOT_CACHE_UNREACHABLE: str = (
    "This IPO's snapshot is temporarily unreachable. This is a free-tier "
    "infrastructure hiccup, not a problem with the IPO. Try again in a minute."
)

UNKNOWN_DRHP_ID_COPY: str = "That IPO isn't in the catalogue."

# ---------------------------------------------------------------------------
# Phase 3 — Red-flag signal table copy (03-UI-SPEC.md §Copywriting Contract)
# Every string VERBATIM from the UI-SPEC Copywriting Contract (L3-8). Do NOT
# paraphrase — scrubber-clean copy stability is load-bearing. No banned token
# (subscribe / avoid / buy / sell / target / recommend / fair value /
# overvalued / undervalued / target price) appears anywhere below.
# ---------------------------------------------------------------------------

REDFLAG_BLOCK_HEADING: str = "Red-flag signals"

REDFLAG_BLOCK_SUBLINE: str = (
    "Structured signals extracted from the prospectus. Each value cites the "
    "DRHP page it came from and shows how confident the extractor is."
)

# The 7 field labels in canonical order (UI-SPEC R-1 fixed order; 600 semibold).
REDFLAG_FIELD_LABEL_RPT_PCT: str = "RPT % of revenue"
REDFLAG_FIELD_LABEL_OFS_VS_FRESH: str = "OFS vs fresh issue"
REDFLAG_FIELD_LABEL_PROMOTER_PLEDGE_PCT: str = "Promoter pledge %"
REDFLAG_FIELD_LABEL_CUSTOMER_CONCENTRATION: str = "Customer concentration"
REDFLAG_FIELD_LABEL_AUDITOR_HISTORY: str = "Auditor history"
REDFLAG_FIELD_LABEL_DEBT_TRAJECTORY: str = "Debt trajectory"
REDFLAG_FIELD_LABEL_GOING_CONCERN: str = "Going-concern mentions"

# field_key -> display label (canonical order); keys match REDFLAG_FIELD_KEYS.
REDFLAG_FIELD_LABELS: dict[str, str] = {
    "rpt_pct": REDFLAG_FIELD_LABEL_RPT_PCT,
    "ofs_vs_fresh": REDFLAG_FIELD_LABEL_OFS_VS_FRESH,
    "promoter_pledge_pct": REDFLAG_FIELD_LABEL_PROMOTER_PLEDGE_PCT,
    "customer_concentration": REDFLAG_FIELD_LABEL_CUSTOMER_CONCENTRATION,
    "auditor_history": REDFLAG_FIELD_LABEL_AUDITOR_HISTORY,
    "debt_trajectory": REDFLAG_FIELD_LABEL_DEBT_TRAJECTORY,
    "going_concern": REDFLAG_FIELD_LABEL_GOING_CONCERN,
}

CONFIDENCE_LABEL_TEMPLATE: str = "Confidence: {confidence_tier}"
"""Per-field confidence label (Small 12 muted, text only — no pill, no color,
L3-2). .format(confidence_tier='high'|'medium'|'low')."""

CONFIDENCE_RUBRIC_LINE: str = (
    "Confidence reflects how directly the value is stated in the DRHP — "
    "high: stated verbatim in the cited span; medium: stated but needed light "
    "parsing or aggregation; low: inferred across sections."
)

FIELD_NUMERIC_GATE_BLOCKED: str = (
    "Could not ground this number to a cited DRHP page, so it is not shown."
)
"""L3-9 blocked-copy — rendered instead of an unsourced number when the
cite_check numeric sub-check fails."""

# ---------------------------------------------------------------------------
# Phase 3 — IDF-ranked risk list copy (03-UI-SPEC.md §Copywriting Contract)
# ---------------------------------------------------------------------------

RISK_BLOCK_HEADING: str = "Risk factors, ranked by how specific they are"

RISK_BLOCK_SUBLINE: str = (
    "Risks unique to this company are listed first; risks that appear in most "
    "prospectuses are listed lower. Order is the signal — not severity."
)

RISK_SPECIFICITY_COUNTER_TEMPLATE: str = "Risk {n} of {m} · {specificity}"
"""Rank + specificity counter (Small 12 muted). .format(n=.., m=.., specificity=..)
where specificity ∈ the three SPECIFICITY_WORD_* values."""

SPECIFICITY_WORD_ISSUER_SPECIFIC: str = "Issuer-specific"
SPECIFICITY_WORD_MOSTLY_ISSUER_SPECIFIC: str = "Mostly issuer-specific"
SPECIFICITY_WORD_INDUSTRY_STANDARD: str = "Industry-standard"

# specificity_band enum (RankedRisk.specificity_band) -> display word.
SPECIFICITY_BAND_WORDS: dict[str, str] = {
    "issuer_specific": SPECIFICITY_WORD_ISSUER_SPECIFIC,
    "mostly_issuer_specific": SPECIFICITY_WORD_MOSTLY_ISSUER_SPECIFIC,
    "industry_standard": SPECIFICITY_WORD_INDUSTRY_STANDARD,
}

SPEC_METER_ARIA_TEMPLATE: str = (
    "Issuer-specificity: {pct} percent. Higher means more specific to this company."
)
"""Specificity-meter aria-label. .format(pct=..)."""

# ---------------------------------------------------------------------------
# Phase 3 — Methodology pane ("Show your work") copy (03-UI-SPEC.md)
# ---------------------------------------------------------------------------

METHODOLOGY_TRIGGER: str = "Show your work"
"""Methodology-pane expander header (Primary CTA — the one explicit affordance
Phase 3 adds). Neutral verb phrase, no emoji, no icon."""

METHODOLOGY_PANE_LABEL_QUERY: str = "Retrieval query"
METHODOLOGY_PANE_LABEL_CHUNKS: str = "Retrieved chunks (with scores)"
METHODOLOGY_PANE_LABEL_PROMPT: str = "Prompt used"
METHODOLOGY_PANE_LABEL_SOURCES: str = "Sources cited"
METHODOLOGY_PANE_LABEL_EVAL: str = "Eval scores (from the latest committed report)"

METHODOLOGY_EVAL_PROVENANCE_NOTE: str = (
    "These scores come from the most recent committed evaluation report, not a "
    "fresh check run when you expanded this. See the methodology page for the "
    "full eval."
)

METHODOLOGY_EVAL_NOT_AVAILABLE: str = (
    "No committed eval score yet for this field. The numeric-faithfulness gate "
    "still applies before this number is shown."
)

FIELD_NOT_DISCLOSED_IN_DRHP_NOTE: str = "Not disclosed in DRHP"
"""Phase 3 not-disclosed note (L3-3). Distinct verbatim string from the Phase 2
FIELD_NOT_DISCLOSED_NOTE ('Not disclosed in this DRHP.') per the UI-SPEC."""

# ---------------------------------------------------------------------------
# Phase 3 — Red-flag table empty / error states (03-UI-SPEC.md)
# ---------------------------------------------------------------------------

REDFLAG_EMPTY_HEADING: str = "No structured signals extracted yet."

REDFLAG_EMPTY_BODY: str = (
    "This IPO's red-flag table hasn't been computed. Try one of the IPOs "
    "already processed, or check back once ingestion completes."
)

REDFLAG_ERROR_STATE: str = (
    "The red-flag table couldn't load for this IPO. This is a free-tier "
    "infrastructure hiccup, not a problem with the prospectus. Try again in a "
    "minute."
)


# ---------------------------------------------------------------------------
# TRUST-03 anchor: import-time scrubber assertion.
# Any future copy edit that introduces a banned token will raise AssertionError
# here at import time, before any HTTP request is served.
# This is defense-in-depth: the scrubber already blocks LLM output; this
# ensures our OWN copy also passes.
#
# FLAG-COPY-TEMPLATING: format-string constants (containing "{") are scrubbed
# on a SAMPLE-SUBSTITUTED instance (issuer="Sample Issuer Limited", etc.) so
# the "no banned token, enforced at import" guarantee covers the templated
# forms too — not just the literal "{issuer}" placeholder text.
# ---------------------------------------------------------------------------
from compliance.scrubber import scrub as _scrub  # noqa: E402
import inspect as _inspect  # noqa: E402
import string as _string  # noqa: E402

_SAMPLE_FORMAT_VALUES = {
    "issuer": "Sample Issuer Limited",
    "topic": "sample topic",
    "suggestion1": "sample suggestion one",
    "suggestion2": "sample suggestion two",
    "fresh_pct": "59.0",
    "ofs_pct": "41.0",
    "n": "1",
    "m": "7",
    "sector": "Sample sector",
    "date": "Listed Nov 2024",
    "size": "₹1,000 cr",
    "grounded_answer": "sample grounded answer",
    "missing_part": "sample missing part",
    "specificity": "Issuer-specific",
    "pct": "62",
    "confidence_tier": "high",
}


def _scrub_sample_substituted(name: str, value: str) -> None:
    """Scrub a copy constant; if it is a format-string template, scrub the
    sample-substituted instance instead of the literal "{placeholder}" text."""
    try:
        fields = [f[1] for f in _string.Formatter().parse(value) if f[1]]
    except ValueError:
        fields = []
    sample_value = value
    if fields:
        try:
            sample_value = value.format(
                **{f: _SAMPLE_FORMAT_VALUES.get(f, "sample") for f in fields}
            )
        except (KeyError, IndexError):
            sample_value = value
    _r = _scrub(sample_value)
    if not _r.passed:
        raise AssertionError(
            f"ui/copy.py contains banned token in {name!r}: matched {_r.match!r} "
            f"(checked sample-substituted form: {sample_value!r})"
        )


_module = _inspect.getmodule(_inspect.currentframe())
for _name, _value in list(vars(_module).items()):
    if _name.startswith("_") or not isinstance(_value, str):
        continue
    _scrub_sample_substituted(_name, _value)
del _scrub, _inspect, _string, _module
