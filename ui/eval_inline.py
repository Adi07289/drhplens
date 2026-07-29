"""ui/eval_inline.py — Surface 1: the honest inline eval figure (EVAL-02).

Renders the system-level eval figure on every IPO snapshot page from the COMMITTED
``eval/reports/eval_summary.json`` — the same read-only ``card_data.json`` posture used
by ``pages/01_methodology.py``. It imports ONLY json / pathlib / html / streamlit and
makes NO live LLM / agent / judge / DeepEval call at render (P19, demo-safe), pinned by
the ``inspect.getsource`` + AST-import isolation test in ``tests/unit/test_eval_inline.py``.

Honesty invariant (SEBI / compliance, non-negotiable — 06.1-UI-SPEC):
  - eval numbers are PLAIN IBM-Plex-Mono figures via ``.drhp-eval-figure`` — NO red/green,
    NO badge, NO severity icon, NO verdict UX; a 0.31 and a 0.99 render byte-identically
    except the digits;
  - accent amber is reserved for the ``view report`` link alone;
  - provenance (n, ipo, generated date, judge model) accompanies every figure;
  - ``faithfulness_deepeval == -1.0`` is the documented "not measured" sentinel — rendered
    verbatim as ``not measured``, NEVER ``0.00`` / ``-1.00`` / a guess;
  - a per-IPO line renders ONLY when ``per_ipo[drhp_id]`` exists — never a fabricated number;
  - a missing metric renders ``—`` (em dash); a missing ``report`` omits the link (no dead link);
  - an absent / unreadable JSON renders a single muted fallback line, never a crash.
Every interpolated string is HTML-escaped before markup interpolation (T-6.1-19 XSS).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

# Read-only committed artifact (mirrors _card_data_path in pages/01_methodology.py).
_EVAL_SUMMARY_PATH = (
    Path(__file__).resolve().parents[1] / "eval" / "reports" / "eval_summary.json"
)

# The documented "not measured" sentinel for the LLM-judge faithfulness metric
# (eval.metrics.schema: faithfulness_deepeval == -1.0 is the ONLY sub-zero value —
# rate-limited / key unset — never a real 0.0).
_NOT_MEASURED_SENTINEL = -1.0

_EMPTY_FALLBACK = "Eval metrics not yet generated for this release."


def _eval_num(value, nd: int = 2) -> str:
    """2-decimal figure; None / NaN / non-numeric -> em dash. NEVER 0.00 as a guess."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    return "—" if num != num else f"{num:.{nd}f}"


def _faithfulness_display(value) -> str:
    """The faithfulness figure: the -1.0 sentinel -> 'not measured' (honest, never a
    number); None / NaN -> em dash; otherwise the 2-decimal value."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    if num != num:  # NaN
        return "—"
    if num == _NOT_MEASURED_SENTINEL:
        return "not measured"
    return f"{num:.2f}"


def _figure(text: str) -> str:
    """Wrap a value in the neutral, value-invariant mono figure span (no verdict UX)."""
    return f'<span class="drhp-eval-figure">{html.escape(text)}</span>'


def _metrics_clause(block: dict) -> str:
    """The 'faithfulness … · recall@10 … · citation …' clause — identical grammar for
    the system-level and per-IPO lines. Every value is a neutral .drhp-eval-figure so a
    high and a low score render byte-identically except the digits."""
    faith = _figure(_faithfulness_display(block.get("faithfulness_deepeval")))
    recall = _figure(_eval_num(block.get("recall_at_10")))
    citation = _figure(_eval_num(block.get("citation_accuracy")))
    return f"faithfulness {faith} · recall@10 {recall} · citation {citation}"


def render_eval_inline(drhp_id: str) -> None:
    """Render the honest inline eval figure for an IPO page.

    Read-only: reads the committed ``eval_summary.json`` once (``.is_file()`` +
    try/except) and makes no live call. Absent / unreadable JSON -> a single muted
    fallback line, never a crash.
    """
    if not _EVAL_SUMMARY_PATH.is_file():
        st.markdown(
            f'<p class="drhp-eval-empty">{html.escape(_EMPTY_FALLBACK)}</p>',
            unsafe_allow_html=True,
        )
        return
    try:
        summary = json.loads(_EVAL_SUMMARY_PATH.read_text(encoding="utf-8"))
    except Exception:
        st.markdown(
            f'<p class="drhp-eval-empty">{html.escape(_EMPTY_FALLBACK)}</p>',
            unsafe_allow_html=True,
        )
        return

    corpus = summary.get("corpus", {}) or {}
    aggregate = summary.get("aggregate", {}) or {}
    per_ipo = summary.get("per_ipo", {}) or {}

    # Provenance is MANDATORY on the system-level line: n, ipo, date, judge model.
    n_questions = html.escape(str(corpus.get("n_questions", "—")))
    ipo = html.escape(str(corpus.get("ipo", "—")))
    generated = html.escape(str(summary.get("generated", "—")))
    judge_model = html.escape(str(summary.get("judge_model", "—")))

    # Honest base: the deterministic metrics are scored over the GRADED subset, not every
    # entry (refusal-eligible questions are excluded). Show "N-question set · M scored" so
    # the surface never implies all N were measured (UI audit WARNING). Falls back to the
    # plain set size when n_scored is absent (older artifacts).
    n_scored = corpus.get("n_scored")
    if n_scored is not None:
        set_clause = f"our {n_questions}-question eval set ({html.escape(str(n_scored))} scored)"
    else:
        set_clause = f"our {n_questions}-question eval set"
    provenance = (
        f"Measured over {set_clause} "
        f"({ipo}, {generated}, judge {judge_model}): "
    )
    system_line = provenance + _metrics_clause(aggregate)

    # Report reference. The committed report lives at a repo-relative path Streamlit does
    # not serve (and the branch isn't deployed), so rendering it as an <a href> would be a
    # DEAD link (UI audit WARNING). Show the path as PLAIN neutral mono text instead — no
    # dead link, honest provenance. This can become a real link once the app is deployed and
    # the report is served/pushed (OPS-02). Omit entirely when `report` is absent.
    report = summary.get("report")
    if report:
        system_line += (
            f' · report: <span class="drhp-eval-report-ref">{html.escape(str(report))}</span>'
        )

    # A single muted <p> with text content (never a bare <div>, never a split card) so
    # the Streamlit sanitizer keeps it; the report <a> is inline inside the <p> (safe).
    st.markdown(
        f'<p class="drhp-eval-inline">{system_line}</p>',
        unsafe_allow_html=True,
    )

    # Per-IPO sub-line ONLY when this IPO has a real gold-set entry. Never fabricate a
    # per-IPO number for an IPO absent from per_ipo.
    if drhp_id in per_ipo:
        entry = per_ipo[drhp_id] or {}
        n_val = entry.get("n")
        n_clause = f" (n={html.escape(str(n_val))})" if n_val is not None else ""
        per_line = f"This IPO's eval{n_clause}: " + _metrics_clause(entry)
        st.markdown(
            f'<p class="drhp-eval-per-ipo">{per_line}</p>',
            unsafe_allow_html=True,
        )
