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
"""Home page hero heading (Display 28px). Single sentence, no exclamation."""

HERO_SUBHEADING: str = (
    "One Indian IPO. One prospectus. Ask anything. "
    "Every answer cites the page it came from."
)

# ---------------------------------------------------------------------------
# Question input
# ---------------------------------------------------------------------------

QUESTION_PLACEHOLDER: str = (
    "Ask about Swiggy's risk factors, financials, promoter holdings, "
    "or use of proceeds…"
)

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
# TRUST-03 anchor: import-time scrubber assertion.
# Any future copy edit that introduces a banned token will raise AssertionError
# here at import time, before any HTTP request is served.
# This is defense-in-depth: the scrubber already blocks LLM output; this
# ensures our OWN copy also passes.
# ---------------------------------------------------------------------------
from compliance.scrubber import scrub as _scrub  # noqa: E402
import inspect as _inspect  # noqa: E402

_module = _inspect.getmodule(_inspect.currentframe())
for _name, _value in list(vars(_module).items()):
    if _name.startswith("_") or not isinstance(_value, str):
        continue
    _r = _scrub(_value)
    if not _r.passed:
        raise AssertionError(
            f"ui/copy.py contains banned token in {_name!r}: matched {_r.match!r}"
        )
del _scrub, _inspect, _module
