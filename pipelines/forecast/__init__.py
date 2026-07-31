"""
pipelines/forecast/__init__.py — the read-only listing-day-forecast cache reader.

`load_forecast(drhp_id)` is the render side's ONLY door onto a forecast: it reads
a pre-computed record from data/forecasts/<drhp_id>.json and returns a validated
ForecastRecord. This package's __init__ is deliberately IMPORT-LIGHT — it pulls in
only stdlib + the pydantic record + the catalogue allow-list. The heavy model
wrappers (XGB-quantile + calibrated intervals + the walk-forward loop) live in
sibling modules (pipelines/forecast/model.py, pipelines/forecast/walkforward.py)
that the offline pre-compute pipeline imports LAZILY — they are NEVER imported by
this __init__, so importing the loader never drags in a modelling library.

Path safety (T-05-03-PATH): load_forecast gates <drhp_id> through the catalogue
allow-list (data/catalogue_loader.is_known_drhp_id) BEFORE forming any
data/forecasts/<id>.json path — a non-allow-listed id raises ValueError and no
path is ever built (path-traversal mitigation, verbatim from the Phase 4 display
cache reader's _*_path gate).

State mapping for the render (D5-09, honesty invariant):
  - a present record -> the covered or abstain state carried on the record itself.
  - a MISSING file -> FileNotFoundError, which the render maps to the honest
    "no calibrated forecast available yet" empty-state (never a fabricated band).

ISOLATION (FCAST-02): this module references NOTHING from any modelling library
and NOTHING from the display signal it must stay computationally isolated from.
The invariant is pinned in BOTH directions by tests/unit/test_forecast_isolation.py
(an inspect.getsource substring audit): the render imports no model module, and
the predictor / this loader import no display signal.
"""
from __future__ import annotations

import json
from pathlib import Path

from agent.forecast_schema import ForecastRecord
from data.catalogue_loader import is_known_drhp_id

FORECASTS_DIR: Path = Path(__file__).resolve().parents[2] / "data" / "forecasts"


def load_forecast(drhp_id: str) -> ForecastRecord:
    """Read data/forecasts/<drhp_id>.json into a ForecastRecord.

    Args:
        drhp_id: e.g. "swiggy_2024_11". Must be a known catalogue id (T-05-03-PATH).

    Returns:
        The validated ForecastRecord (covered or first-class abstain).

    Raises:
        ValueError: if drhp_id is not in the catalogue allow-list (raised BEFORE
            any filesystem path is formed — path-traversal mitigation).
        FileNotFoundError: if no forecast cache file exists for drhp_id — the
            render's honest "no calibrated forecast available yet" empty-state.
    """
    path = _forecast_path(drhp_id)
    if not path.exists():
        raise FileNotFoundError(
            f"No forecast cache found for drhp_id={drhp_id!r} at {path}"
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    return ForecastRecord.from_dict(raw)


def _forecast_path(drhp_id: str) -> Path:
    """Form the cache path, gating drhp_id through the allow-list (T-05-03-PATH).

    Raises:
        ValueError: if drhp_id is not a known catalogue entry — the path is never
        formed for an untrusted id (path-traversal mitigation; the gate runs
        BEFORE any data/forecasts/<id>.json path is built).
    """
    if not is_known_drhp_id(drhp_id):
        raise ValueError(
            f"Unknown drhp_id={drhp_id!r}; refusing to form a cache path "
            f"(catalogue allow-list, T-05-03-PATH)."
        )
    return FORECASTS_DIR / f"{drhp_id}.json"


__all__ = ["FORECASTS_DIR", "load_forecast"]
