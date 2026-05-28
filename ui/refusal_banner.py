"""
Refusal banner renderer — consumes RefusalResponse; renders amber surface.

UI-SPEC anti-pattern: do NOT replace with st.warning or st.error — refusals
are first-class output, not chrome.

The <button> elements here are visual-only. The functional click handler is
wired in app.py via st.button widgets rendered alongside the HTML banner
(UI-SPEC §Streamlit-Specific Constraints reformulation-chip row — two-layer pattern).
"""
from __future__ import annotations

import html as _html

from agent.schemas import RefusalResponse
from compliance.disclaimer_text import PER_ANSWER_FOOTER

# ── Module-level heading constants (scrubber-testable, locked) ────────────────

REFUSAL_HEADING_LOW_RETRIEVAL: str = "This isn't in the DRHP."
REFUSAL_HEADING_PARTIAL_GROUNDING: str = "The DRHP only addresses part of this."
REFUSAL_HEADING_BANNED_TOKEN: str = "Couldn't return that answer."
REFUSAL_HEADING_INFRASTRUCTURE: str = "Couldn't reach the DRHP."

# Phase 1 policy: cap at 2 reformulation chips (matches RELAXED_SEARCH_TOP_SECTIONS=2
# in 01-04-PLAN.md). UI-SPEC allows up to 3; Phase 2 may raise.
MAX_CHIPS_RENDERED: int = 2


def _select_heading(refusal: RefusalResponse) -> str:
    """Select the banner heading based on refusal reason."""
    reason = refusal.reason
    if reason == "low_retrieval_score":
        return REFUSAL_HEADING_LOW_RETRIEVAL
    if reason == "unsupported_claim":
        if "addresses parts of" in refusal.explanation:
            return REFUSAL_HEADING_PARTIAL_GROUNDING
        return REFUSAL_HEADING_LOW_RETRIEVAL
    if reason == "banned_token":
        return REFUSAL_HEADING_BANNED_TOKEN
    # infrastructure_error + fallback
    return REFUSAL_HEADING_INFRASTRUCTURE


def render_refusal_banner(refusal: RefusalResponse) -> str:
    """Return the full refusal banner HTML string.

    T-1-06: html.escape applied to every dynamic string field.
    aria-live="polite" per UI-SPEC Accessibility §Live regions.
    Per UI-SPEC anti-pattern §"Banned-token detected": NO chips when reason=banned_token.

    The per-answer disclaimer (Informational only — not advice.) is baked into
    the banner structure per UI-SPEC §Visuals §Refusal Banner §Content layout 4.
    This function intentionally does NOT import the per-answer footer renderer to keep
    the import graph clean (UI-SPEC §Disclaimer Surfaces §3 enforcement).
    """
    heading = _select_heading(refusal)
    escaped_heading = _html.escape(heading)
    escaped_message = _html.escape(refusal.explanation)
    escaped_disclaimer = _html.escape(PER_ANSWER_FOOTER)

    # Build suggestion chips (visual-only HTML buttons)
    chips_html = ""
    show_chips = (
        refusal.reason != "banned_token"
        and bool(refusal.reformulation_suggestions)
    )
    if show_chips:
        chip_parts = []
        for s in refusal.reformulation_suggestions[:MAX_CHIPS_RENDERED]:
            esc_s = _html.escape(s)
            esc_s_attr = _html.escape(s, quote=True)
            chip_parts.append(
                f'<button class="drhp-suggest" type="button" '
                f'data-suggestion="{esc_s_attr}">{esc_s}</button>'
            )
        chips_html = (
            f'<div class="drhp-suggest-group">'
            f'{"".join(chip_parts)}'
            f'</div>'
        )

    return (
        f'<div class="drhp-refusal" role="alert" aria-live="polite">'
        f'<h2 class="drhp-refusal-heading">{escaped_heading}</h2>'
        f'<p class="drhp-refusal-body">{escaped_message}</p>'
        f'{chips_html}'
        f'<div class="drhp-disclaimer-per-answer">{escaped_disclaimer}</div>'
        f'</div>'
    )
