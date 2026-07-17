"""
Unit test — the FCAST-02 / D5-01 leakage gate on the issue-structure feature layer
(05-04-PLAN.md).

Pins the ``available_at <= T0`` contract that is the walk-forward model's primary
P4 / look-ahead defense (T0 = issue-open day = ``issue_date``, D5-01 — which
supersedes FCAST-02's literal "T−1 of listing" wording). Everything here is
OFFLINE and deterministic (the 05-01 ``synthetic_panel`` / ``synthetic_features``
builders; no network, no live model):

  1. ``build_features`` on the synthetic panel succeeds, returns exactly
     ``FEATURE_COLUMNS`` (issue-structure only), preserves the row count, and its
     resolved ``available_at`` is ``<= issue_date`` (T0) for every feature/row.
  2. A crafted feature whose ``available_at`` is ``issue_date + 1 day`` RAISES
     ``LeakageError`` (naming the offending feature) — a post-T0 feature cannot
     enter the matrix.
  3. A missing issue-structure value is NaN-retained (never fabricated as 0) and
     the row is kept — the panel row count is preserved.
  4. ``leakage_audit`` returns a ``"<= T0 ✓"`` verdict for every issue-structure
     feature and lists no GMP / subscription feature.
  5. GMP / at-close subscription are excluded by construction (contract-level +
     builder guard).
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

import pipelines.features as F
from pipelines.features import (
    EXCLUDED_FROM_MODEL,
    FEATURE_COLUMNS,
)
from pipelines.features.build import (
    LeakageError,
    build_features,
    leakage_audit,
)
from tests.unit.fixtures.forecast_fixtures import (
    synthetic_features,
    synthetic_panel,
)


def _enriched_panel(n: int = 40, seed: int = 0) -> pd.DataFrame:
    """A synthetic panel with the issue-structure feature columns attached.

    Uses the 05-01 offline builders: ``synthetic_features`` supplies the
    issue-structure X (issue_size_cr, ..., lot_size) plus a shared ``available_at``
    stamp == issue_date, which the builder resolves the T0 gate against.
    """
    panel = synthetic_panel(n=n, seed=seed)
    feats = synthetic_features(panel, seed=seed + 1)
    return panel.join(feats)


# ---------------------------------------------------------------------------
# (a) build_features succeeds; exactly FEATURE_COLUMNS; rows preserved; <= T0
# ---------------------------------------------------------------------------


def test_build_features_returns_exactly_feature_columns_bare_panel():
    """A bare panel (no feature columns) still builds: all-NaN X, columns correct."""
    panel = synthetic_panel(n=30, seed=3)
    x, avail = build_features(panel)

    assert list(x.columns) == list(FEATURE_COLUMNS)
    assert list(avail.columns) == list(FEATURE_COLUMNS)
    # row count preserved
    assert len(x) == len(panel)
    assert len(avail) == len(panel)
    # no column is GMP / subscription / listing-day
    assert "gmp" not in x.columns
    assert not any("subscri" in c for c in x.columns)
    assert not any("listing_day" in c for c in x.columns)
    # a bare panel has no feature values -> every value NaN-retained (never 0)
    assert x.isna().all().all()


def test_build_features_enriched_panel_values_and_t0_gate():
    """An enriched panel builds real values, exactly FEATURE_COLUMNS, all <= T0."""
    panel = _enriched_panel(n=40, seed=0)
    x, avail = build_features(panel)

    assert list(x.columns) == list(FEATURE_COLUMNS)
    assert len(x) == len(panel)
    # real (non-NaN) feature values came through
    assert x["issue_size_cr"].notna().all()
    assert x["lot_size"].notna().all()

    # THE GATE: every feature's resolved available_at <= issue_date (T0) for every row
    t0 = pd.to_datetime(panel["issue_date"])
    for col in FEATURE_COLUMNS:
        a = pd.to_datetime(avail[col])
        assert (a <= t0).all(), f"{col} has a row with available_at > T0"


# ---------------------------------------------------------------------------
# (b) a post-T0 feature RAISES LeakageError, naming the feature
# ---------------------------------------------------------------------------


def test_post_t0_feature_raises_leakage_error():
    """A feature stamped available_at = issue_date + 1 day trips the gate."""
    panel = _enriched_panel(n=20, seed=5)
    # Override ONE feature's available_at to one day AFTER issue-open (T0) -> leakage.
    panel = panel.copy()
    panel["issue_size_cr__available_at"] = pd.to_datetime(
        panel["issue_date"]
    ) + pd.Timedelta(days=1)

    with pytest.raises(LeakageError) as excinfo:
        build_features(panel)

    # The error names the offending feature (FCAST-02 auditability).
    assert "issue_size_cr" in str(excinfo.value)


def test_gate_passes_when_available_at_equals_t0():
    """available_at == issue_date (the boundary) is NOT leakage (<= is inclusive)."""
    panel = _enriched_panel(n=15, seed=6).copy()
    panel["filing_date"] = pd.to_datetime(panel["issue_date"])  # exactly T0
    x, avail = build_features(panel)  # must not raise
    assert len(x) == len(panel)


# ---------------------------------------------------------------------------
# (c) missing feature value -> NaN retained, row kept (replace-with-NaN honesty)
# ---------------------------------------------------------------------------


def test_missing_feature_value_is_nan_retained_row_kept():
    """A None issue-structure value stays NaN and the row is NOT dropped."""
    panel = _enriched_panel(n=25, seed=7).copy()
    n_before = len(panel)
    # blank out one cell (a genuinely missing disclosure)
    panel.loc[panel.index[3], "promoter_dilution_pct"] = None

    x, _avail = build_features(panel)

    assert len(x) == n_before  # row preserved, never dropped
    val = x.loc[panel.index[3], "promoter_dilution_pct"]
    assert isinstance(val, float) and math.isnan(val)  # NaN, not fabricated 0
    assert val != 0.0


# ---------------------------------------------------------------------------
# (d) leakage_audit — a verdict per feature; no GMP/subscription
# ---------------------------------------------------------------------------


def test_leakage_audit_verdict_per_feature_no_excluded():
    """Every issue-structure feature gets a '<= T0 ✓' verdict; none is excluded."""
    panel = _enriched_panel(n=30, seed=8)
    audit = leakage_audit(panel)

    # one record per feature, in feature order
    assert [rec["feature"] for rec in audit] == list(FEATURE_COLUMNS)
    for rec in audit:
        assert rec["verdict"] == "<= T0 ✓"
        assert rec["available_at_rule"]  # a non-empty rule token
        # no audited feature is a GMP / subscription / listing-day token
        assert rec["feature"].lower() not in EXCLUDED_FROM_MODEL
        assert "gmp" not in rec["feature"].lower()
        assert "subscri" not in rec["feature"].lower()
        assert "listing_day" not in rec["feature"].lower()


def test_leakage_audit_data_verified_raises_on_leaky_panel():
    """leakage_audit(panel) data-verifies: a leaky panel raises, not a clean audit."""
    panel = _enriched_panel(n=12, seed=9).copy()
    panel["lot_size__available_at"] = pd.to_datetime(
        panel["issue_date"]
    ) + pd.Timedelta(days=2)
    with pytest.raises(LeakageError):
        leakage_audit(panel)


def test_leakage_audit_static_declaration_without_panel():
    """The audit is emittable for the model card without a live panel."""
    audit = leakage_audit()
    assert len(audit) == len(FEATURE_COLUMNS)
    assert all(rec["verdict"] == "<= T0 ✓" for rec in audit)


# ---------------------------------------------------------------------------
# (e) GMP / subscription excluded by construction
# ---------------------------------------------------------------------------


def test_excluded_from_model_names_gmp_and_subscription():
    """The contract names GMP + at-close subscription as never-features."""
    assert "gmp" in EXCLUDED_FROM_MODEL
    assert "subscription_at_close" in EXCLUDED_FROM_MODEL
    # and no feature column is one of them
    assert not (set(FEATURE_COLUMNS) & EXCLUDED_FROM_MODEL)
    assert "gmp" not in FEATURE_COLUMNS
    assert not any("subscri" in c for c in FEATURE_COLUMNS)


def test_missing_t0_column_raises():
    """A panel without issue_date (T0) cannot be gated -> ValueError."""
    panel = _enriched_panel(n=10, seed=11).drop(columns=["issue_date"])
    with pytest.raises(ValueError, match="issue_date"):
        build_features(panel)


def test_module_exports_contract_surface():
    """The feature contract surface is importable (like PANEL_COLUMNS)."""
    assert F.FEATURE_COLUMNS
    assert F.FEATURE_DTYPES
    assert F.FEATURE_AVAILABLE_AT
    assert F.EXCLUDED_FROM_MODEL
