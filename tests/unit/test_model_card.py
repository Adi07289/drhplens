"""
tests/unit/test_model_card.py — the committed public MODEL_CARD.md assembly
(FCAST-05, Success Criterion 4).

``build_model_card(write=False)`` must return markdown ASSEMBLED FROM COMPUTED
INPUTS covering: a calibration-plot ref, a PIT-histogram ref, a four-row baselines +
Diebold–Mariano table with the P9 release-gate verdict, the `available_at`
leakage-audit section (incl. the anchor pre-open audit, D5-08), the R²-alarm status,
an n-per-sector section (D5-10), and a Known-limitations section (low R² is a
feature, D5-01) — and it must contain no secret/PII and no banned prescriptive token
(informational only).

The structural assertions use small INJECTED inputs (fast + deterministic); a couple
of thin integration checks confirm ``default_seed_inputs`` assembles from the real
committed artifacts and that the writer emits both committed files.
"""
from __future__ import annotations

import json

import pytest

from pipelines.forecast.card import (
    BANNED_ADVICE_TOKENS,
    CardInputs,
    build_model_card,
    default_seed_inputs,
)


def _fake_inputs() -> CardInputs:
    """A tiny, fully-deterministic CardInputs (no walk-forward / model fit)."""
    return CardInputs(
        training_window="2016-2025 listing years (2016–2025)",
        backtest_window="2016-2025",
        n_scored=247,
        coverage=0.783,
        mae_pts=11.4,
        per_year_rmse={"2016": 14.1, "2024": 11.9},
        r2=-0.064,
        r2_alarm=None,
        gate_passed=True,
        gate_notes=[
            "The model does not significantly outperform the following baseline(s) "
            "at p<0.05: ['predict_zero']. For a pre-apply, no-demand forecast this "
            "humble result is EXPECTED (D5-01)."
        ],
        baselines=[
            {"name": "predict_zero", "dm_stat": 0.42, "p_value": 0.67,
             "wilcoxon_p": 0.55, "n": 46, "verdict": "tie — no significant difference"},
            {"name": "global_median", "dm_stat": 0.31, "p_value": 0.76,
             "wilcoxon_p": 0.61, "n": 46, "verdict": "tie — no significant difference"},
            {"name": "trailing_12", "dm_stat": -1.10, "p_value": 0.28,
             "wilcoxon_p": 0.33, "n": 46, "verdict": "tie — no significant difference"},
            {"name": "sector_mean", "dm_stat": -0.11, "p_value": 0.91,
             "wilcoxon_p": 0.88, "n": 46, "verdict": "tie — no significant difference"},
        ],
        selected_features=["issue_size_cr", "anchor_book_cr"],
        leakage_audit=[
            {"feature": "issue_size_cr", "family": "a",
             "available_at_rule": "filing_date", "verdict": "<= T0 ✓"},
            {"feature": "anchor_book_cr", "family": "d",
             "available_at_rule": "preopen_snapshot", "verdict": "<= T0 ✓"},
        ],
        anchor_audit=[
            {"feature": "anchor_book_cr",
             "source_field": "pre-open anchor allocation book size (₹ crore)",
             "disclosure_timestamp": "T0-1",
             "verdict": "pre-open allocation only, <= T0 ✓"},
        ],
        n_per_sector={"Food delivery": 2, "Insurance": 1},
    )


def test_build_model_card_returns_markdown_from_inputs():
    md = build_model_card(inputs=_fake_inputs(), write=False)
    assert isinstance(md, str) and md.strip()
    assert md.startswith("# DRHPLens — Listing-Day Forecaster Model Card")


def test_card_embeds_calibration_and_pit_plot_refs():
    md = build_model_card(inputs=_fake_inputs(), write=False)
    assert "calibration.png" in md
    assert "pit.png" in md


def test_card_has_four_row_baselines_dm_table_with_p9_verdict():
    md = build_model_card(inputs=_fake_inputs(), write=False)
    assert "Diebold" in md
    for name in ("predict_zero", "global_median", "trailing_12", "sector_mean"):
        assert name in md
    # the P9 release-gate verdict + the honest "does not significantly outperform" note
    assert "P9 release gate: PASS" in md
    assert "does not significantly outperform" in md


def test_card_has_available_at_leakage_and_anchor_audit_sections():
    md = build_model_card(inputs=_fake_inputs(), write=False)
    assert "available_at" in md
    assert "Anchor pre-open leakage audit" in md
    assert "T0-1" in md  # the anchor pre-open disclosure timestamp (D5-08)


def test_card_has_r2_alarm_status_and_n_per_sector_and_limitations():
    md = build_model_card(inputs=_fake_inputs(), write=False)
    assert "R² leakage alarm" in md
    assert "not fired" in md  # r2 <= 0.5 honest status
    assert "N per sector" in md
    assert "Known limitations" in md
    assert "low R²" in md or "humble" in md  # D5-01: low R² is a feature


def test_card_has_no_banned_prescriptive_token():
    md = build_model_card(inputs=_fake_inputs(), write=False).lower()
    for token in BANNED_ADVICE_TOKENS:
        assert token not in md, f"model card carries banned advice token {token!r}"


def test_card_has_no_obvious_secret_or_pii():
    md = build_model_card(inputs=_fake_inputs(), write=False).lower()
    for secret in ("password", "api_key", "secret_key", "begin private key", "@gmail"):
        assert secret not in md


def test_writer_emits_markdown_and_card_data_json(tmp_path):
    md = build_model_card(inputs=_fake_inputs(), write=True, out_dir=tmp_path)
    assert (tmp_path / "MODEL_CARD.md").read_text(encoding="utf-8") == md
    data = json.loads((tmp_path / "card_data.json").read_text(encoding="utf-8"))
    # the JSON is the render-only page's plain-data source (no model import needed).
    assert data["seed"] is True
    assert len(data["baselines"]) == 4
    assert data["plot_files"]["shap"] == "shap.png"


def test_card_labels_shap_as_global_interpretability():
    """The SHAP plot is labelled global interpretability (median model on the FULL
    panel), explicitly distinct from the as-of-T0 walk-forward metrics — so no reader
    conflates the two (05-11 SHAP residual)."""
    md = build_model_card(inputs=_fake_inputs(), write=False)
    assert "shap.png" in md
    assert "global interpretability" in md
    assert "mean |SHAP value|" in md


def test_card_renders_populated_live_column_only_when_present():
    """The live card stamps each lean feature with populated_live; the render then
    shows a 'Populated live?' column (yes / no (deferred)). The seed/injected card
    (no populated_live key) omits the column entirely — seed render unchanged."""
    ci = _fake_inputs()
    ci.leakage_audit = [
        {"feature": "trailing_listing_gain", "family": "b",
         "available_at_rule": "preopen_snapshot", "verdict": "<= T0 ✓",
         "populated_live": True},
        {"feature": "issue_size_cr", "family": "a",
         "available_at_rule": "filing_date", "verdict": "<= T0 ✓",
         "populated_live": False},
    ]
    md = build_model_card(inputs=ci, write=False)
    assert "Populated live?" in md
    assert "| `trailing_listing_gain` | b | pre-open T0−1 EOD snapshot (< T0) | yes |" in md
    assert "no (deferred)" in md  # the unpopulated feature is honestly marked, not hidden

    plain = build_model_card(inputs=_fake_inputs(), write=False)
    assert "Populated live?" not in plain


@pytest.mark.slow
def test_default_seed_inputs_assembles_from_committed_artifacts():
    """Integration: the seed inputs are COMPUTED (seed forecast record metrics +
    the walk-forward release gate + the static leakage/anchor audits + real
    catalogue n-per-sector), not hand-narrated."""
    ci = default_seed_inputs()
    assert ci.seed is True
    assert ci.n_scored > 0
    assert 0.0 < ci.coverage < 1.0 and ci.coverage != 0.80  # raw held-out (P17)
    assert len(ci.baselines) == 4
    assert ci.leakage_audit and ci.anchor_audit
    assert ci.n_per_sector  # real catalogue sectors
    md = build_model_card(inputs=ci, write=False)
    assert "Diebold" in md and "calibration.png" in md
