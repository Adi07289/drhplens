"""
tests/unit/test_release_gate.py — Wave-0 FCAST-05 / P9 / D5-01: the P9 release gate
composes the four-baseline Diebold–Mariano tests with the R²>0.5 leakage alarm into
an explicit, HONEST pass/fail verdict.

Proves:
  * a LEAKED frame (median == actual -> OOS R²>0.5) yields ``passed=False`` with the
    ``r2_alarm`` set — the deferred 05-04 R²-gate now acts as a HARD release gate
    (a T0-violating feature likely slipped in, P4/P9).
  * a frame where a naive baseline SIGNIFICANTLY beats the model (DM p<0.05 in the
    baseline's favour) yields ``passed=False`` — do NOT ship, do NOT p-hack
    (RESEARCH §Pitfall 4).
  * an honest statistical TIE yields ``passed=True`` WITH the explicit "does not
    significantly outperform" note (a pre-apply, no-demand model is EXPECTED to be
    humble; a low R² is a feature, D5-01) — the gate never tunes to force a pass.
  * the verdict is plain-data (``per_baseline`` DM stats + ``notes``) the 05-10 model
    card embeds verbatim.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from pipelines.forecast.baselines import BASELINE_NAMES, release_gate

# A common T0 strictly after every prior listing built below.
T0 = pd.Timestamp("2020-01-01")


def _prior_panel(mean: float, sigma: float, *, n: int = 60, seed: int = 0) -> pd.DataFrame:
    """``n`` prior listings, all listed well before the common T0, ~N(mean, sigma)."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2016-01-01")
    dates = pd.to_datetime([start + pd.Timedelta(days=15 * i) for i in range(n)])
    rets = rng.normal(mean, sigma, n)
    return pd.DataFrame(
        {
            "issuer": [f"Prior {i:03d}" for i in range(n)],
            "listing_date": dates,
            "listing_day_return": rets,
        }
    )


def _oos(actual, median) -> pd.DataFrame:
    """A covered walk-forward OOS frame (all rows reference the same as-of-T0 pool)."""
    actual = np.asarray(actual, dtype=float)
    median = np.asarray(median, dtype=float)
    n = actual.size
    return pd.DataFrame(
        {
            "issuer": [f"OOS {i:03d}" for i in range(n)],
            "actual": actual,
            "median": median,
            "t0": [T0] * n,
            "abstain": [False] * n,
        }
    )


# ---------------------------------------------------------------------------
# (a) FAIL on the R²>0.5 leakage alarm (the deferred 05-04 gate, P4/P9)
# ---------------------------------------------------------------------------
def test_release_gate_fails_on_r2_leakage_alarm() -> None:
    panel = _prior_panel(0.05, 0.10, seed=1)
    rng = np.random.default_rng(10)
    actual = rng.normal(0.05, 0.15, 24)
    # median == actual -> a perfect fit -> OOS R²=1 -> the leakage alarm fires.
    oos = _oos(actual, actual.copy())

    verdict = release_gate(oos, panel)

    assert verdict["passed"] is False
    assert verdict["r2_alarm"] is not None
    assert verdict["r2"] > 0.5
    assert any("leakage" in note.lower() for note in verdict["notes"])


# ---------------------------------------------------------------------------
# (b) FAIL when a naive baseline significantly beats the model (Pitfall 4)
# ---------------------------------------------------------------------------
def test_release_gate_fails_when_a_baseline_beats_the_model() -> None:
    # A tight pool -> every baseline lands ≈ 0.05; the model is wildly off (0.60).
    panel = _prior_panel(0.05, 0.02, seed=2)
    rng = np.random.default_rng(20)
    actual = rng.normal(0.05, 0.02, 24)          # baselines nail actual ≈ 0.05
    median = np.full(24, 0.60)                    # model uniformly far from actual
    oos = _oos(actual, median)

    verdict = release_gate(oos, panel)

    assert verdict["passed"] is False
    # the failure is the baseline-beats-model path, NOT a leakage alarm (R² is low here)
    assert verdict["r2_alarm"] is None
    beaten = [
        name
        for name in BASELINE_NAMES
        if verdict["per_baseline"][name]["baseline_beats_model_sig"]
    ]
    assert beaten, "at least one naive baseline should significantly beat the model"
    # the DM stat for a beating baseline is positive (model loss significantly higher)
    for name in beaten:
        assert verdict["per_baseline"][name]["dm_stat"] > 0.0
        assert verdict["per_baseline"][name]["p_value"] < 0.05
    assert any("baseline beats model" in note.lower() for note in verdict["notes"])


# ---------------------------------------------------------------------------
# (c) PASS honestly on a statistical tie — with the humility note (D5-01)
# ---------------------------------------------------------------------------
def test_release_gate_passes_honestly_on_a_statistical_tie() -> None:
    # A wide pool centered at 0 -> every baseline ≈ 0; the model also ≈ 0 -> a tie.
    panel = _prior_panel(0.0, 0.30, seed=3)
    rng = np.random.default_rng(30)
    actual = rng.normal(0.0, 0.30, 24)           # wide, centered at 0
    median = rng.normal(0.0, 0.01, 24)           # model ≈ 0 (≈ every baseline)
    oos = _oos(actual, median)

    verdict = release_gate(oos, panel)

    assert verdict["passed"] is True
    assert verdict["r2_alarm"] is None
    # no baseline significantly beats the model on the tie
    assert not any(
        verdict["per_baseline"][name]["baseline_beats_model_sig"]
        for name in BASELINE_NAMES
    )
    # the explicit honest "does not significantly outperform" note is present (D5-01)
    assert any(
        "does not significantly outperform" in note for note in verdict["notes"]
    )
    # the verdict is plain-data the 05-10 model card can embed verbatim
    assert set(BASELINE_NAMES) <= set(verdict["per_baseline"])
    for name in BASELINE_NAMES:
        stats = verdict["per_baseline"][name]
        assert {"dm_stat", "p_value", "wilcoxon_p", "n"} <= set(stats)


# ---------------------------------------------------------------------------
# plain-data shape — the model card reads per_baseline + r2 + notes, no plotting
# ---------------------------------------------------------------------------
def test_release_gate_returns_plain_data_verdict() -> None:
    panel = _prior_panel(0.05, 0.20, seed=4)
    rng = np.random.default_rng(40)
    actual = rng.normal(0.05, 0.20, 20)
    median = rng.normal(0.05, 0.20, 20)
    verdict = release_gate(_oos(actual, median), panel)

    assert set(verdict) >= {
        "passed",
        "r2",
        "r2_alarm",
        "per_baseline",
        "n_scored",
        "notes",
    }
    assert isinstance(verdict["passed"], bool)
    assert isinstance(verdict["notes"], list)
    assert verdict["n_scored"] == 20
