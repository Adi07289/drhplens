"""
scripts/regenerate_model_card.py — the reproducible model-card regeneration
(05-11 SHAP residual; the runbook's ``card build``).

The live model card (``model_card/MODEL_CARD.md`` + ``card_data.json``) was first
produced by an ad-hoc supervised run at the 05-11 live build, which regenerated
``calibration.png`` / ``pit.png`` from the committed held-out frame but LEFT
``shap.png`` as the seed fixture (SHAP needs a FITTED model, not just the OOS
frame). This script closes that gap deterministically:

  1. Fit the ONE production median quantile model on the full committed live panel
     (``pipelines.forecast.interpret.fit_median_model``) and regenerate ``shap.png``
     from REAL SHAP values (global interpretability — see the card caption).
  2. Reload the committed live ``card_data.json`` (the source of truth for every
     narrative string + the live held-out numbers), apply exactly two disclosures:
       - stamp each lean feature with ``populated_live`` (from the real panel), and
       - swap the "SHAP plot pending real regeneration" limitation for the honest
         "one-feature model" limitation (only ``trailing_listing_gain`` is populated
         on the live panel — which is WHY the model is humble / fails P9).
  3. Re-render BOTH files from ONE ``CardInputs`` via ``build_model_card`` so the
     markdown and the JSON can never drift apart.

Re-runnable and deterministic: running it again over the same committed artifacts
reproduces the same card + plot. It reads only committed data (no network, no crawl)
and is a MODEL-side tool (never imported by the render side; FCAST-02).

Usage:  .venv/bin/python -m scripts.regenerate_model_card
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pipelines.forecast.card import (
    MODEL_CARD_DIR,
    CardInputs,
    build_model_card,
)
from pipelines.forecast.diagnostics import shap_summary
from pipelines.forecast.interpret import feature_population, fit_median_model

_REPO = Path(__file__).resolve().parents[1]
_PANEL = _REPO / "data" / "historical" / "ipo_panel.parquet"
_CARD_JSON = MODEL_CARD_DIR / "card_data.json"

# The seed caveat this script retires (SHAP is now regenerated for real).
_RETIRED_LIMITATION_TITLE = "SHAP plot pending real regeneration"

# The honest one-feature disclosure (the SHAP plot's real story on the live panel).
_ONE_FEATURE_LIMITATION = {
    "title": "Live panel — effectively a one-feature model",
    "body": (
        "On the live NSE survivorship panel only `trailing_listing_gain` (a regime "
        "feature derived from prior listings) was populated. The DRHP-structure "
        "(families a / c), the market-regime VIX / nifty features (b) and the anchor "
        "book (d) all require the DRHP caches and the market / anchor fetchers that "
        "were deferred at the 05-11 live build, so every other lean column was "
        "all-NaN. The live model is therefore effectively a single-feature model — "
        "which is WHY it is humble and does not beat the naive baselines (D5-01). The "
        "SHAP plot above shows the one populated feature carrying all the attribution; "
        "populating the deferred sources is the path to a model with genuine signal."
    ),
}


def main() -> None:
    if not _PANEL.is_file():
        raise SystemExit(f"live panel missing: {_PANEL} — run the 05-11 crawl first.")
    if not _CARD_JSON.is_file():
        raise SystemExit(f"committed card_data.json missing: {_CARD_JSON}")

    panel = pd.read_parquet(_PANEL)

    # 1) REAL SHAP — fit the production median model on the full panel, explain it.
    median_model, x_fit = fit_median_model(panel)
    shap_path = shap_summary(
        median_model, x_fit, MODEL_CARD_DIR / "shap.png", feature_names=list(x_fit.columns)
    )
    if not (shap_path.exists() and shap_path.stat().st_size > 0):
        raise SystemExit("shap.png was not written")

    # 2) Reload the committed live card and apply the two honest disclosures.
    data = json.loads(_CARD_JSON.read_text(encoding="utf-8"))
    populated = feature_population(panel)
    for row in data["leakage_audit"]:
        row["populated_live"] = bool(populated.get(row["feature"], False))

    limitations = [
        lim for lim in data["limitations"]
        if lim.get("title") != _RETIRED_LIMITATION_TITLE
    ]
    if all(lim["title"] != _ONE_FEATURE_LIMITATION["title"] for lim in limitations):
        limitations.append(_ONE_FEATURE_LIMITATION)
    data["limitations"] = limitations

    # 3) Re-render BOTH files from one CardInputs (markdown + JSON stay in sync).
    ci = CardInputs(**data)
    build_model_card(inputs=ci, write=True)

    n_pop = sum(1 for v in populated.values() if v)
    print(f"regenerated model card: shap.png ({shap_path.stat().st_size} bytes), "
          f"{n_pop}/{len(populated)} lean features populated live, "
          f"{len(limitations)} limitations, gate_passed={data['gate_passed']}")


if __name__ == "__main__":
    main()
