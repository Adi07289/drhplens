"""Render-only methodology artifact loader (global; no drhp_id). Reads committed JSON
only — imports NO model / sklearn / shap / diagnostics module (FCAST-02). A missing or
corrupt artifact degrades to None, never a fabricated number (honesty invariant)."""
from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_CARD = _REPO / "model_card" / "card_data.json"
_PLOTS = _REPO / "model_card" / "card_plots.json"
_EVAL_SUMMARY = _REPO / "eval" / "reports" / "eval_summary.json"
_PANEL_SANITY = _REPO / "data" / "historical" / "panel_sanity.json"


def _load(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None


def load_methodology() -> dict:
    return {
        "card": _load(_CARD),
        "plots": _load(_PLOTS),
        "eval": _load(_EVAL_SUMMARY),
        "panel_sanity": _load(_PANEL_SANITY),
    }
