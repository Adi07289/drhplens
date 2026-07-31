"""
Unit test — the expanded four-family feature pool (05-08-PLAN.md Task 2).

Extends the 05-04 issue-structure leakage gate (tests/unit/test_features_available_at.py)
to the three families added in 05-08, each behind the same hard ``available_at <= T0``
(issue-open, D5-01) gate. Everything here is OFFLINE and deterministic (the 05-01
synthetic builders + tmp-dir DRHP caches; no network, no live model, no live fetch):

  (a) family (c) DRHP-derived features are read ALLOW-LIST-GATED from the Phase-2
      (data/snapshots) + Phase-3 (data/redflag) caches and stamped a filing-date
      available_at (<= T0); an unknown/traversal id reads nothing (NaN-retained).
  (b) a crafted post-open anchor field (available_at = T0+1) RAISES LeakageError,
      and the post-open QIB/NII/RII subscription multiples are excluded by
      construction (D5-08).
  (c) anchor_leakage_audit documents each pre-open anchor source field + its T0-1
      disclosure timestamp + verdict.
  (d) pool_sectors maps a <min_n sector to 'Other' and reports N-per-sector (D5-10).
  (e) the panel-derived regime features (b) are no-lookahead (PRIOR listings only).
"""
from __future__ import annotations

import json
import math

import pandas as pd
import pytest

from pipelines.features import (
    ANCHOR_FEATURES,
    DRHP_FEATURES,
    EXCLUDED_FROM_MODEL,
    FEATURE_COLUMNS,
    REGIME_FEATURES,
)
from pipelines.features import build as build_mod
from pipelines.features.build import (
    LeakageError,
    anchor_leakage_audit,
    build_features,
    pool_sectors,
)
from tests.unit.fixtures.forecast_fixtures import synthetic_features, synthetic_panel

KNOWN_ID = "swiggy_2024_11"  # a real catalogue allow-list entry


def _enriched_panel(n: int = 20, seed: int = 0) -> pd.DataFrame:
    """A synthetic panel with the issue-structure X (+ available_at stamp) attached."""
    panel = synthetic_panel(n=n, seed=seed)
    feats = synthetic_features(panel, seed=seed + 1)
    return panel.join(feats)


# ---------------------------------------------------------------------------
# (a) family (c) DRHP-derived: allow-list-gated cache read + filing-date stamp
# ---------------------------------------------------------------------------


def _seed_drhp_caches(monkeypatch, tmp_path, drhp_id: str) -> None:
    """Point the DRHP cache dirs at a tmp fixture and seed a clean numeric block."""
    snap_dir = tmp_path / "snapshots"
    red_dir = tmp_path / "redflag"
    snap_dir.mkdir()
    red_dir.mkdir()
    (snap_dir / f"{drhp_id}.json").write_text(
        json.dumps(
            {
                "drhp_id": drhp_id,
                "numeric": {
                    "revenue_growth": 0.22,
                    "ebitda_margin": -0.05,
                    "roe": 0.11,
                    "debt_to_equity": 0.4,
                },
            }
        ),
        encoding="utf-8",
    )
    (red_dir / f"{drhp_id}.json").write_text(
        json.dumps(
            {
                "drhp_id": drhp_id,
                "numeric": {
                    "rpt_intensity": 0.034,
                    "use_of_proceeds_mix": 0.6,
                    "promoter_holding_pct": 45.0,
                },
                "ranked_risks": [{"claim_id": "a"}, {"claim_id": "b"}, {"claim_id": "c"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(build_mod, "SNAPSHOTS_DIR", snap_dir)
    monkeypatch.setattr(build_mod, "REDFLAG_DIR", red_dir)


def test_family_c_reads_caches_allow_list_gated_and_stamps_filing_available_at(
    monkeypatch, tmp_path
):
    """Family (c) reads the Phase-2/3 caches for a KNOWN id, values + <= T0 stamp."""
    _seed_drhp_caches(monkeypatch, tmp_path, KNOWN_ID)

    panel = _enriched_panel(n=8, seed=2).copy()
    panel["drhp_id"] = KNOWN_ID  # a known allow-list id -> caches read

    x, avail = build_features(panel)

    # clean structured numerics came through
    assert (x["revenue_growth"] == 0.22).all()
    assert (x["ebitda_margin"] == -0.05).all()
    assert (x["roe"] == 0.11).all()
    assert (x["debt_to_equity"] == 0.4).all()
    assert (x["rpt_intensity"] == 0.034).all()
    assert (x["use_of_proceeds_mix"] == 0.6).all()
    assert (x["promoter_holding_pct"] == 45.0).all()
    # red_flag_count is the structured ranked_risks COUNT (never prose-parsed)
    assert (x["red_flag_count"] == 3.0).all()

    # filing-date available_at is <= T0 (issue_date) for every family (c) feature
    t0 = pd.to_datetime(panel["issue_date"])
    for col in DRHP_FEATURES:
        assert (pd.to_datetime(avail[col]) <= t0).all(), f"{col} available_at > T0"


def test_family_c_unknown_id_reads_nothing_nan_retained(monkeypatch, tmp_path):
    """An unknown / path-traversal drhp_id is allow-list-refused -> family c NaN."""
    _seed_drhp_caches(monkeypatch, tmp_path, KNOWN_ID)

    panel = _enriched_panel(n=6, seed=3).copy()
    panel["drhp_id"] = "../../etc/passwd"  # not a catalogue id -> gate blocks read

    x, _avail = build_features(panel)
    for col in DRHP_FEATURES:
        assert x[col].isna().all(), f"{col} should be NaN for an un-allow-listed id"


# ---------------------------------------------------------------------------
# (b) a crafted post-open anchor field RAISES; subscription excluded by construction
# ---------------------------------------------------------------------------


def test_post_open_anchor_field_raises_leakage_error():
    """An anchor feature stamped available_at = T0+1 trips the T0 gate (D5-08)."""
    panel = _enriched_panel(n=10, seed=5).copy()
    panel["anchor_book_cr__available_at"] = pd.to_datetime(
        panel["issue_date"]
    ) + pd.Timedelta(days=1)

    with pytest.raises(LeakageError) as excinfo:
        build_features(panel)
    assert "anchor_book_cr" in str(excinfo.value)


def test_post_open_subscription_excluded_by_construction():
    """QIB/NII/RII + subscription_at_close are named excluded, never features (D5-08)."""
    for token in ("subscription_at_close", "qib", "nii", "rii"):
        assert token in EXCLUDED_FROM_MODEL
        assert token not in FEATURE_COLUMNS
    assert not any("subscri" in c for c in FEATURE_COLUMNS)


# ---------------------------------------------------------------------------
# (c) anchor_leakage_audit documents the pre-open field + T0-1 timestamp
# ---------------------------------------------------------------------------


def test_anchor_leakage_audit_documents_preopen_fields():
    """Every anchor feature has a named pre-open source field + T0-1 timestamp."""
    audit = anchor_leakage_audit()
    assert [rec["feature"] for rec in audit] == list(ANCHOR_FEATURES)
    for rec in audit:
        assert rec["disclosure_timestamp"] == "T0-1"
        assert "pre-open" in rec["verdict"]
        assert "<= T0 ✓" in rec["verdict"]
        assert rec["source_field"]  # a non-empty named pre-open source
        # the audited anchor field is never a post-open subscription token
        assert "subscri" not in rec["feature"]


# ---------------------------------------------------------------------------
# (d) pool_sectors maps a <min_n sector to 'Other' and reports n_per_sector
# ---------------------------------------------------------------------------


def test_pool_sectors_pools_small_n_and_reports_counts():
    """Sectors below min_n (and NaN) -> 'Other'; n_per_sector reports original N."""
    panel = pd.DataFrame(
        {
            "sector": ["Food"] * 5 + ["Tiny"] * 2 + [None],
        }
    )
    pooled, n_per_sector = pool_sectors(panel, min_n=3)

    # the >= min_n sector is kept; the <min_n sector + the NaN sector pool to 'Other'
    assert list(pooled) == ["Food"] * 5 + ["Other"] * 2 + ["Other"]
    # the report keeps the ORIGINAL per-sector counts (thinness visible)
    assert n_per_sector == {"Food": 5, "Tiny": 2}


def test_pool_sectors_requires_sector_column():
    """A panel with no sector column cannot be pooled -> ValueError (D5-10)."""
    with pytest.raises(ValueError, match="sector"):
        pool_sectors(pd.DataFrame({"issuer": ["X"]}))


# ---------------------------------------------------------------------------
# (e) panel-derived regime features are no-lookahead (PRIOR listings only)
# ---------------------------------------------------------------------------


def test_regime_panel_features_are_no_lookahead():
    """ipo_pipeline_density / trailing_listing_gain use ONLY prior listings.

    The panel is ordered by listing_date, so the EARLIEST scorable IPO has no prior
    listings: density is an honest 0 and trailing gain is NaN (nothing to average).
    """
    panel = synthetic_panel(n=40, seed=6)
    x, avail = build_features(panel)

    # both panel-derived regime features are present in the matrix
    assert {"ipo_pipeline_density", "trailing_listing_gain"} <= set(x.columns)

    # earliest listing (first non-withdrawn row by listing_date) has no priors
    ordered = panel[panel["listing_date"].notna()].sort_values("listing_date")
    first_idx = ordered.index[0]
    assert x.loc[first_idx, "ipo_pipeline_density"] == 0.0
    assert math.isnan(x.loc[first_idx, "trailing_listing_gain"])

    # every regime feature's available_at is the pre-open (T0-1) snapshot <= T0
    t0 = pd.to_datetime(panel["issue_date"])
    for col in REGIME_FEATURES:
        a = pd.to_datetime(avail[col])
        assert (a[a.notna()] <= t0[a.notna()]).all(), f"{col} available_at > T0"
