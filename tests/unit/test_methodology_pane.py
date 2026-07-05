"""
Unit test — the "show your work" methodology pane (METHOD-01): renders from
cached per-claim data (no live LLM/Qdrant call), and the module imports no LLM or
Qdrant client (the inspect.getsource / AST substring check mirroring
test_cite_check.test_no_llm_judge_fallback).

Requirement: METHOD-01. Plan 06 implements ui/methodology_pane.py.

The pane is a pure render over cached `GroundedAnswer` + the field's known query
constant + the latest committed `eval/reports/*.md`. NO argument is a live client;
the module makes zero graph/LLM/Qdrant calls on expand (Pitfall 5 / L3-6 / D3-17).
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import ui.methodology_pane as mp
from ui.methodology_pane import latest_eval_scores, render_methodology_pane


def _grounded_answer_from_record(synthetic_redflag_record):
    """Pull the cached GroundedAnswer out of the synthetic record's rpt_pct field."""
    return synthetic_redflag_record.fields["rpt_pct"].value


def test_pane_renders_from_cache(synthetic_redflag_record, tmp_path, capsys, monkeypatch):
    """The pane builds its content (query / chunks+scores / prompt / sources /
    eval scores) from cached RedFlagRecord + committed eval reports, no live call.

    We stub Streamlit so the test runs headless and asserts the five Phase 3 pane
    labels are emitted, and that the numeric confidence score surfaces in the pane.
    """
    ga = _grounded_answer_from_record(synthetic_redflag_record)

    # A committed eval report on disk (dated) — parsed, never recomputed.
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "2026-06-20-extraction-f1.md").write_text(
        "# Red-Flag Extraction F1 — 2026-06-20\n\n"
        "## Summary\n\n"
        "| Metric | Value |\n|---|---|\n"
        "| Citation accuracy (grounded) | 0.97 |\n"
        "| Macro F1 (mean per-field score) | 0.91 |\n",
        encoding="utf-8",
    )

    # Capture every markdown/label string the pane emits via a recording stub.
    emitted: list[str] = []

    class _ExpanderCtx:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _StStub:
        def expander(self, label, expanded=False):
            emitted.append(f"EXPANDER:{label}")
            return _ExpanderCtx()

        def markdown(self, body, unsafe_allow_html=False):
            emitted.append(body)

        def caption(self, body):
            emitted.append(body)

        def code(self, body, language=None):
            emitted.append(body)

        def write(self, body):
            emitted.append(str(body))

    monkeypatch.setattr(mp, "st", _StStub())

    render_methodology_pane(
        query="What are the related-party transactions?",
        grounded_answer=ga,
        prompt_path="agent/prompts/generate.md",
        confidence_tier="high",
        confidence_score=0.9,
        eval_report_dir=str(report_dir),
    )

    blob = "\n".join(emitted)
    # The five Phase 3 pane labels render.
    assert "Show your work" in blob
    assert "Retrieval query" in blob
    assert "Retrieved chunks (with scores)" in blob
    assert "Prompt used" in blob
    assert "Sources cited" in blob
    assert "Eval scores (from the latest committed report)" in blob
    # The retrieval query string renders.
    assert "related-party transactions" in blob.lower()
    # The numeric confidence score (0.00-1.00) surfaces ONLY here.
    assert "0.9" in blob
    # A retrieved-chunk score from the cached sources[] renders.
    assert "0.88" in blob


def test_pane_renders_eval_not_available_when_no_report(
    synthetic_redflag_record, tmp_path, monkeypatch
):
    """With no committed eval report present, the pane renders the
    eval-not-yet-available copy and still renders the other four lines."""
    ga = _grounded_answer_from_record(synthetic_redflag_record)
    empty_report_dir = tmp_path / "empty_reports"
    empty_report_dir.mkdir()

    emitted: list[str] = []

    class _ExpanderCtx:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _StStub:
        def expander(self, label, expanded=False):
            emitted.append(f"EXPANDER:{label}")
            return _ExpanderCtx()

        def markdown(self, body, unsafe_allow_html=False):
            emitted.append(body)

        def caption(self, body):
            emitted.append(body)

        def code(self, body, language=None):
            emitted.append(body)

        def write(self, body):
            emitted.append(str(body))

    monkeypatch.setattr(mp, "st", _StStub())

    render_methodology_pane(
        query="What are the related-party transactions?",
        grounded_answer=ga,
        confidence_tier="high",
        confidence_score=0.9,
        eval_report_dir=str(empty_report_dir),
    )

    blob = "\n".join(emitted)
    from ui.copy import METHODOLOGY_EVAL_NOT_AVAILABLE

    assert METHODOLOGY_EVAL_NOT_AVAILABLE in blob
    # The other four lines still render from cached trace.
    assert "Retrieval query" in blob
    assert "Retrieved chunks (with scores)" in blob
    assert "Prompt used" in blob
    assert "Sources cited" in blob


def test_latest_eval_scores_picks_most_recent_dated_report(tmp_path):
    """latest_eval_scores reads the most-recently-dated eval/reports/*.md."""
    report_dir = tmp_path / "reports"
    report_dir.mkdir()
    (report_dir / "2026-06-10-extraction-f1.md").write_text(
        "## Summary\n| Macro F1 (mean per-field score) | 0.50 |\n", encoding="utf-8"
    )
    (report_dir / "2026-06-22-extraction-f1.md").write_text(
        "## Summary\n| Macro F1 (mean per-field score) | 0.91 |\n", encoding="utf-8"
    )
    scores = latest_eval_scores(str(report_dir))
    assert scores is not None
    # The newer report's content is the one parsed.
    assert "0.91" in scores["raw"]
    assert "2026-06-22" in scores["report_name"]


def test_latest_eval_scores_none_when_no_reports(tmp_path):
    """latest_eval_scores returns None when no committed report exists."""
    report_dir = tmp_path / "empty"
    report_dir.mkdir()
    assert latest_eval_scores(str(report_dir)) is None


def test_no_llm_or_qdrant_import() -> None:
    """ui/methodology_pane.py must not import any LLM or Qdrant client
    (Pitfall 5: pane is pure render over cached data). Mirrors
    test_cite_check.test_no_llm_judge_fallback."""
    src = inspect.getsource(mp)
    forbidden = ("openai", "genai", "instructor", "groq", "qdrant", "GRAPH.invoke")
    for token in forbidden:
        assert token not in src, (
            f"ui/methodology_pane.py must not reference {token!r} "
            f"(L3-6/Pitfall 5: cached-only render, no live call)."
        )
