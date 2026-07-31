"""
tests/unit/test_walkforward_no_lookahead.py — P4 / FCAST-03 / D5-11: the
expanding-window as-of-T0 walk-forward is PROVABLY lookahead-free, abstains on thin
history, and its automated R²>0.5 alarm fires on a leak (and stays quiet on the
honest fixture).

The no-lookahead property is asserted PER FOLD against the provenance columns the
loop itself records (``t0`` = the IPO's issue-open day; ``pool_max_listing_date`` =
the newest listing in the pre-T0 pool; ``train_max`` / ``cal_min`` = the split
boundaries) — so the test audits the SAME selection ``walk_forward`` used, not a
re-implementation.

Offline + tiny: the deterministic ``synthetic_panel`` / ``synthetic_features``
builders + light trees; the walk-forward is computed ONCE (module-scoped) and
reused across the assertions.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from pipelines.forecast.walkforward import r2_leakage_alarm, walk_forward
from tests.unit.fixtures.forecast_fixtures import (
    synthetic_features,
    synthetic_panel,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# light trees + a smaller min_train keep the offline loop fast while still
# producing a healthy mix of covered folds and abstain rows on the 80-row fixture.
_LIGHT_PARAMS = {"n_estimators": 40, "max_depth": 2}
_MIN_TRAIN = 30


@pytest.fixture(scope="module")
def oos_frame():
    """Run the walk-forward once over the synthetic fixture (shared by the suite)."""
    panel = synthetic_panel()
    feats = synthetic_features(panel)
    return walk_forward(panel, feats, min_train=_MIN_TRAIN, params=_LIGHT_PARAMS)


@pytest.fixture(scope="module")
def panel():
    return synthetic_panel()


def test_every_nonabstain_fold_is_lookahead_free(oos_frame):
    """For EVERY covered fold the newest pre-T0 listing is strictly before T0
    (no lookahead) — T0 = issue-open (D5-01 / P4)."""
    covered = oos_frame[~oos_frame["abstain"]]
    assert len(covered) >= 2, "expected several covered folds on the fixture"

    # the whole pool (hence train AND calibration) listed strictly before T0_i
    assert (covered["pool_max_listing_date"] < covered["t0"]).all(), (
        "a training/calibration row listed on/after the IPO's issue-open day "
        "(lookahead leak — violates P4/D5-01)"
    )
    # belt-and-braces: the explicit train/calibration boundaries are pre-T0 too
    assert (covered["train_max_listing_date"] < covered["t0"]).all()
    assert (covered["cal_min_listing_date"] < covered["t0"]).all()


def test_calibration_slice_disjoint_and_newer_than_train(oos_frame):
    """The calibration slice is disjoint from and strictly newer than the
    proper-train slice — the precondition for a valid conformal coverage guarantee."""
    covered = oos_frame[~oos_frame["abstain"]]
    # cal = listing_date > cut, train = listing_date <= cut => cal_min > train_max
    assert (covered["cal_min_listing_date"] > covered["train_max_listing_date"]).all()
    assert (covered["n_train"] > 0).all()
    assert (covered["n_cal"] > 0).all()


def test_thin_history_ipos_abstain_insufficient_history(oos_frame, panel):
    """IPOs with fewer than ``min_train`` prior listings emit an
    ``insufficient_history`` abstain row and NO fabricated band (D5-09)."""
    abstained = oos_frame[oos_frame["abstain"]]
    assert len(abstained) >= 1, "the earliest IPOs must abstain on thin history"
    assert (abstained["abstain_reason"] == "insufficient_history").all()
    # abstain rows carry no band
    assert abstained["low"].isna().all()
    assert abstained["high"].isna().all()
    assert abstained["median"].isna().all()

    # the earliest-listing scorable IPO (0 priors < min_train) MUST be abstained
    first_issuer = (
        panel[panel["listing_day_return"].notna()]
        .sort_values("listing_date")
        .iloc[0]["issuer"]
    )
    assert first_issuer in set(abstained["issuer"])


def test_r2_leakage_alarm_quiet_on_honest_and_fires_on_leak(oos_frame):
    """The R²>0.5 alarm stays quiet on the honest fixture (random features -> low
    OOS R²) and FIRES on a synthetically leaked frame (median == actual -> R²=1)."""
    # honest: the model cannot beat its own uncertainty -> no alarm
    r2, flag = r2_leakage_alarm(oos_frame)
    assert flag is None, f"honest fixture should not alarm (R²={r2})"
    assert r2 <= 0.5

    # leaked: overwrite the median with the realized return (perfect fit) -> alarm
    leaked = oos_frame.copy()
    covered_mask = ~leaked["abstain"]
    leaked.loc[covered_mask, "median"] = leaked.loc[covered_mask, "actual"]
    r2_leak, flag_leak = r2_leakage_alarm(leaked)
    assert r2_leak > 0.5
    assert flag_leak is not None
    assert "LEAKAGE ALARM" in flag_leak


def test_r2_alarm_returns_nan_none_on_too_few_rows():
    """Fewer than two covered rows -> (NaN, None): no alarm can be computed."""
    import pandas as pd

    tiny = pd.DataFrame(
        {"actual": [0.1], "median": [0.05], "abstain": [False]}
    )
    r2, flag = r2_leakage_alarm(tiny)
    assert flag is None
    assert r2 != r2  # NaN


def test_walkforward_import_is_lazy_no_modelling_stack():
    """Importing pipelines.forecast.walkforward must NOT import xgboost/mapie/sklearn
    at module load — the modelling stack is reached only lazily (inside functions),
    so the walk-forward module import stays offline."""
    code = (
        "import sys\n"
        "import pipelines.forecast.walkforward  # noqa: F401\n"
        "for lib in ('xgboost', 'mapie', 'sklearn'):\n"
        "    assert lib not in sys.modules, f'{lib} imported at module load'\n"
        "print('lazy-ok')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"lazy-import check failed:\nstdout={proc.stdout}\nstderr={proc.stderr}"
    )
    assert "lazy-ok" in proc.stdout
