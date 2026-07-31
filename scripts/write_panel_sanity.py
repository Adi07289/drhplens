"""
scripts/write_panel_sanity.py — write data/historical/panel_sanity.json from the
committed historical panel (04-07 / SC-5 median MAAR sanity-check).

Deterministic, no network. Produces the small render-ready artifact that
`/methodology` reads (json only) to surface the survivorship sanity result — the
same human-MD (README) + machine-JSON split the model card uses. On the current
committed panel the median (~10.2%) is WITHIN the [-5%, +20%] band, so no divergence
flag fires; the page renders the honest within-band confirmation.

Usage:  PYTHONPATH=. .venv/bin/python scripts/write_panel_sanity.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from pipelines.historical import coerce_panel
from pipelines.historical.validate import panel_sanity_summary

_REPO = Path(__file__).resolve().parents[1]
_PANEL = _REPO / "data" / "historical" / "ipo_panel.parquet"
_OUT = _REPO / "data" / "historical" / "panel_sanity.json"


def main() -> None:
    if not _PANEL.is_file():
        raise SystemExit(f"committed panel missing: {_PANEL} — run the 05-11 crawl first.")
    df = coerce_panel(pd.read_parquet(_PANEL))
    summary = panel_sanity_summary(df)
    _OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"wrote {_OUT}: median_pct={summary['median_pct']} n={summary['n_scored']} "
        f"within_band={summary['within_band']} "
        f"flag={'FIRED' if summary['flag'] else 'none'}"
    )


if __name__ == "__main__":
    main()
