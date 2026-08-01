"""scripts/build_eval_dashboard.py — generate the committed self-contained HTML eval
dashboard (OPS-03a) from the committed eval artifacts.

Deterministic, no network, stdlib-only (json / base64 / html / pathlib). Reads the
committed source-of-truth artifacts and writes ONE self-contained
``eval/dashboards/eval-dashboard.html``:

  - RAG      ← ``eval/reports/eval_summary.json``  (recall@k, citation, faithfulness)
  - Extraction ← hardcoded Macro F1 ``0.000`` with an inline ref to
                 ``eval/reports/2026-06-25-extraction-f1.md`` (no machine-readable
                 extraction JSON exists — RESEARCH Open-Q#2)
  - Forecast ← ``model_card/card_data.json``       (coverage, MAE, R², gate verdict)
               + base64-inlined ``model_card/calibration.png``

Honesty invariant (06.2-UI-SPEC C3 / D-03, non-negotiable):
  - ``faithfulness_deepeval == -1.0`` renders verbatim ``not measured`` — NEVER
    ``-1.0`` / ``0.00`` / a guess (the -1.0 sentinel rule is re-implemented inline below
    so this generator stays dependency-light; it does not import the app render layer);
  - the forecast section states does-not-beat-baseline honestly (``gate_passed=false``);
  - sectioned by surface (RAG / Extraction / Forecast) with the Swiggy-only per-IPO
    caveat inline;
  - mono figures only, NO red/green verdict color;
  - self-contained: a FRESH inline ``<style>`` mirroring the ``:root`` token VALUES with
    font FALLBACKS only — NO ``@import``, NO ``http(s)://`` anywhere; the plot is
    base64-inlined. Re-running over the same committed artifacts is byte-identical.

Usage:  .venv/bin/python scripts/build_eval_dashboard.py
Regen:  python scripts/build_eval_dashboard.py   (commit the produced HTML)
"""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SUMMARY = _REPO / "eval" / "reports" / "eval_summary.json"
_CARD = _REPO / "model_card" / "card_data.json"
_CALIB = _REPO / "model_card" / "calibration.png"
_OUT = _REPO / "eval" / "dashboards" / "eval-dashboard.html"

# The documented "not measured" sentinel for the LLM-judge faithfulness metric
# (faithfulness_deepeval == -1.0 is the ONLY sub-zero value — rate-limited / key unset —
# never a real 0.0). Rule re-implemented inline (kept stdlib-only, no render-layer dep).
_NOT_MEASURED = -1.0

# The Extraction Macro F1 has no committed machine-readable JSON (RESEARCH Open-Q#2) —
# hardcode the literal with an inline citation to the dated report so it is honest + pinned.
_EXTRACTION_F1 = "0.000"
_EXTRACTION_REF = "eval/reports/2026-06-25-extraction-f1.md"

_TITLE = "DRHPLens — Evaluation Dashboard"
_LIVE_DEMO = "Live demo — coming with the public deploy (Phase 6.3)."
_SWIGGY_CAVEAT = "1 IPO has a real gold set (Swiggy); others show the system-level figure."


def _faith(value) -> str:
    """Faithfulness figure: the -1.0 sentinel -> 'not measured' (never a number);
    None / NaN -> em dash; otherwise the 2-decimal value."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    if num != num:  # NaN
        return "—"
    if num == _NOT_MEASURED:
        return "not measured"
    return f"{num:.2f}"


def _num(value, nd: int = 3) -> str:
    """nd-decimal figure; None / NaN / non-numeric -> em dash. NEVER 0.00 as a guess."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    return "—" if num != num else f"{num:.{nd}f}"


def _esc(value) -> str:
    return html.escape(str(value))


def _metric_row(label: str, figure: str, note: str = "") -> str:
    """One neutral mono metric row: label · figure · optional note. Value-invariant —
    a high and a low figure render byte-identically except the digits (no verdict color)."""
    note_html = f'<span class="note">{_esc(note)}</span>' if note else ""
    return (
        '<div class="metric">'
        f'<span class="metric-label">{_esc(label)}</span>'
        f'<span class="metric-figure">{_esc(figure)}</span>'
        f"{note_html}"
        "</div>"
    )


_STYLE = """
:root {
  --bg: #16171A;
  --surface: #1E2024;
  --surface-2: #26282D;
  --border: #33363C;
  --text: #ECECEA;
  --muted: #9A9BA0;
  --accent: #E0A24E;
  --accent-link: #E6AC5C;
  --mono: 'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  --sans: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  --serif: 'IBM Plex Serif', Georgia, 'Times New Roman', serif;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 860px; margin: 0 auto; padding: 64px 24px 96px; }
.eyebrow {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent-link);
}
h1 {
  font-family: var(--serif);
  font-size: 40px;
  font-weight: 600;
  line-height: 1.12;
  margin: 12px 0 8px;
}
.subhead { color: var(--muted); font-size: 15px; margin: 0 0 20px; max-width: 62ch; }
.provenance, .caveat {
  font-family: var(--mono);
  font-size: 12.5px;
  color: var(--muted);
  margin: 6px 0;
}
.caveat { color: var(--text); }
section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 24px;
  margin-top: 24px;
  box-shadow: 0 1px 2px rgba(0,0,0,.45), 0 16px 32px -20px rgba(0,0,0,.80);
}
.section-label {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent-link);
  border-left: 3px solid var(--accent);
  padding-left: 10px;
}
h2 { font-family: var(--serif); font-size: 22px; font-weight: 600; margin: 10px 0 4px; }
.sec-sub { color: var(--muted); font-size: 14px; margin: 0 0 16px; }
.metrics { display: flex; flex-direction: column; gap: 2px; }
.metric {
  display: grid;
  grid-template-columns: 220px 130px 1fr;
  gap: 12px;
  align-items: baseline;
  padding: 8px 0;
  border-top: 1px solid var(--border);
}
.metric:first-child { border-top: none; }
.metric-label { font-family: var(--mono); font-size: 12.5px; color: var(--muted); }
.metric-figure {
  font-family: var(--mono);
  font-size: 13.5px;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
.note { font-family: var(--sans); font-size: 13px; color: var(--muted); }
.honest {
  font-size: 14px;
  color: var(--text);
  margin: 16px 0 0;
  padding: 14px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--accent);
  border-radius: 8px;
}
.honest b { font-weight: 600; }
.ref { font-family: var(--mono); font-size: 12px; color: var(--muted); }
.plot { margin: 18px 0 6px; }
.plot img {
  display: block;
  width: 100%;
  max-width: 640px;
  height: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-2);
}
.plot-cap { font-family: var(--mono); font-size: 11.5px; color: var(--muted); margin-top: 6px; }
footer {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
  font-family: var(--mono);
  font-size: 12px;
  color: var(--muted);
}
""".strip()


def _rag_section(summary: dict) -> str:
    agg = summary.get("aggregate", {}) or {}
    corpus = summary.get("corpus", {}) or {}
    n_questions = _esc(corpus.get("n_questions", "—"))
    n_scored = _esc(corpus.get("n_scored", "—"))
    ipo = _esc(corpus.get("ipo", "—"))
    judge = _esc(summary.get("judge_model", "—"))
    generated = _esc(summary.get("generated", "—"))

    rows = "".join([
        _metric_row("recall@5", _num(agg.get("recall_at_5")),
                    "coarse gold spans — a measurement floor, not a discriminating win"),
        _metric_row("recall@10", _num(agg.get("recall_at_10"))),
        _metric_row("recall@30", _num(agg.get("recall_at_30"))),
        _metric_row("citation accuracy", _num(agg.get("citation_accuracy")),
                    "saturated by the same coarse spans"),
        _metric_row("faithfulness", _faith(agg.get("faithfulness_deepeval")),
                    "judge-vs-human calibration not yet done — reported, not gated"),
    ])
    return (
        '<section id="rag">'
        '<div class="section-label">RAG</div>'
        "<h2>Retrieval-augmented Q&amp;A</h2>"
        f'<p class="sec-sub">Measured over our {n_questions}-question eval set '
        f"({n_scored} scored) &middot; {ipo}, {generated}, judge {judge}.</p>"
        f'<div class="metrics">{rows}</div>'
        '<p class="honest">recall@k and citation both saturate at '
        f'{_num(agg.get("recall_at_10"))} on <b>coarse</b> gold spans (mean ~44 pages), '
        "so they read as a regression <b>floor</b>, not a headline win. Faithfulness is "
        "<b>not measured</b> — the LLM-judge is not yet calibrated against human labels, so "
        "the honest value is a sentinel, never a fabricated number.</p>"
        "</section>"
    )


def _extraction_section() -> str:
    rows = _metric_row(
        "Macro F1 (red-flag extraction)", _EXTRACTION_F1,
        "n=7 labeled, 0 scored — not yet meaningfully evaluated",
    )
    return (
        '<section id="extraction">'
        '<div class="section-label">Extraction</div>'
        "<h2>Structured signal extraction</h2>"
        '<p class="sec-sub">Red-flag table extraction against a hand-labeled gold set.</p>'
        f'<div class="metrics">{rows}</div>'
        '<p class="honest">Macro F1 is <b>' + _EXTRACTION_F1 + "</b> on a tiny labeled "
        "set — extraction is disclosed as <b>not yet meaningfully evaluated</b>, not spun "
        'as a result. Source: <span class="ref">' + _esc(_EXTRACTION_REF) + "</span> "
        "(no machine-readable extraction JSON is committed).</p>"
        "</section>"
    )


def _forecast_section(card: dict) -> str:
    coverage = _num(card.get("coverage"))                       # 0.800
    mae = _num(card.get("mae_pts"), nd=2)                       # 0.43
    r2 = _num(card.get("r2"), nd=2)                             # -0.01
    n_scored = card.get("n_scored")
    n_scored_disp = f"{n_scored:,}" if isinstance(n_scored, int) else _esc(n_scored)
    model_version = _esc(card.get("model_version", "—"))
    backtest = _esc(card.get("backtest_window", "—"))

    beaten_by = [
        b.get("name", "")
        for b in card.get("baselines", []) or []
        if "baseline lower loss" in str(b.get("verdict", "")).lower()
    ]
    beaten_disp = " and ".join(_esc(name) for name in beaten_by) if beaten_by else "naive baselines"
    gate_passed = bool(card.get("gate_passed"))
    gate_verb = "PASSED" if gate_passed else "FAILED"

    rows = "".join([
        _metric_row("empirical coverage (80% interval)", coverage, "target 0.80 — measured, not assumed"),
        _metric_row("MAE", f"{mae} pts"),
        _metric_row("R² (out-of-sample)", r2, "near zero — expected for a pre-apply, no-demand forecast"),
        _metric_row("scored OOS IPOs", n_scored_disp, backtest),
        _metric_row("release gate (P9)", gate_verb),
    ])

    calib_b64 = base64.b64encode(_CALIB.read_bytes()).decode("ascii")
    plot = (
        '<div class="plot">'
        f'<img src="data:image/png;base64,{calib_b64}" '
        'alt="Calibration plot: predicted 80% interval coverage vs nominal">'
        '<div class="plot-cap">calibration.png &middot; committed Phase-5 diagnostic</div>'
        "</div>"
    )

    honest = (
        '<p class="honest"><b>Release gate: ' + gate_verb + "</b> — the naive baselines "
        f"<b>{beaten_disp}</b> beat the model (Diebold&ndash;Mariano p&lt;0.05 in the "
        "baselines' favour). The forecaster <b>does not beat naive baselines</b> and is not "
        "presented as a validated model: a pre-apply, no-demand forecast made at issue open "
        "(T0) cannot see book-build demand, so a near-zero out-of-sample R² is EXPECTED "
        "(D5-01) &mdash; no features, folds or tests were tuned to force a pass. On the live "
        "NSE survivorship panel only <b>trailing_listing_gain</b> was populated (the DRHP, "
        "regime and anchor sources were deferred), so this is effectively a one-feature model "
        "&mdash; which is why it is honestly humble.</p>"
    )
    return (
        '<section id="forecast">'
        '<div class="section-label">Forecast</div>'
        "<h2>Calibrated listing-day forecaster</h2>"
        f'<p class="sec-sub">Conformalized quantile regression &middot; {model_version}.</p>'
        f'<div class="metrics">{rows}</div>'
        f"{plot}"
        f"{honest}"
        "</section>"
    )


def _build_html(summary: dict, card: dict) -> str:
    judge = _esc(summary.get("judge_model", "—"))
    generated = _esc(summary.get("generated", "—"))
    model_version = _esc(card.get("model_version", "—"))
    body = (
        '<main class="wrap">'
        "<header>"
        '<div class="eyebrow">Evaluation Dashboard &middot; committed artifact</div>'
        f"<h1>{_esc(_TITLE)}</h1>"
        '<p class="subhead">The honest eval numbers for DRHPLens, read straight from the '
        "committed artifacts &mdash; sectioned by surface, with the forecaster shown honestly "
        "losing to naive baselines and faithfulness reported as not measured.</p>"
        '<p class="provenance">Rendered from committed artifacts: '
        f"eval/reports/eval_summary.json (generated {generated}, judge {judge}) &amp; "
        f"model_card/card_data.json ({model_version}).</p>"
        f'<p class="caveat">{_esc(_SWIGGY_CAVEAT)}</p>'
        "</header>"
        f"{_rag_section(summary)}"
        f"{_extraction_section()}"
        f"{_forecast_section(card)}"
        "<footer>"
        f"{_esc(_LIVE_DEMO)}<br>"
        "Regenerate: python scripts/build_eval_dashboard.py"
        "</footer>"
        "</main>"
    )
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{_esc(_TITLE)}</title>\n"
        f"<style>\n{_STYLE}\n</style>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        "</body>\n</html>\n"
    )


def main() -> None:
    for path in (_SUMMARY, _CARD, _CALIB):
        if not path.is_file():
            raise SystemExit(f"committed artifact missing: {path}")
    summary = json.loads(_SUMMARY.read_text(encoding="utf-8"))
    card = json.loads(_CARD.read_text(encoding="utf-8"))
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(_build_html(summary, card), encoding="utf-8")
    print(f"wrote {_OUT} ({_OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
