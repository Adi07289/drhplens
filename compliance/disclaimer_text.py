"""
Single source of truth for DRHPLens disclaimer copy — D-07 anchor strings.

These constants are the CANONICAL source. All three UI surfaces (modal, persistent
footer, per-answer footer) import from here. Future legal-review copy edits touch
THIS file only — not individual call sites.

BYTE-FOR-BYTE INTEGRITY: ANCHOR_COPY is the D-07 string with:
  - Straight ASCII apostrophe (U+0027) — no smart quotes
  - No trailing whitespace
  - Four sentences, each ending with a period
  - All tests in test_disclaimer_surface.py assert byte-for-byte equality

D-08 three-surface requirement: modal + persistent footer + per-answer footer.
TRUST-03 SEBI Jan-2025 RA requirements:
  - Minimum 10pt equivalent font size (12px CSS = 10.5pt at 1x zoom)
  - AI-disclosure copy: modal body contains "large language models"
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# D-07 anchor copy — the canonical disclaimer text.
# Subject to legal-review polish before Phase 6 public launch.
# DO NOT paraphrase or edit without a phase-protocol discussion.
# ---------------------------------------------------------------------------
ANCHOR_COPY: str = (
    "DRHPLens reads prospectuses for you. "
    "It cites what the document says and shows historical context. "
    "Decisions about investing are yours. "
    "This is not investment advice."
)

# ---------------------------------------------------------------------------
# Modal (first-use) copy
# ---------------------------------------------------------------------------

MODAL_HEADING: str = "Read this once."

MODAL_BODY_ADDENDUM: str = (
    "The system uses large language models that occasionally make mistakes"
    " — every claim links to its source page so you can verify."
)
"""AI-disclosure addendum per SEBI Jan-2025 RA guidelines (UI-SPEC L-11, TRUST-03).
Must contain the substring 'large language models'.
"""

MODAL_CTA: str = "I understand — open DRHPLens"

# ---------------------------------------------------------------------------
# Footer copy
# ---------------------------------------------------------------------------

PERSISTENT_FOOTER_SUFFIX: str = " · methodology"
"""Appended to ANCHOR_COPY in the persistent footer; 'methodology' is wrapped
in an <a href="/methodology"> link by render_persistent_footer()."""

PER_ANSWER_FOOTER: str = "Informational only — not advice."
"""Per-answer disclaimer appended below every generated answer (D-08 surface 3)."""
