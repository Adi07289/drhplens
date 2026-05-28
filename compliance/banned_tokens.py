r"""
Banned-token list and compiled regex for DRHPLens compliance scrubber.

TRUST-02 / SEBI PITFALL 1 mitigation: prevents prescriptive investment-advice
language from appearing in any LLM-generated answer.

LOCKED LIST — Phase 1 v1:

UI-SPEC L-5 locked tokens (must not be extended or removed without
a phase-protocol discussion):
  subscribe, avoid, buy, sell, target, recommend, fair value,
  overvalued, undervalued, target price

Planner-discretion extensions (Open Question 2 — financial-advice synonyms
that carry the same regulatory risk as the locked set):
  accumulate   — common brokerage-note "action" word; same risk profile as "buy"
  outperform   — analyst rating vocabulary (Pitfall 1: SEBI RA boundary)
  underperform — analyst rating vocabulary (Pitfall 1: SEBI RA boundary)
  book profits — direct sell-instruction phrase in Indian retail finance discourse
  bullish      — directional market-sentiment word; prescriptive framing
  bearish      — directional market-sentiment word; prescriptive framing

REGEX DESIGN — morphological stems + \\w* suffix:

  The pattern uses TRUNCATED STEMS rather than full word forms, because many
  inflections are NOT formed by appending a suffix to the full word:
    - "subscribe" + "ing" = "subscribing" (correct) BUT
    - Python literal: "subscribe" does NOT appear in "subscribing"
      ("subscribing" = "subscrib" + "ing", dropping the silent 'e')

  Therefore we use STEMS that are common to all inflections:
    subscrib   → subscribe, subscribed, subscribing, subscriber, subscription
    accumulat  → accumulate, accumulated, accumulating, accumulation
    avoid      → avoid, avoided, avoiding (stem IS the full word here)
    recomm     → recommend, recommended, recommending, recommendation
      wait — "recommend" shares "recomm" but "recommendation" = recomm+endation
      Better stem: "recommend" itself because:
        recommend → recommend, recommended, recommending (all start with "recommend")
        recommendation → recommend + ation (Python: "recommend" IS in "recommendation")

  Actually for Python string matching: "recommend" IS a prefix of "recommendation"
  so recommend\w* would match "recommendation". The issue was only with "subscribing".

  TESTED STEMS (verified in Python 3.13):
    "subscri"    covers: subscribe, subscribed, subscribing, subscriber, subscription
    "avoid"      covers: avoid, avoided, avoiding
    "buy"        covers: buy, buying (but NOT "bought" — irregular past tense)
    "sell"       covers: sell, selling (but NOT "sold" — irregular past tense)
    "target"     covers: target, targeted, targeting
    "recommend"  covers: recommend, recommended, recommending, recommendation
    "accumulat"  covers: accumulate, accumulated, accumulating, accumulation
    "outperform" covers: outperform, outperformed, outperforming, outperforms
    "underperform" covers: underperform, underperformed, underperforming
    "bullish"    covers: bullish (only form in use)
    "bearish"    covers: bearish (only form in use)
    "overvalued" covers: overvalued (only form; "overvalue" + d)
    "undervalued" covers: undervalued (only form)

  "bought" and "sold" are NOT caught because they are irregular past tenses that
  do not share a stem with "buy"/"sell". In practice, "bought" in DRHP context
  means acquisition (legitimate), not a recommendation. We accept this trade-off
  and document it here. A future Phase N can add "bought" if monitoring shows
  evasion. (Rule 1 deviation from naive plan: necessary for correctness.)

  MULTI-WORD TOKENS use exact phrase matching without a \\w* suffix:
    "fair value", "target price", "book profits"
    "fair values" would NOT match the "fair value" phrase form — this is accepted
    because "fair value" as a valuation-opinion phrase is the regulated concern,
    not "fair values" as a plural noun (rare in this context).

  CASE INSENSITIVITY via re.IGNORECASE flag.
  UNICODE normalization via re.UNICODE flag.

  HOMOGLYPH ATTACK NOTE: we do NOT attempt to normalize unicode homoglyphs
  (e.g. cyrillic 's' in "ѕubscribe"). The attack surface is LLM output using
  standard Latin characters, not adversarial user input. Homoglyph defense is
  out of scope for Phase 1.
"""
from __future__ import annotations

import re

# -------------------------------------------------------------------------
# BANNED_TOKENS — the canonical display names (full words for documentation).
# The actual regex uses STEMS (defined in _STEM_MAP below).
# The tuple order is documentation-only; regex treats it as a set.
# -------------------------------------------------------------------------
BANNED_TOKENS: tuple[str, ...] = (
    # UI-SPEC L-5 locked tokens
    "subscribe",    # IPO subscription action
    "avoid",        # sell-equivalent advisory
    "buy",          # direct purchase recommendation
    "sell",         # direct sale recommendation
    "target",       # target price / target-price phrase anchor
    "recommend",    # analyst recommendation vocabulary
    "fair value",   # valuation-opinion phrase (multi-word)
    "overvalued",   # valuation-opinion word
    "undervalued",  # valuation-opinion word
    "target price", # explicit price-target phrase (multi-word)
    # Planner-discretion extensions (Open Question 2)
    "accumulate",   # brokerage "accumulate" rating
    "outperform",   # sell-side analyst rating
    "underperform", # sell-side analyst rating
    "book profits", # direct sell-instruction phrase (multi-word)
    "bullish",      # directional market-sentiment word
    "bearish",      # directional market-sentiment word
)

# -------------------------------------------------------------------------
# _STEMS — regex stems for morphological matching.
# Keyed to canonical token name.  For multi-word tokens, the value is a
# tuple of the full phrase (matched as phrase, not with stem).
# -------------------------------------------------------------------------
_SINGLE_WORD_STEMS: tuple[str, ...] = (
    "subscri",       # subscribe, subscribed, subscribing, subscriber, subscription
    "avoid",         # avoid, avoided, avoiding
    "buy",           # buy, buying (NB: "bought" NOT caught — irregular)
    "sell",          # sell, selling (NB: "sold" NOT caught — irregular)
    "target",        # target, targeted, targeting (also covers "target price" via phrase)
    "recommend",     # recommend, recommended, recommending, recommendation
    "overvalued",    # overvalued
    "undervalued",   # undervalued
    "accumulat",     # accumulate, accumulated, accumulating, accumulation
    "outperform",    # outperform, outperformed, outperforming, outperforms
    "underperform",  # underperform, underperformed, underperforming
    "bullish",       # bullish
    "bearish",       # bearish
)

_MULTI_WORD_PHRASES: tuple[str, ...] = (
    "fair value",    # valuation-opinion phrase
    "target price",  # explicit price-target phrase
    "book profits",  # direct sell-instruction
)


def _build_pattern() -> re.Pattern:  # type: ignore[type-arg]
    """Build the compiled banned-token regex.

    Pattern design:
      Multi-word phrases: \\b(phrase)\\b — exact match, no suffix
      Single-word stems:  \\b(stem)\\w*\\b — stem + any suffix for morphology

    Multi-word phrases come FIRST (longest-first) so alternation favors them
    over their single-word components (e.g. "target price" before "target").

    group(lastindex) in a match gives the canonical matched stem/phrase because
    \\w* is OUTSIDE the capturing group for single-word stems.
    """
    parts: list[str] = []

    # Multi-word phrases first (sorted longest-first for alternation priority)
    for phrase in sorted(_MULTI_WORD_PHRASES, key=len, reverse=True):
        escaped = re.escape(phrase)
        parts.append(r"\b(" + escaped + r")\b")

    # Single-word stems (sorted longest-first)
    for stem in sorted(_SINGLE_WORD_STEMS, key=len, reverse=True):
        escaped = re.escape(stem)
        parts.append(r"\b(" + escaped + r")\w*\b")

    pattern_str = "|".join(parts)
    return re.compile(pattern_str, re.IGNORECASE | re.UNICODE)


BANNED_TOKEN_PATTERN: re.Pattern = _build_pattern()  # type: ignore[type-arg]
