"""
agent/tools/query_forecast.py — the read-only forecast tool node + GMP fold (D-01, D-04).

A deterministic `SupervisorState`-in / `SupervisorState`-out function in the shape
of `agent/nodes/retrieve.run`. It READS the committed calibrated forecast band
for the single in-scope IPO (`data/forecasts/<drhp_id>.json`) via the existing
`pipelines.forecast.load_forecast` loader and returns the already-validated
`ForecastRecord` as a provenance-tagged `tool_results` entry. It calls NO LLM and
burns NO quota — storage is the integration bus (D-01).

GMP fold (D-04) — read-only, DISPLAY-ONLY, NEVER a model feature (P4/GMP-01/02):
when the IPO has a reported grey-market premium, the tool ADDITIONALLY surfaces a
`gmp_gap` block carrying the GMP quotes/spread, the GMP-free model band it sits
NEXT TO (for the "GMP says X; the GMP-free model says Y" honesty framing), and the
mandatory display-only caveat (the single-source `ui.copy.GMP_CAVEAT`, which itself
states GMP is "never used in any forecast"). The gap is computed at READ/DISPLAY
time only. GMP is NEVER passed into any model computation, NEVER color-coded, and
when the record is ABSENT (`is_absent`) the fold is simply OMITTED — no fabricated
gap. This module imports NO modelling library; the isolation invariant is pinned by
tests/unit/test_tools_isolation.py.

Security (T-6.3-PATH): `drhp_id` is gated through the catalogue allow-list
(`data.catalogue_loader.is_known_drhp_id`) BEFORE any `data/*` path is formed (for
BOTH the forecast and the GMP read) — a non-allow-listed / traversal id is rejected
(ValueError) before any read. `load_forecast` re-applies the same gate.

Honesty (P14): a MISSING forecast record (FileNotFoundError) yields an honest
`abstain=True, record=None` — never a fabricated band. A record-native abstain
(insufficient calibration history) surfaces its own `is_abstain` on the record.
"""
from __future__ import annotations

import json
from pathlib import Path

from agent.gmp_schema import GmpRecord
from agent.supervisor_state import SupervisorState
from data.catalogue_loader import is_known_drhp_id
from pipelines.forecast import load_forecast
from ui.copy import GMP_CAVEAT

TOOL_NAME = "query_forecast"

# data/gmp/<drhp_id>.json lives at the repo root; parents[2] == repo root
# (agent/tools/query_forecast.py -> tools -> agent -> repo root).
_GMP_DIR: Path = Path(__file__).resolve().parents[2] / "data" / "gmp"


def run(state: SupervisorState) -> SupervisorState:
    """Load the committed forecast for state["drhp_id"] + fold GMP read-only (D-04).

    Appends one provenance-tagged entry to `tool_results` (with an optional
    display-only `gmp_gap` block), pops itself from `tool_plan`, and increments
    `tool_calls` by exactly 1 — returning via the `{**state, ...}` overwrite
    convention every existing node uses.

    Raises:
        ValueError: if `drhp_id` is not in the catalogue allow-list — rejected
            BEFORE any `data/*` read (path-traversal mitigation, T-6.3-PATH).
    """
    drhp_id = state["drhp_id"]

    # Path-safety allow-list gate (T-6.3-PATH) runs FIRST — before any data/* path
    # (guards BOTH the forecast read and the GMP read below).
    if not is_known_drhp_id(drhp_id):
        raise ValueError(
            f"Unknown drhp_id={drhp_id!r}; refusing to read the forecast for a "
            f"non-allow-listed id (catalogue allow-list, T-6.3-PATH)."
        )

    try:
        record = load_forecast(drhp_id)
        result = {
            "tool": TOOL_NAME,
            "record": record.model_dump(),
            "provenance": f"data/forecasts/{drhp_id}.json",
            "abstain": record.is_abstain,
        }
        # D-04: fold the read-only GMP-vs-model gap alongside the forecast, ONLY
        # when a GMP is actually reported (absent -> omit, never a fabricated gap).
        gap = _gmp_gap(drhp_id, record)
        if gap is not None:
            result["gmp_gap"] = gap
    except FileNotFoundError:
        # Honest "no calibrated forecast" state — never a fabricated band (P14).
        result = {
            "tool": TOOL_NAME,
            "record": None,
            "provenance": None,
            "abstain": True,
        }

    plan = [t for t in state.get("tool_plan", []) if t != TOOL_NAME]
    return {
        **state,
        "tool_plan": plan,
        "tool_calls": state.get("tool_calls", 0) + 1,
        "tool_results": state.get("tool_results", []) + [result],
    }


def _gmp_gap(drhp_id, record) -> dict | None:
    """Build the read-only GMP-vs-model gap block (D-04), or None when absent.

    DISPLAY-ONLY: GMP is read from `data/gmp/<drhp_id>.json` via the display-only
    `GmpRecord` and surfaced NEXT TO the GMP-free model band purely for context.
    GMP is NEVER passed into any model field. Returns None (fold omitted) when no
    GMP file exists OR the record is the honest absent-GMP state — never a
    fabricated gap. `drhp_id` is already allow-list gated by the caller.
    """
    path = _GMP_DIR / f"{drhp_id}.json"
    if not path.exists():
        return None

    gmp = GmpRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
    if gmp.is_absent:
        # No grey-market premium is being reported — omit the fold, fabricate no gap.
        return None

    spread = gmp.spread()
    # The GMP-FREE model band this GMP sits next to (None on a record-native
    # abstain — an honest "the model declines a band" state, still no fabrication).
    model_band_pct = None
    if record.interval is not None:
        model_band_pct = {
            "low_pct": record.interval.low_pct,
            "high_pct": record.interval.high_pct,
            "median_pct": record.interval.median_pct,
        }

    return {
        "gmp_quotes": [
            {"source": q.source, "value": q.value, "as_of": q.as_of}
            for q in gmp.quotes
        ],
        "gmp_spread": (
            None if spread is None
            else {"low": spread.low, "high": spread.high, "n": spread.n}
        ),
        "gmp_as_of": gmp.as_of,
        # The GMP-free model band the GMP is compared AGAINST — display context only.
        "model_band_pct": model_band_pct,
        # Mandatory display-only caveat (single-source; states GMP is never used in
        # any forecast). Re-scrubbed downstream when synthesis fuses the answer.
        "caveat": GMP_CAVEAT,
    }
