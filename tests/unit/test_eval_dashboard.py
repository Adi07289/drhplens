"""Unit tests — the committed self-contained HTML eval dashboard (OPS-03a).

Builds ``eval/dashboards/eval-dashboard.html`` via the generator
(``scripts/build_eval_dashboard.py``) and pins it with a build + numeric-parity +
self-contained + honesty test so the committed HTML can NEVER silently drift from
the committed metrics.

Each headline number is re-derived INDEPENDENTLY from the committed source-of-truth
JSON (``eval/reports/eval_summary.json`` for RAG, ``model_card/card_data.json`` for
forecast) and asserted verbatim — one drifted figure cannot hide behind another.

Honesty invariants pinned here (06.2-UI-SPEC C3 / D-03):
  - self-contained: zero external ``http(s)://`` asset URLs; no ``@import`` (Pitfall 3);
  - faithfulness renders verbatim ``not measured`` — never ``-1.0`` / a fabricated ``0.00``;
  - the forecast section states does-not-beat-baseline honestly (``gate_passed=false``);
  - the calibration plot is base64-inlined (``data:image/png;base64,``);
  - sectioned by surface — RAG / Extraction / Forecast — with the Swiggy-only per-IPO
    caveat inline;
  - mono figures only, NO red/green verdict color;
  - deterministic: building twice yields a byte-identical file.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "build_eval_dashboard.py"
_OUT = _REPO / "eval" / "dashboards" / "eval-dashboard.html"
_SUMMARY = _REPO / "eval" / "reports" / "eval_summary.json"
_CARD = _REPO / "model_card" / "card_data.json"
_CALIB = _REPO / "model_card" / "calibration.png"
_F1_REPORT_REF = "eval/reports/2026-06-25-extraction-f1.md"


def _build() -> bytes:
    """Run the generator (from the repo root) and return the produced bytes.

    Uses ``check=True`` so a missing generator (Task 2 not yet done) surfaces as the
    intended RED — the build step fails before any assertion runs.
    """
    subprocess.run([sys.executable, str(_SCRIPT)], check=True, cwd=str(_REPO))
    return _OUT.read_bytes()


@pytest.fixture(scope="module")
def html() -> str:
    return _build().decode("utf-8")


@pytest.fixture(scope="module")
def summary() -> dict:
    return json.loads(_SUMMARY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def card() -> dict:
    return json.loads(_CARD.read_text(encoding="utf-8"))


# ── (1) self-contained — zero external asset URLs, no @import ─────────────────
def test_self_contained_no_external_urls(html):
    assert not re.search(r'(src|href)\s*=\s*["\']https?://', html), (
        "dashboard references an external asset URL — must be self-contained"
    )
    assert not re.search(r"url\(\s*['\"]?https?://", html), (
        "dashboard CSS references an external url(https://…) — must be self-contained"
    )
    assert "@import" not in html, (
        "dashboard must not use @import (the app CSS's Google-Fonts @import breaks "
        "self-containment — author fresh inline <style> with font fallbacks only)"
    )
    # No occurrence of an http(s):// scheme anywhere in the committed artifact.
    assert "http://" not in html and "https://" not in html


# ── (2) RAG parity — re-derived from eval_summary.json, asserted independently ─
def test_rag_parity_recall_and_citation(html, summary):
    agg = summary["aggregate"]
    # citation + recall@{5,10,30} are the committed aggregate — each 3-decimal figure
    # is re-derived from the JSON, not a hardcoded copy, so a metric change forces regen.
    assert f'{agg["citation_accuracy"]:.3f}' in html   # 1.000
    assert f'{agg["recall_at_5"]:.3f}' in html
    assert f'{agg["recall_at_10"]:.3f}' in html
    assert f'{agg["recall_at_30"]:.3f}' in html
    # Provenance is present (judge model named).
    assert str(summary["judge_model"]) in html


# ── (3) faithfulness — verbatim "not measured", never -1.0 / fabricated 0.00 ──
def test_faithfulness_sentinel_verbatim(html, summary):
    assert summary["aggregate"]["faithfulness_deepeval"] == -1.0  # the pinned sentinel
    assert "not measured" in html
    assert "-1.0" not in html          # the raw sentinel never leaks
    assert "-1.00" not in html
    # No fabricated 0.00 faithfulness anywhere — the honest 0.000 extraction F1 is allowed.
    assert "0.00" not in html.replace("0.000", "")


# ── (4) forecast parity — coverage + honest gate-fail framing ────────────────
def test_forecast_parity_and_honest_gate(html, card):
    assert f'{card["coverage"]:.3f}' in html          # 0.800 (from 0.8004)
    assert f'{card["mae_pts"]:.2f}' in html            # 0.43
    assert f'{card["n_scored"]:,}' in html             # 1,132
    # The gate honestly FAILED — the dashboard must say so, and name the winning baselines.
    assert card["gate_passed"] is False
    low = html.lower()
    assert "release gate" in low
    assert ("does not beat" in low) or ("do not beat" in low) or ("does not outperform" in low)
    assert "global_median" in html and "trailing_12" in html


# ── (5) calibration plot base64-inlined (re-derived from the committed PNG) ───
def test_calibration_png_base64_inlined(html):
    assert "data:image/png;base64," in html
    encoded = base64.b64encode(_CALIB.read_bytes()).decode("ascii")
    # The ACTUAL committed image bytes are inlined (not a placeholder) — strong parity.
    assert encoded in html


# ── (6) extraction F1 hardcoded literal + inline ref ─────────────────────────
def test_extraction_f1_literal_with_ref(html):
    assert "0.000" in html                     # the hardcoded Macro F1 literal
    assert _F1_REPORT_REF in html              # inline citation (no machine-readable JSON)


# ── (7) sectioned by surface (D-03) + Swiggy-only per-IPO caveat inline ───────
def test_sectioned_by_surface_and_swiggy_caveat(html):
    # The three surface section labels must all be present.
    assert re.search(r"\bRAG\b", html)
    assert "Extraction" in html
    assert "Forecast" in html
    # The honest Swiggy-only per-IPO caveat is rendered inline.
    assert "Swiggy" in html
    assert "gold set" in html


# ── (8) honesty-color — mono figures only, no red/green verdict color ────────
def test_no_red_green_verdict_color(html):
    low = html.lower()
    assert not re.search(r"color:\s*red", low)
    assert not re.search(r"color:\s*green", low)
    for hexc in ("#e5484d", "#d33682", "#2ecc71", "#3fb950"):
        assert hexc not in low, f"forbidden red/green verdict hex {hexc} present"


# ── (9) title + live-demo placeholder copy (UI-SPEC copywriting contract) ─────
def test_title_and_live_demo_placeholder(html):
    assert "DRHPLens — Evaluation Dashboard" in html
    assert "Live demo — coming with the public deploy (Phase 6.3)." in html


# ── (10) deterministic — building twice yields a byte-identical file ─────────
def test_deterministic_rebuild():
    first = _build()
    second = _build()
    assert first == second, "generator output is not byte-identical on rebuild"
