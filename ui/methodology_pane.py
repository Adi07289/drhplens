"""
ui/methodology_pane.py — the "Show your work" methodology pane (METHOD-01).

A PURE render over cached data. The pane surfaces, top to bottom, five lines for
one answer/field:

  1. Retrieval query      — the field's known query constant (or the user question)
  2. Retrieved chunks     — the cached per-source scores + sections + snippets
     (with scores)          (read from the cached ``GroundedAnswer.claims[].sources[]``)
  3. Prompt used          — the developer-authored prompt text read off disk
  4. Sources cited        — the ``metadata_footer`` reused from ``ui.expander``
  5. Eval scores          — the latest COMMITTED ``eval/reports/*.md`` (parsed,
     (from the latest        never recomputed); degrades to the not-yet-available
      committed report)      copy when no report exists.

The numeric confidence score (0.00-1.00) + its rubric tier surface ONLY here
(D3-02 / L3-2) — never in the up-front red-flag row.

L3-6 / D3-17 / Pitfall 5: this module makes ZERO live calls. It imports no LLM or
vector-DB client and never invokes the graph — it renders exclusively from the
cached trace + a committed markdown report on disk. The no-live-client test pins
this by substring-scanning ``inspect.getsource`` for the forbidden client tokens.

STRIDE T-03-12: all snippet/metadata strings are HTML-escaped by ``ui.expander``;
prompt text is rendered inside an escaped ``st.code`` block — no ``unsafe_allow_html``
over un-escaped cached text.
"""
from __future__ import annotations

import re
from pathlib import Path

import streamlit as st

from agent.schemas import GroundedAnswer
from ui.copy import (
    CONFIDENCE_LABEL_TEMPLATE,
    CONFIDENCE_PLAIN_WORDS,
    CONFIDENCE_RUBRIC_LINE,
    METHODOLOGY_EVAL_ACCURACY_TEMPLATE,
    METHODOLOGY_EVAL_NOT_AVAILABLE,
    METHODOLOGY_EVAL_PROVENANCE_NOTE,
    METHODOLOGY_PANE_LABEL_CHUNKS,
    METHODOLOGY_PANE_LABEL_EVAL,
    METHODOLOGY_PANE_LABEL_PROMPT,
    METHODOLOGY_PANE_LABEL_QUERY,
    METHODOLOGY_PANE_LABEL_SOURCES,
    METHODOLOGY_SOURCE_HEADING,
    METHODOLOGY_SOURCE_LEAD,
    METHODOLOGY_SOURCE_LOCATION_TEMPLATE,
    METHODOLOGY_TECH_CAPTION,
    METHODOLOGY_TECH_TOGGLE,
    METHODOLOGY_TRIGGER,
    METHODOLOGY_TRUST_HEADING,
    METHODOLOGY_TRUST_TEMPLATE,
)
from ui.expander import render_citation_expanders


def latest_eval_scores(eval_report_dir: str) -> dict | None:
    """Return the most-recently-dated committed eval report, or ``None``.

    Eval reports are named ``<ISO-date>-*.md`` (e.g. ``2026-06-22-extraction-f1.md``)
    so the ISO date prefix sorts lexically — the max filename IS the newest report.
    The report is READ, never recomputed (D3-17 / Pitfall 5).

    Returns a dict shaped ``{"raw": <full report text>, "report_name": <filename>}``
    or ``None`` when the directory is missing or holds no ``*.md`` report.
    """
    report_dir = Path(eval_report_dir)
    if not report_dir.is_dir():
        return None
    reports = sorted(report_dir.glob("*.md"))
    if not reports:
        return None
    # ISO-date-prefixed filenames sort lexically == chronologically.
    latest = max(reports, key=lambda p: p.name)
    return {
        "raw": latest.read_text(encoding="utf-8"),
        "report_name": latest.name,
    }


def _citation_accuracy_pct(raw: str) -> str | None:
    """Pull the citation-accuracy figure out of a committed eval report as a
    plain percent string (e.g. ``"97%"``), or ``None`` if absent.

    The report carries a summary row like ``| Citation accuracy (grounded) | 0.97 |``.
    We read that committed number (never recompute it) and render it as a single
    investor-facing sentence in Tier 1.
    """
    match = re.search(r"Citation accuracy[^|\n]*\|\s*([0-9]*\.?[0-9]+)", raw)
    if not match:
        return None
    try:
        value = float(match.group(1))
    except ValueError:
        return None
    if value <= 1.0:  # stored as a 0-1 fraction — present as a percent.
        value *= 100
    return f"{round(value)}%"


def _read_prompt_text(prompt_path: str) -> str:
    """Read the developer-authored prompt text off disk (no live call).

    A missing prompt file degrades to a short note rather than crashing the pane
    (STRIDE T-03-12: malformed/missing on-disk artifact must not break render).
    """
    path = Path(prompt_path)
    if not path.is_file():
        return f"(prompt file not found: {prompt_path})"
    return path.read_text(encoding="utf-8")


def render_methodology_pane(
    *,
    query: str,
    grounded_answer: GroundedAnswer,
    prompt_path: str = "agent/prompts/generate.md",
    confidence_tier: str | None = None,
    confidence_score: float | None = None,
    eval_report_dir: str = "eval/reports",
    key: str | None = None,
) -> None:
    """Render the cached-only "Show your work" methodology pane for one answer.

    Every line is derived from cached/committed data: the passed ``query`` string,
    the cached ``grounded_answer`` trace, the on-disk ``prompt_path``, and the
    latest committed report under ``eval_report_dir``. NO argument is a live client
    and NO live LLM/Qdrant/graph call is made (METHOD-01 / D3-17 / Pitfall 5).
    """
    # One chip per unique claim, in claim order — reused for the citation descriptors.
    chip_map = {
        claim.claim_id: idx + 1 for idx, claim in enumerate(grounded_answer.claims)
    }
    descriptors = render_citation_expanders(grounded_answer, chip_map)
    scores = latest_eval_scores(eval_report_dir)

    with st.expander(METHODOLOGY_TRIGGER, expanded=False):
        # ── Tier 1: plain-English source verification (investor-facing) ──────
        st.markdown(f"**{METHODOLOGY_SOURCE_HEADING}**")
        st.caption(METHODOLOGY_SOURCE_LEAD)
        for claim in grounded_answer.claims:
            for source in claim.sources:
                location = METHODOLOGY_SOURCE_LOCATION_TEMPLATE.format(
                    page=source.page_start, section=source.section
                )
                st.markdown(f"**{location}**")
                if source.verbatim_span:
                    # Blockquote (reads like a citation, not a terminal dump).
                    st.markdown("> " + source.verbatim_span.replace("\n", "\n> "))

        # Trust: confidence-in-words + the committed citation-accuracy number.
        st.markdown(f"**{METHODOLOGY_TRUST_HEADING}**")
        trust_parts: list[str] = []
        if confidence_tier is not None:
            trust_parts.append(
                METHODOLOGY_TRUST_TEMPLATE.format(
                    tier_word=confidence_tier.capitalize(),
                    tier_meaning=CONFIDENCE_PLAIN_WORDS.get(confidence_tier, ""),
                )
            )
        accuracy = _citation_accuracy_pct(scores["raw"]) if scores else None
        if accuracy is not None:
            trust_parts.append(
                METHODOLOGY_EVAL_ACCURACY_TEMPLATE.format(accuracy=accuracy)
            )
        if trust_parts:
            st.markdown(" ".join(trust_parts))
        if scores is None:
            st.caption(METHODOLOGY_EVAL_NOT_AVAILABLE)

        # ── Tier 2: developer internals, hidden behind a toggle ──────────────
        # (Streamlit forbids nested expanders, so this is a toggle, not a second
        # expander.) Default off — the investor never sees it unless they ask.
        # A unique key is REQUIRED: the pane renders once per red-flag field +
        # per Q&A answer, so identical toggles would collide (Streamlit assigns
        # IDs by type+params). Callers pass an explicit key; otherwise derive a
        # stable one from the answer's claim ids.
        toggle_key = key or "methodpane_" + "_".join(
            c.claim_id for c in grounded_answer.claims
        )
        if st.toggle(METHODOLOGY_TECH_TOGGLE, value=False, key=f"{toggle_key}_tech"):
            st.caption(METHODOLOGY_TECH_CAPTION)

            # Retrieval query.
            st.markdown(f"**{METHODOLOGY_PANE_LABEL_QUERY}**")
            st.markdown(query)

            # Numeric confidence (0.00-1.00) surfaces ONLY inside this pane
            # (D3-02 / L3-2) — here, in the technical tier.
            if confidence_tier is not None:
                st.caption(
                    CONFIDENCE_LABEL_TEMPLATE.format(confidence_tier=confidence_tier)
                )
            if confidence_score is not None:
                st.caption(f"Confidence score: {confidence_score}")
                st.caption(CONFIDENCE_RUBRIC_LINE)

            # Retrieved chunks (with scores).
            st.markdown(f"**{METHODOLOGY_PANE_LABEL_CHUNKS}**")
            for claim in grounded_answer.claims:
                for source in claim.sources:
                    score_str = (
                        f"{source.score:.2f}" if source.score is not None else "—"
                    )
                    st.markdown(
                        f"DRHP page {source.page_start} · {source.section} · "
                        f"score {score_str}"
                    )
                    if source.verbatim_span:
                        st.code(source.verbatim_span)

            # Prompt used.
            st.markdown(f"**{METHODOLOGY_PANE_LABEL_PROMPT}**")
            st.code(_read_prompt_text(prompt_path))

            # Sources cited (reuse ui.expander metadata_footer).
            st.markdown(f"**{METHODOLOGY_PANE_LABEL_SOURCES}**")
            for descriptor in descriptors:
                st.markdown(descriptor["metadata_footer"])

            # Full eval report (latest committed; never recomputed).
            st.markdown(f"**{METHODOLOGY_PANE_LABEL_EVAL}**")
            if scores is None:
                st.markdown(METHODOLOGY_EVAL_NOT_AVAILABLE)
            else:
                st.caption(METHODOLOGY_EVAL_PROVENANCE_NOTE)
                st.markdown(scores["raw"])
