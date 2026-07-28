"""Unit tests — the honest inline eval figure (EVAL-02, Surface 1).

Pins the 9 honesty-invariant acceptance checks from 06.1-UI-SPEC on
``ui.eval_inline.render_eval_inline``:

  (a) read-only isolation — imports ONLY json / pathlib / html / streamlit, no
      LLM / agent / DeepEval client, no live call (AST import allowlist +
      inspect.getsource forbidden-token scan);
  (b) value-invariant styling — a 0.31 and a 0.99 summary render byte-identically
      except the digits (same classes);
  (c) no fabricated per-IPO number — no ``This IPO's eval`` line for an IPO absent
      from ``per_ipo``;
  (d) provenance always present — n, ipo, generated date, judge_model;
  (e) a missing metric renders ``—`` (em dash), never ``0.00``;
  (f) a missing ``report`` key omits the link (no dead link);
  (g) graceful absence — an absent / unreadable JSON renders the muted fallback and
      does not crash;
  (h) no verdict / severity styling — only the neutral ``.drhp-eval-*`` classes,
      no inline color, no badge / severity / emoji / arrow;
  (i) the judge model is named in the provenance clause, before the faithfulness
      figure (LLM-judge, reported not gated).

Plus the -1.0 "not measured" sentinel landmine: faithfulness == -1.0 renders
``not measured``, never ``0.00`` / ``-1.00``.
"""
from __future__ import annotations

import ast
import inspect
import json
import re

import ui.eval_inline as eval_inline
from ui.eval_inline import render_eval_inline

# The eval markup may only carry these neutral classes — any other class token
# (badge / severity / success / danger / green / red …) is a verdict-UX breach.
_ALLOWED_CLASSES = {
    "drhp-eval-inline",
    "drhp-eval-figure",
    "drhp-eval-report-link",
    "drhp-eval-per-ipo",
    "drhp-eval-empty",
}


class _RecordingSt:
    """A minimal Streamlit stub recording every markdown body."""

    def __init__(self) -> None:
        self.emitted: list[str] = []

    def markdown(self, body, unsafe_allow_html=False):
        self.emitted.append(body)


def _summary(v, *, per_ipo=None, report="eval/reports/2026-07-28-rag-eval.md",
             judge="gemini-3.5-flash"):
    """A synthetic eval_summary.json whose every metric is the same value ``v`` (so a
    value-invariance diff isolates the digits)."""
    block = {
        "faithfulness_deepeval": v,
        "citation_accuracy": v,
        "recall_at_5": v,
        "recall_at_10": v,
        "recall_at_30": v,
    }
    s = {
        "generated": "2026-07-28",
        "judge_model": judge,
        "corpus": {"gold_set": "g.jsonl", "ipo": "Swiggy DRHP", "n_questions": 13},
        "aggregate": dict(block),
        "per_ipo": per_ipo or {},
    }
    if report is not None:
        s["report"] = report
    return s


def _render(tmp_path, monkeypatch, summary, drhp_id="swiggy_2024_11"):
    path = tmp_path / "eval_summary.json"
    path.write_text(json.dumps(summary), encoding="utf-8")
    monkeypatch.setattr(eval_inline, "_EVAL_SUMMARY_PATH", path)
    st = _RecordingSt()
    monkeypatch.setattr(eval_inline, "st", st)
    render_eval_inline(drhp_id)
    return "\n".join(st.emitted)


# ── (a) read-only isolation ──────────────────────────────────────────────────
def test_read_only_isolation_no_llm_import():
    """The render module imports ONLY the read-only stdlib + streamlit set, and makes
    no live judge / agent / client call (P19). NB: bare ``deepeval`` is NOT a forbidden
    substring — ``faithfulness_deepeval`` is a required honest provenance key — so the
    AST import allowlist below is what forbids importing the DeepEval library."""
    src = inspect.getsource(eval_inline)
    tree = ast.parse(src)
    allowed_imports = {"__future__", "html", "json", "pathlib", "streamlit"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    stray = imported - allowed_imports
    assert not stray, f"ui/eval_inline.py imports outside the read-only allowlist: {stray}"

    forbidden = (
        "openai", "genai", "instructor", "groq", "qdrant",
        "GeminiModel", "GRAPH.invoke", ".invoke(",
        "import deepeval", "from deepeval",
        "langgraph", "llama_index",
    )
    for token in forbidden:
        assert token not in src, (
            f"ui/eval_inline.py must not reference {token!r} "
            f"(P19: read the committed JSON only, no live call)."
        )


# ── (b) value-invariant styling ──────────────────────────────────────────────
def test_value_invariant_styling(tmp_path, monkeypatch):
    """A 0.99 and a 0.31 summary render byte-identically except the digits."""
    high = _render(tmp_path, monkeypatch, _summary(0.99), drhp_id="not_in_per_ipo")
    low = _render(tmp_path, monkeypatch, _summary(0.31), drhp_id="not_in_per_ipo")
    assert high != low
    assert high.replace("0.99", "N") == low.replace("0.31", "N")


# ── (c) no fabricated per-IPO number ─────────────────────────────────────────
def test_no_fabricated_per_ipo_line(tmp_path, monkeypatch):
    """An IPO absent from per_ipo shows NO per-IPO line — never a fabricated number."""
    per = {"swiggy_2024_11": {"faithfulness_deepeval": 0.9, "citation_accuracy": 0.9,
                              "recall_at_5": 0.9, "recall_at_10": 0.9, "recall_at_30": 0.9}}
    out = _render(tmp_path, monkeypatch, _summary(0.9, per_ipo=per), drhp_id="reliance_2025")
    assert "This IPO's eval" not in out
    assert "drhp-eval-per-ipo" not in out


def test_per_ipo_line_renders_when_entry_exists(tmp_path, monkeypatch):
    """The per-IPO sub-line renders for an IPO WITH a real gold-set entry."""
    per = {"swiggy_2024_11": {"faithfulness_deepeval": 0.9, "citation_accuracy": 0.9,
                              "recall_at_5": 0.9, "recall_at_10": 0.9, "recall_at_30": 0.9}}
    out = _render(tmp_path, monkeypatch, _summary(0.9, per_ipo=per), drhp_id="swiggy_2024_11")
    assert "This IPO's eval" in out
    assert "drhp-eval-per-ipo" in out


# ── (d) provenance always present ────────────────────────────────────────────
def test_provenance_present(tmp_path, monkeypatch):
    out = _render(tmp_path, monkeypatch, _summary(0.9))
    assert "13-question" in out          # n
    assert "Swiggy DRHP" in out          # ipo
    assert "2026-07-28" in out           # generated date
    assert "gemini-3.5-flash" in out     # judge_model


# ── (e) missing metric -> em dash, never 0.00 ────────────────────────────────
def test_missing_metric_renders_em_dash_not_zero(tmp_path, monkeypatch):
    s = _summary(0.9)
    s["aggregate"]["recall_at_10"] = None
    out = _render(tmp_path, monkeypatch, s)
    assert "—" in out
    assert "0.00" not in out


# ── (f) missing report -> no link ────────────────────────────────────────────
def test_missing_report_omits_link(tmp_path, monkeypatch):
    out = _render(tmp_path, monkeypatch, _summary(0.9, report=None))
    assert "view report" not in out
    assert "drhp-eval-report-link" not in out


# ── (g) graceful absence ─────────────────────────────────────────────────────
def test_absent_json_renders_fallback(tmp_path, monkeypatch):
    missing = tmp_path / "nope.json"
    monkeypatch.setattr(eval_inline, "_EVAL_SUMMARY_PATH", missing)
    st = _RecordingSt()
    monkeypatch.setattr(eval_inline, "st", st)
    render_eval_inline("swiggy_2024_11")  # must not raise
    out = "\n".join(st.emitted)
    assert "Eval metrics not yet generated for this release." in out
    assert "drhp-eval-empty" in out


def test_unreadable_json_renders_fallback(tmp_path, monkeypatch):
    path = tmp_path / "eval_summary.json"
    path.write_text("{ this is not valid json", encoding="utf-8")
    monkeypatch.setattr(eval_inline, "_EVAL_SUMMARY_PATH", path)
    st = _RecordingSt()
    monkeypatch.setattr(eval_inline, "st", st)
    render_eval_inline("swiggy_2024_11")  # must not raise
    assert "Eval metrics not yet generated for this release." in "\n".join(st.emitted)


# ── (h) no verdict / severity styling ────────────────────────────────────────
def test_no_verdict_or_severity_markup(tmp_path, monkeypatch):
    """Only the neutral .drhp-eval-* classes appear; no inline color, no badge /
    severity / emoji / arrow. Exercises BOTH the system-level and per-IPO lines."""
    per = {"swiggy_2024_11": {"faithfulness_deepeval": 0.31, "citation_accuracy": 0.31,
                              "recall_at_5": 0.31, "recall_at_10": 0.31, "recall_at_30": 0.31}}
    out = _render(tmp_path, monkeypatch, _summary(0.31, per_ipo=per), drhp_id="swiggy_2024_11")

    for class_attr in re.findall(r'class="([^"]*)"', out):
        for cls in class_attr.split():
            assert cls in _ALLOWED_CLASSES, f"unexpected verdict-ish class {cls!r} on eval markup"

    assert "style=" not in out  # no inline color / severity styling
    for glyph in ("✅", "❌", "⚠️", "🔴", "🟢", "▲", "▼", "↑", "↓"):
        assert glyph not in out


# ── (i) judge model named in the provenance clause ───────────────────────────
def test_judge_model_named_before_faithfulness(tmp_path, monkeypatch):
    out = _render(tmp_path, monkeypatch, _summary(0.9, judge="gemini-3.5-flash"))
    assert "judge gemini-3.5-flash" in out
    assert out.index("judge gemini-3.5-flash") < out.index("faithfulness")


# ── landmine: the -1.0 "not measured" sentinel ───────────────────────────────
def test_faithfulness_sentinel_renders_not_measured(tmp_path, monkeypatch):
    s = _summary(1.0)
    s["aggregate"]["faithfulness_deepeval"] = -1.0
    out = _render(tmp_path, monkeypatch, s)
    assert "not measured" in out
    assert "-1.00" not in out
    assert "0.00" not in out


def test_committed_eval_summary_renders_without_crash(tmp_path, monkeypatch):
    """The REAL committed eval_summary.json renders: faithfulness -1 -> 'not measured',
    the swiggy per-IPO line present, no crash."""
    st = _RecordingSt()
    monkeypatch.setattr(eval_inline, "st", st)
    render_eval_inline("swiggy_2024_11")
    out = "\n".join(st.emitted)
    assert "Swiggy DRHP" in out
    assert "not measured" in out            # committed faithfulness_deepeval == -1
    assert "This IPO's eval" in out         # swiggy_2024_11 has a per_ipo entry
