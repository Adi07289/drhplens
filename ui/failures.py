"""ui/failures.py — the FAILGAL-01 /failures gallery (render-only, honesty-invariant).

Renders a browseable gallery of real DRHPLens failures from the COMMITTED
``eval/failures/failures.yaml`` — the same read-only posture as ``ui/eval_inline.py``.
It imports ONLY {__future__, html, pathlib, yaml, streamlit} and makes NO live
LLM / agent / vector / model call at render (P19, demo-safe), pinned by the
``inspect.getsource`` + AST-import-allowlist test in ``tests/unit/test_failures.py``.

Honesty invariant (SEBI / compliance, non-negotiable — 06.2-UI-SPEC §C2):
  - ``open`` vs ``mitigated`` render in muted mono with a DASHED NEUTRAL border — never a
    red/green verdict colour; two entries that differ only in status render byte-identically
    except the status text;
  - the amber left-rule / surface chip / Actual-column rule are scannability accents, NOT
    "bad" signals — accent never encodes good/bad;
  - no failure is spun as a win — the evaluative copy lives in the (un-scrubbed) YAML data
    file, deliberately kept out of ``ui/copy.py``;
  - the gallery is filterable by surface + free-text ENTIRELY in-memory over the already-loaded
    entries (the "searchable" FAILGAL-01 mechanism) — no live call on filter;
  - an absent / unreadable / empty file, or a no-match search, renders ONE muted empty-state
    <p>, never a crash.
Every interpolated field is HTML-escaped before markup interpolation (V5 / T-6.1-19 XSS).
YAML is parsed with the safe loader only (never the unsafe full loader — V12, no tag
execution from a data file).
"""
from __future__ import annotations

import html
from pathlib import Path

import yaml
import streamlit as st

# Read-only committed artifact (mirrors _EVAL_SUMMARY_PATH in ui/eval_inline.py).
_FAILURES_PATH = (
    Path(__file__).resolve().parents[1] / "eval" / "failures" / "failures.yaml"
)

# Empty-state copy — defined LOCALLY (not imported from ui.copy) so the read-only
# AST allowlist {__future__, html, pathlib, yaml, streamlit} stays pure; importing
# ui.copy would add "ui" to the import set and break the P19 isolation test. This
# mirrors ui/eval_inline.py's local _EMPTY_FALLBACK constant. The page-chrome
# strings (eyebrow / heading) live in ui/copy.py for pages/04_failures.py.
_EMPTY_HEADING = "No failures loaded."
_EMPTY_BODY = "Run the eval suite to populate `eval/failures/failures.yaml`."

# Surface grouping order for the vertical stack (stable within a surface).
_SURFACE_ORDER = {"rag": 0, "extraction": 1, "forecast": 2}

# Fields the free-text search scans (lower-cased substring, in-memory).
_SEARCH_FIELDS = ("id", "category", "query", "expected", "actual", "postmortem")


def _empty_state() -> None:
    """Emit the single muted empty-state <p> (absent/unreadable/empty file, or a
    no-match search). Never a crash, never a colour."""
    st.markdown(
        f'<p class="drhp-fail-empty">{html.escape(_EMPTY_HEADING)} '
        f'{html.escape(_EMPTY_BODY)}</p>',
        unsafe_allow_html=True,
    )


def _status_label(status: str, by_design: bool) -> str:
    """Map the neutral status to its UI-SPEC label. Never a colour — the honesty
    invariant renders open/mitigated in muted mono only.

      mitigated            -> ``MITIGATED``
      open + by_design     -> ``OPEN · BY DESIGN``
      open                 -> ``OPEN``
    """
    if (status or "").strip().lower() == "mitigated":
        return "MITIGATED"
    return "OPEN · BY DESIGN" if by_design else "OPEN"


def _card_html(entry: dict) -> str:
    """Build the neutral, fully-escaped inner card markup for one failure entry.

    Every interpolated field is ``html.escape(str(...))`` before interpolation; the
    status is a fixed derived label (never the raw data string) so a failure can never
    be coloured. Only ``.drhp-fail-*`` classes appear."""
    fail_id = html.escape(str(entry.get("id", "")))
    surface = html.escape(str(entry.get("surface", "")))
    category = html.escape(str(entry.get("category", "")))
    query = html.escape(str(entry.get("query", "")))
    expected = html.escape(str(entry.get("expected", "")))
    actual = html.escape(str(entry.get("actual", "")))
    postmortem = html.escape(str(entry.get("postmortem", "")))
    status_label = _status_label(str(entry.get("status", "")), bool(entry.get("by_design")))

    return (
        f'<div class="drhp-fail-card" id="drhp-fail-{fail_id}">'
        f'<div class="drhp-fail-head">'
        f'<span class="drhp-fail-chip">{surface.upper()}</span>'
        f'<span class="drhp-fail-cat">category: {category}</span>'
        f'<span class="drhp-fail-status">{status_label}</span>'
        f'</div>'
        f'<h3 class="drhp-fail-title">{query}</h3>'
        f'<div class="drhp-fail-grid">'
        f'<div class="drhp-fail-expected">'
        f'<span class="drhp-fail-label">Expected</span>'
        f'<span class="drhp-fail-val">{expected}</span></div>'
        f'<div class="drhp-fail-actual">'
        f'<span class="drhp-fail-label">Actual</span>'
        f'<span class="drhp-fail-val">{actual}</span></div>'
        f'</div>'
        f'<div class="drhp-fail-postmortem">'
        f'<span class="drhp-fail-pmlabel">Post-mortem</span>'
        f'<span class="drhp-fail-pmbody">{postmortem}</span></div>'
        f'</div>'
    )


def render_failures(surface: str | None = None, query: str | None = None) -> None:
    """Render the /failures gallery from the committed ``failures.yaml``.

    Read-only: reads the committed file once (``.is_file()`` + try/except) and makes no
    live call. Optional ``surface`` / ``query`` filter the already-loaded entries IN-MEMORY
    (the FAILGAL-01 "searchable" mechanism — no live call). An absent/unreadable/empty file,
    or a filtered-to-empty result, renders the single muted empty-state <p>, never a crash.
    """
    if not _FAILURES_PATH.is_file():
        _empty_state()
        return
    try:
        entries = yaml.safe_load(_FAILURES_PATH.read_text(encoding="utf-8"))
    except Exception:
        _empty_state()
        return

    if not isinstance(entries, list) or not entries:
        _empty_state()
        return

    # Defensive: the file is hand-curated — drop any non-mapping list element so a stray
    # bare string / null can never AttributeError on .get() in the filters/loop below (WR-01).
    entries = [e for e in entries if isinstance(e, dict)]
    if not entries:
        _empty_state()
        return

    # ── Render-only filters (in-memory over already-loaded entries; NO live call) ──
    if surface and surface != "all":
        entries = [e for e in entries if e.get("surface") == surface]
    if query and query.strip():
        needle = query.strip().lower()
        entries = [
            e for e in entries
            if needle in " ".join(str(e.get(k, "")) for k in _SEARCH_FIELDS).lower()
        ]

    if not entries:
        _empty_state()
        return

    # Group/order the vertical stack by surface (stable within a surface).
    entries = sorted(entries, key=lambda e: _SURFACE_ORDER.get(e.get("surface", ""), 99))

    for entry in entries:
        # st.container(border=True, key="drhpcard-fail-…") is the lifted-depth card hook —
        # the `drhpcard-` prefix inherits the ambient shadow/bevel (drhplens.css:1358-1374).
        # One inner st.markdown for the whole card (never a split <div> — the Phase-3
        # white-bar lesson).
        with st.container(border=True, key=f"drhpcard-fail-{html.escape(str(entry.get('id', '')))}"):
            st.markdown(_card_html(entry), unsafe_allow_html=True)
