"""
pipelines/forecast/card.py — the committed public MODEL CARD writer (FCAST-05,
Success Criterion 4).

``build_model_card`` mirrors ``pipelines.historical.build._write_readme``'s posture
— assemble a committed markdown ENTIRELY from COMPUTED inputs, never hand-narrated
numbers. It stitches together:

  * the training / backtest window + N (the seed ``data/forecasts`` record's
    ``global_metrics`` block — D5-12),
  * the LEAN feature list (``pipelines.features.select.SELECTED_FEATURES``, D5-07)
    each with its ``available_at`` verdict (``pipelines.features.build.leakage_audit``)
    plus the explicit anchor pre-open audit (``anchor_leakage_audit``, D5-08),
  * the four baselines + the Diebold–Mariano table with the P9 release-gate verdict
    (``pipelines.forecast.baselines.release_gate``) + the paired-Wilcoxon robustness
    + the A7 cross-sectional-DM caveat,
  * the empirical coverage / MAE / per-year RMSE (the real held-out numbers, P17),
  * the R²>0.5 leakage-alarm status (a high R² would flag a T0-violating feature),
  * embedded references to the committed ``calibration.png`` / ``pit.png`` /
    ``shap.png`` (``pipelines.forecast.diagnostics``, FCAST-03),
  * the n-per-sector thinness report (``pipelines.features.build.pool_sectors``, D5-10),
  * a plain "Known limitations" section (a pre-apply, no-demand forecast is EXPECTED
    to be humble — a low R² is a feature, D5-01; R²>0.5 would flag leakage).

CODE-NOW-DEFER (Success Criterion 4 seam)
-----------------------------------------
The committed card + PNGs are assembled from the CURRENT seed/fixture artifacts so
``/methodology`` renders OFFLINE today; the REAL card + PNGs regenerate from the
live walk-forward at the 05-11 checkpoint. The seed provenance is stated EXPLICITLY
in a banner at the top of the card (``seed / not-yet-regenerated``) — seed numbers
are NEVER presented as if they were the live backtest.

Two committed outputs (``write=True``):
  * ``model_card/MODEL_CARD.md`` — the human-readable public card.
  * ``model_card/card_data.json`` — the SAME assembled content as plain data, so the
    render-only ``/methodology`` page can build its tables WITHOUT importing any
    model/training/explainability module (the T-05-10-ISO isolation invariant).

Honesty / safety
----------------
The card is assembled from AGGREGATE metrics + audit records only — no raw DRHP
text, no credential, no PII (T-05-10-PII). It is informational-only: it carries no
prescriptive advice token (no buy / sell / subscribe / avoid / target / recommend /
fair-value language) — the numbers describe the forecaster's honesty, they never
tell anyone what to do (T-05-10-HONEST).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Repo-root committed artifact directory (the /methodology render + this writer share it).
MODEL_CARD_DIR: Path = Path(__file__).resolve().parents[2] / "model_card"

# The committed PNG filenames (FCAST-03) the card embeds and the page renders.
PLOT_FILES: dict[str, str] = {
    "calibration": "calibration.png",
    "pit": "pit.png",
    "shap": "shap.png",
}

MODEL_VERSION_SEED: str = "cqr-xgb-seed-2026.07"
MODEL_VERSION_LIVE: str = "cqr-xgb-live-2026.07"

# Prescriptive advice tokens the card must NEVER carry (informational only). These
# are the ADVICE verbs/phrases — NOT the technical stems — so a leakage-exclusion
# term stays describable ("post-open book-build demand" never appears as advice).
BANNED_ADVICE_TOKENS: tuple[str, ...] = (
    "buy",
    "sell",
    "subscribe",
    "avoid",
    "target",
    "recommend",
    "fair value",
    "overvalued",
    "undervalued",
    "accumulate",
)

# The Known-limitations section (D5-01 humility; A7/A8 caveats; seed provenance).
_LIMITATIONS: tuple[tuple[str, str], ...] = (
    (
        "A humble R² is the honest result",
        "This is a pre-apply, no-demand forecast made at issue open (T0). It cannot "
        "see book-build demand, so a low out-of-sample R² is EXPECTED — a feature, "
        "not a bug (D5-01). A high R² (> 0.5) would instead flag a T0-violating "
        "feature leaking the future, so it is wired as a release-gate alarm.",
    ),
    (
        "Coverage is measured, not assumed",
        "The 80% interval coverage is the REAL held-out number over IPOs the model "
        "never trained on. It can land below or above 0.80 — the card shows the "
        "measured value, never a rounded-to-0.80 fiction (P17).",
    ),
    (
        "The PIT curve is grid-derived",
        "The reliability/PIT diagnostic fits a fine 0.05..0.95 quantile grid PURELY "
        "for the plot; the production interval stays the 0.1 / 0.5 / 0.9 band. The "
        "PIT is labelled grid-derived wherever it is shown (A8).",
    ),
    (
        "The Diebold–Mariano test is cross-sectional",
        "The four baselines are compared under the identical as-of-T0 protocol, but "
        "the loss differential is cross-sectional across IPOs rather than a single "
        "time series — read the DM p-values with that caveat (A7). A paired Wilcoxon "
        "signed-rank p is reported alongside as a distribution-free cross-check.",
    ),
    (
        "Seed provenance — regenerates at the live build",
        "These numbers are assembled from the current seed/fixture artifacts so the "
        "card and its plots render offline today. They regenerate from the live "
        "walk-forward over the real survivorship panel at the 05-11 checkpoint.",
    ),
)


@dataclass
class CardInputs:
    """Every COMPUTED input the model card is assembled from (no hand-narration)."""

    training_window: str
    backtest_window: str
    n_scored: int
    coverage: float
    mae_pts: float
    per_year_rmse: dict[str, float]
    r2: float
    r2_alarm: str | None
    gate_passed: bool
    gate_notes: list[str]
    baselines: list[dict]  # {name, dm_stat, p_value, wilcoxon_p, verdict, n}
    selected_features: list[str]
    leakage_audit: list[dict]  # {feature, family, available_at_rule, verdict}
    anchor_audit: list[dict]  # {feature, source_field, disclosure_timestamp, verdict}
    n_per_sector: dict[str, int]
    limitations: list[dict] = field(  # {title, body}
        default_factory=lambda: [{"title": t, "body": b} for t, b in _LIMITATIONS]
    )
    plot_files: dict[str, str] = field(default_factory=lambda: dict(PLOT_FILES))
    model_version: str = MODEL_VERSION_SEED
    seed: bool = True


# ---------------------------------------------------------------------------
# Verdict helpers (plain-data — mirror the release_gate posture)
# ---------------------------------------------------------------------------
def _baseline_verdict(entry: dict) -> str:
    """A plain per-baseline DM verdict string (no advice, no colour)."""
    if entry.get("baseline_beats_model_sig"):
        return "baseline lower loss (DM p<0.05)"
    if entry.get("model_beats_sig"):
        return "model lower loss (DM p<0.05)"
    return "tie — no significant difference"


def _fmt(value: float, nd: int = 3) -> str:
    """Format a float honestly; NaN renders as an em-dash (never a fabricated 0)."""
    if value is None or value != value:  # None or NaN
        return "—"
    return f"{value:.{nd}f}"


# ---------------------------------------------------------------------------
# Seed inputs (CODE-NOW-DEFER) — assembled from the current committed artifacts
# ---------------------------------------------------------------------------
def _seed_release_verdict() -> dict:
    """Run the walk-forward + P9 release gate ONCE on the offline synthetic fixture.

    This is the seed DM table + gate verdict (CODE-NOW-DEFER); the live-panel run
    at 05-11 replaces it. Imported lazily so this module stays import-light.
    """
    from pipelines.forecast.baselines import release_gate
    from pipelines.forecast.walkforward import walk_forward
    from tests.unit.fixtures.forecast_fixtures import (
        synthetic_features,
        synthetic_panel,
    )

    panel = synthetic_panel(n=90)
    X = synthetic_features(panel)
    oos = walk_forward(
        panel, X, min_train=30, cal_frac=0.25, params={"n_estimators": 30, "max_depth": 2}
    )
    return release_gate(oos, panel)


def _seed_n_per_sector() -> dict[str, int]:
    """The D5-10 n-per-sector thinness report from the real catalogue sectors."""
    import pandas as pd

    from data.catalogue_loader import load_catalogue
    from pipelines.features.build import pool_sectors

    sectors = [getattr(ipo, "sector", None) for ipo in load_catalogue()]
    frame = pd.DataFrame({"sector": sectors})
    _pooled, n_per_sector = pool_sectors(frame, min_n=30)
    return dict(n_per_sector)


def _seed_metrics() -> dict:
    """The seed global-metrics block from the committed forecast record (D5-12)."""
    from pipelines.forecast import load_forecast

    rec = load_forecast("swiggy_2024_11")
    m = rec.metrics
    return {
        "coverage": float(m.coverage_empirical),
        "mae_pts": float(m.mae_pts),
        "n": int(m.n),
        "backtest_window": m.backtest_window,
        "per_year_rmse": {str(k): float(v) for k, v in m.per_year_rmse.items()},
    }


def default_seed_inputs() -> CardInputs:
    """Assemble the seed ``CardInputs`` from the current committed artifacts."""
    from pipelines.features.build import anchor_leakage_audit, leakage_audit
    from pipelines.features.select import SELECTED_FEATURES

    metrics = _seed_metrics()
    verdict = _seed_release_verdict()

    baselines: list[dict] = []
    for name, entry in verdict["per_baseline"].items():
        baselines.append(
            {
                "name": name,
                "dm_stat": entry["dm_stat"],
                "p_value": entry["p_value"],
                "wilcoxon_p": entry["wilcoxon_p"],
                "n": entry["n"],
                "verdict": _baseline_verdict(entry),
            }
        )

    # Restrict the audit to the LEAN feature list (the production set), in that order.
    audit_by_feature = {row["feature"]: row for row in leakage_audit()}
    lean_audit = [
        audit_by_feature[f] for f in SELECTED_FEATURES if f in audit_by_feature
    ]

    years = metrics["per_year_rmse"]
    training_window = (
        f"{metrics['backtest_window']} listing years "
        f"({min(years) if years else '?'}–{max(years) if years else '?'})"
    )

    return CardInputs(
        training_window=training_window,
        backtest_window=metrics["backtest_window"],
        n_scored=metrics["n"],
        coverage=metrics["coverage"],
        mae_pts=metrics["mae_pts"],
        per_year_rmse=metrics["per_year_rmse"],
        r2=float(verdict["r2"]),
        r2_alarm=verdict["r2_alarm"],
        gate_passed=bool(verdict["passed"]),
        gate_notes=list(verdict["notes"]),
        baselines=baselines,
        selected_features=list(SELECTED_FEATURES),
        leakage_audit=lean_audit,
        anchor_audit=anchor_leakage_audit(),
        n_per_sector=_seed_n_per_sector(),
    )


# ---------------------------------------------------------------------------
# Markdown assembly
# ---------------------------------------------------------------------------
def _available_at_friendly(rule: str) -> str:
    if rule == "filing_date":
        return "DRHP/RHP filing date (≤ T0)"
    if rule == "preopen_snapshot":
        return "pre-open T0−1 EOD snapshot (< T0)"
    return rule


def _render_markdown(ci: CardInputs) -> str:
    lines: list[str] = []
    a = lines.append

    a("# DRHPLens — Listing-Day Forecaster Model Card")
    a("")
    a(f"**Model version:** `{ci.model_version}`")
    a("")
    if ci.seed:
        a("> ⚠️ **SEED / NOT-YET-REGENERATED (CODE-NOW-DEFER).** Every number below is")
        a("> assembled from the current seed/fixture artifacts so this card and its")
        a("> plots render offline today. They are NOT the live backtest — they")
        a("> regenerate from the real walk-forward over the survivorship panel at the")
        a("> 05-11 checkpoint. Seed numbers are never presented as live results.")
        a("")

    a("## What this model is")
    a("")
    a(
        "A calibrated 80% prediction INTERVAL for the listing-day return of an Indian "
        "mainboard IPO, made at issue open (T0) — a range, not a call. It is "
        "informational and educational only, not advice. The grey-market premium is "
        "shown for context but NEVER feeds the model (GMP-free, FCAST-02)."
    )
    a("")

    # ── Data window + N ───────────────────────────────────────────────────────
    a("## Training + backtest window")
    a("")
    a(f"- **Training / backtest window:** {ci.training_window}")
    a(f"- **Scored (held-out, non-abstain) IPOs:** {ci.n_scored}")
    a(
        "- **Protocol:** expanding-window, as-of-T0 walk-forward — for each IPO the "
        "train + calibration pool is STRICTLY the IPOs that listed before its issue "
        "date, so no future IPO can leak into training (P4/P6)."
    )
    a("")

    # ── Lean feature list + available_at ─────────────────────────────────────
    a("## Lean feature list (available_at ≤ T0)")
    a("")
    a(
        "The wide four-family candidate pool is curated to a lean production set "
        "(D5-07); every feature is disclosed at or before issue open, verified by the "
        "`available_at ≤ T0` leakage gate (FCAST-02)."
    )
    a("")
    # "Populated live?" is shown only when the inputs carry it (the live card) — it
    # states, per feature, whether the column actually held a value on the live
    # panel, so the schema-vs-populated gap is explicit (D5-11 honesty).
    has_pop = any("populated_live" in row for row in ci.leakage_audit)
    if has_pop:
        a(
            "The `Populated live?` column states whether each feature actually carried "
            "a value on the live survivorship panel — a feature whose source was "
            "deferred at the 05-11 build is honestly marked `no (deferred)`, not hidden."
        )
        a("")
        a("| Feature | Family | available_at | Populated live? | Verdict |")
        a("|---|---|---|---|---|")
        for row in ci.leakage_audit:
            pop = "yes" if row.get("populated_live") else "no (deferred)"
            a(
                f"| `{row['feature']}` | {row.get('family', '?')} | "
                f"{_available_at_friendly(row['available_at_rule'])} | {pop} | "
                f"{row['verdict']} |"
            )
    else:
        a("| Feature | Family | available_at | Verdict |")
        a("|---|---|---|---|")
        for row in ci.leakage_audit:
            a(
                f"| `{row['feature']}` | {row.get('family', '?')} | "
                f"{_available_at_friendly(row['available_at_rule'])} | {row['verdict']} |"
            )
    a("")

    # ── Anchor pre-open audit (D5-08) ─────────────────────────────────────────
    a("## Anchor pre-open leakage audit (D5-08)")
    a("")
    a(
        "Anchor-investor demand is the ONE legitimate T0 demand proxy, but it is "
        "borderline: only the PRE-OPEN anchor allocation (disclosed the day before "
        "issue open, T0−1) may be read. Post-open book-build demand (QIB / NII / RII, "
        "which closes AFTER issue open) can never be a feature."
    )
    a("")
    a("| Anchor feature | Pre-open source | Disclosed | Verdict |")
    a("|---|---|---|---|")
    for row in ci.anchor_audit:
        a(
            f"| `{row['feature']}` | {row['source_field']} | "
            f"{row['disclosure_timestamp']} | {row['verdict']} |"
        )
    a("")

    # ── Four baselines + Diebold–Mariano + P9 gate ───────────────────────────
    a("## Baselines + Diebold–Mariano test (P9 release gate)")
    a("")
    a(
        "The model is compared against four naive baselines under the IDENTICAL "
        "as-of-T0 protocol — it is never given an easier evaluation. A Diebold–"
        "Mariano test (Harvey small-sample correction) on the MAE-loss differential "
        "gives the significance; a paired Wilcoxon signed-rank p is the "
        "distribution-free cross-check (A7)."
    )
    a("")
    a("| Baseline | DM stat | p-value | Wilcoxon p | n | Verdict |")
    a("|---|---|---|---|---|---|")
    for b in ci.baselines:
        a(
            f"| `{b['name']}` | {_fmt(b['dm_stat'])} | {_fmt(b['p_value'])} | "
            f"{_fmt(b['wilcoxon_p'])} | {b['n']} | {b['verdict']} |"
        )
    a("")
    gate_word = "PASS" if ci.gate_passed else "FAIL"
    a(f"**P9 release gate: {gate_word}.**")
    a("")
    for note in ci.gate_notes:
        a(f"> {note}")
        a("")

    # ── Calibration + PIT + SHAP plots ───────────────────────────────────────
    a("## Calibration, PIT + feature importance")
    a("")
    a(f"![Reliability diagram — nominal vs empirical coverage]({ci.plot_files['calibration']})")
    a("")
    a(f"![PIT histogram — grid-derived, flat means calibrated]({ci.plot_files['pit']})")
    a("")
    a(f"![SHAP feature importance over the lean feature set]({ci.plot_files['shap']})")
    a("")
    a(
        "*Feature importance is the mean |SHAP value| of the median quantile model fit "
        "on the FULL panel (global interpretability) — distinct from the as-of-T0 "
        "walk-forward that produced the held-out metrics above. A feature that was "
        "never populated on the panel contributes zero.*"
    )
    a("")

    # ── Held-out metrics (P17) ────────────────────────────────────────────────
    a("## Held-out calibration metrics")
    a("")
    a(f"- **80% interval coverage (empirical, held-out):** {_fmt(ci.coverage)}")
    a(f"- **Mean absolute error:** {_fmt(ci.mae_pts, 2)} points")
    a("")
    a("| Listing year | RMSE (points) |")
    a("|---|---|")
    for year in sorted(ci.per_year_rmse):
        a(f"| {year} | {_fmt(ci.per_year_rmse[year], 2)} |")
    a("")

    # ── R²>0.5 leakage alarm status ──────────────────────────────────────────
    a("## R² leakage alarm")
    a("")
    if ci.r2_alarm:
        a(f"- **Status: FIRED.** {ci.r2_alarm}")
    else:
        a(
            f"- **Status: not fired.** Out-of-sample median R² = {_fmt(ci.r2)} ≤ 0.5. "
            "A humble R² is expected for a pre-apply, no-demand model (D5-01); a value "
            "above 0.5 would flag a T0-violating feature and fail the release gate."
        )
    a("")

    # ── N-per-sector thinness report (D5-10) ─────────────────────────────────
    a("## N per sector (D5-10)")
    a("")
    a(
        "Sectors with fewer than 30 IPOs are pooled into `Other` so a thin sector "
        "never becomes a noise-prone single-value slice; the ORIGINAL per-sector "
        "counts are kept below so the thinness stays visible."
    )
    a("")
    a("| Sector | N |")
    a("|---|---|")
    for sector in sorted(ci.n_per_sector):
        a(f"| {sector} | {ci.n_per_sector[sector]} |")
    a("")

    # ── Known limitations ─────────────────────────────────────────────────────
    a("## Known limitations")
    a("")
    for lim in ci.limitations:
        a(f"- **{lim['title']}.** {lim['body']}")
    a("")

    a("---")
    a("")
    a("*Informational only — not advice. DRHPLens.*")
    a("")
    return "\n".join(lines)


def _assert_clean(markdown: str) -> None:
    """Guard: the card carries no prescriptive advice token and no obvious secret."""
    low = markdown.lower()
    for token in BANNED_ADVICE_TOKENS:
        if token in low:
            raise ValueError(
                f"model card carries a banned prescriptive token {token!r} — the card "
                f"is informational only (no advice)."
            )
    for secret in ("password", "api_key", "api-key", "secret_key", "begin private key"):
        if secret in low:
            raise ValueError(f"model card appears to leak a secret ({secret!r}).")


def build_model_card(
    *,
    inputs: CardInputs | None = None,
    write: bool = True,
    out_dir: Path | None = None,
) -> str:
    """Assemble the committed public MODEL_CARD.md from computed inputs (FCAST-05).

    Args:
        inputs: the computed ``CardInputs`` (metrics + release verdict + audits +
            lean features + n-per-sector). When ``None`` the seed inputs are
            assembled from the current committed artifacts (CODE-NOW-DEFER).
        write: when True, write ``MODEL_CARD.md`` + ``card_data.json`` under
            ``out_dir`` (the render-only page reads the JSON, no model import).
        out_dir: the committed artifact directory (default the repo ``model_card/``).

    Returns:
        The assembled MODEL_CARD.md markdown string.
    """
    ci = inputs if inputs is not None else default_seed_inputs()
    markdown = _render_markdown(ci)
    _assert_clean(markdown)

    if write:
        target = Path(out_dir) if out_dir is not None else MODEL_CARD_DIR
        target.mkdir(parents=True, exist_ok=True)
        (target / "MODEL_CARD.md").write_text(markdown, encoding="utf-8")
        (target / "card_data.json").write_text(
            json.dumps(asdict(ci), indent=2, sort_keys=False), encoding="utf-8"
        )
    return markdown


__all__ = [
    "MODEL_CARD_DIR",
    "PLOT_FILES",
    "BANNED_ADVICE_TOKENS",
    "CardInputs",
    "default_seed_inputs",
    "build_model_card",
]
