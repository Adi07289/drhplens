"""
pipelines/confidence.py — Deterministic source-grounding confidence rubric (D3-01).

A pure, LLM-free classifier that anchors a field's confidence tier to the already-
computed cite-check primitives and the claim's verbatim span. NO LLM call, NO Qdrant
call, no side effects — confidence becomes a *measured* signal, not a model self-report.

Rubric (evaluated in priority order, per D3-01):
  - high   : the emitted value appears VERBATIM (after cite_check._normalize) inside
             a cited claim.verbatim_span — the value is stated outright in the DRHP.
  - medium : the emitted value's numbers RECONCILE with source numbers (a light
             parse / transformation / aggregation — e.g. an RPT % derived from two
             figures) but are NOT a verbatim substring of any cited span.
  - low    : support spans >= 2 cited sources with DIFFERENT .section values
             (a cross-section inference, the weakest grounding).
  - default: when none of the above fire (e.g. a single-section non-numeric claim
             that is not a verbatim substring), fall back to medium — the value is
             grounded (cite_check already passed upstream) but not stated verbatim.

Score mapping (D3-02): tier -> a policy-anchored representative score
(high=0.90 / medium=0.70 / low=0.50). The score is surfaced ONLY in the methodology
pane on expand — never in the up-front red-flag row. The mapping is intentionally a
small fixed lookup rather than a derived `token_set_ratio`, so the same tier always
reports the same defensible score across fields and IPOs.

Single normalization path: this module imports `_normalize`, `_extract_numbers`, and
`_extract_scaled_numbers` from `agent.nodes.cite_check` and does NOT re-implement any
normalization (consistency-is-correctness — one path across cite-check / eval / IDF /
confidence).
"""
from __future__ import annotations

from typing import Literal

from agent.nodes.cite_check import (
    _extract_numbers,
    _extract_scaled_numbers,
    _normalize,
    _number_reconciles,
)
from agent.schemas import GroundedAnswer, RefusalResponse

ConfidenceTier = Literal["high", "medium", "low"]

# Tier -> representative methodology-pane score (D3-02). Policy-anchored constants;
# documented here as the single mapping (mirrors the cite-check ratio posture).
_TIER_SCORES: dict[ConfidenceTier, float] = {
    "high": 0.90,
    "medium": 0.70,
    "low": 0.50,
}


def _value_is_verbatim(ga: GroundedAnswer) -> bool:
    """True iff a claim's emitted VALUE appears verbatim in a cited span.

    "Verbatim" is checked after `_normalize` so casing / whitespace / unicode
    variants of the same value count as verbatim (D3-01 high tier). For a numeric
    claim the emitted value is its number token(s) — each extracted number string
    (via the shared `_extract_numbers` path) must appear in the normalized span.
    For a non-numeric claim, the whole normalized claim text must be a substring.
    """
    for claim in ga.claims:
        claim_norm = _normalize(claim.text)
        if not claim_norm:
            continue
        claim_numbers = _extract_numbers(claim_norm)
        for src in claim.sources:
            span = src.verbatim_span or claim.verbatim_span
            if not span:
                continue
            span_norm = _normalize(span)
            span_numbers = _extract_numbers(span_norm)
            if claim_numbers:
                # Numeric claim: every emitted number must be present verbatim
                # (same digit string, comma-stripped) in the cited span.
                if claim_numbers.issubset(span_numbers):
                    return True
            elif claim_norm in span_norm:
                return True
    return False


def _value_reconciles_with_sources(ga: GroundedAnswer) -> bool:
    """True iff some claim number reconciles with a cited-span number (light parse).

    Reuses the cite_check unit-aware magnitude extractor + tolerance reconciler so a
    transformation/aggregation (a value derived from source figures) is recognised
    as grounded-by-parse without being a verbatim substring.
    """
    for claim in ga.claims:
        claim_mags = _extract_scaled_numbers(_normalize(claim.text))
        if not claim_mags:
            continue
        for src in claim.sources:
            span = src.verbatim_span or claim.verbatim_span
            if not span:
                continue
            window_mags = _extract_scaled_numbers(_normalize(span))
            if any(
                _number_reconciles(c, w) for c in claim_mags for w in window_mags
            ):
                return True
    return False


def _spans_multiple_sections(ga: GroundedAnswer) -> bool:
    """True iff the answer's cited sources cover >= 2 distinct .section values."""
    sections = {
        src.section for claim in ga.claims for src in claim.sources if src.section
    }
    return len(sections) >= 2


def classify_confidence(ga: GroundedAnswer) -> tuple[ConfidenceTier, float]:
    """Deterministically classify a GroundedAnswer's confidence (tier, score).

    Pure + LLM-free. Priority order: verbatim -> high; else numeric-reconcile ->
    medium; else cross-section (>=2 distinct sections) -> low; else medium default
    (grounded upstream but neither verbatim nor cross-section).

    Returns:
        (tier, score) where score is the policy-anchored representative score for
        the tier (surfaced only in the methodology pane, D3-02).
    """
    if _value_is_verbatim(ga):
        tier: ConfidenceTier = "high"
    elif _value_reconciles_with_sources(ga):
        tier = "medium"
    elif _spans_multiple_sections(ga):
        tier = "low"
    else:
        tier = "medium"
    return tier, _TIER_SCORES[tier]


def confidence_for_field(
    field: GroundedAnswer | RefusalResponse,
) -> tuple[ConfidenceTier | None, float | None]:
    """Field-level wrapper for the precompute loop (one call per red-flag field).

    A `RefusalResponse` (not-disclosed field) carries NO confidence tier and NO
    score — absence is an honest signal, never conflated with low-confidence
    extraction (D3-03). A `GroundedAnswer` is delegated to `classify_confidence`.
    """
    if isinstance(field, RefusalResponse):
        return None, None
    return classify_confidence(field)
