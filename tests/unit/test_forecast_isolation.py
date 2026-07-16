"""
Unit test — the FCAST-02 isolation pin, in BOTH directions (the reverse of the
Phase 4 display-isolation audit, which explicitly reserved this for Phase 5).

The ForecastRecord is the single, cache-only seam between the offline forecaster
and the cache-only Streamlit render. Two invariants must hold, and both are pinned
here as inspect.getsource / on-disk substring audits (mirroring
tests/unit/test_gmp_isolation.py):

  Direction 1 — the RENDER must not import the MODEL. The forecast render module
    (ui/forecast_block.py) and its wiring in pages/02_snapshot.py reference NONE of
    the modelling libraries or the heavy model/feature/historical pipelines. The
    render reads only cached data/forecasts/ JSON via the import-light loader.

  Direction 2 — the PREDICTOR must not import the DISPLAY signal. The forecast
    loader package (pipelines.forecast) and the (later) model / walk-forward /
    feature modules reference NO display-signal module — the model never sees it.

Some target modules do not exist yet (they land in 05-05 / 05-07); those checks
are pytest.importorskip-guarded so this test is GREEN today and executes the real
audit automatically once the modules land. The record schema + the loader package
DO exist now and are audited unconditionally.
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import agent.forecast_schema
import pipelines.forecast

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Direction 1: render must not import the model
# ---------------------------------------------------------------------------

# The render reads only cached JSON. It DOES import the import-light loader package
# (pipelines.forecast), so the bare loader token is intentionally NOT forbidden
# here — only the heavy model/feature/historical modules and the modelling libs.
RENDER_FORBIDDEN = (
    "xgboost",
    "mapie",
    "sklearn",
    "conformal",
    "pipelines.forecast.model",
    "pipelines.forecast.walkforward",
    "pipelines.features",
    "pipelines.historical",
    "shap",
)


def test_render_block_imports_no_model_code() -> None:
    """ui/forecast_block.py (once it lands in 05-07) references none of the
    modelling libraries or the heavy model/feature/historical pipelines — it is a
    cache-only render over data/forecasts/ JSON (FCAST-02, Direction 1)."""
    fb = pytest.importorskip(
        "ui.forecast_block",
        reason="ui.forecast_block lands in 05-07; audit runs once it exists.",
    )
    src = inspect.getsource(fb)
    for token in RENDER_FORBIDDEN:
        assert token not in src, (
            f"ui/forecast_block.py must not reference {token!r} "
            f"(FCAST-02 Direction 1: the render is cache-only, "
            f"computationally isolated from the model)."
        )


def test_snapshot_page_forecast_wiring_imports_no_model_code() -> None:
    """The forecast wiring in pages/02_snapshot.py references none of the modelling
    libraries or the heavy model/feature/historical pipelines. The page is a
    Streamlit script (importing it would execute it), so it is audited by reading
    its source from disk rather than via inspect.getsource (FCAST-02, Direction 1)."""
    page = REPO_ROOT / "pages" / "02_snapshot.py"
    assert page.exists(), f"expected the snapshot page at {page}"
    src = page.read_text(encoding="utf-8")
    for token in RENDER_FORBIDDEN:
        assert token not in src, (
            f"pages/02_snapshot.py must not reference {token!r} "
            f"(FCAST-02 Direction 1: the render is cache-only, "
            f"computationally isolated from the model)."
        )


# ---------------------------------------------------------------------------
# Direction 2: predictor must not import the display signal
# ---------------------------------------------------------------------------

# The forecast loader / model / feature modules must never reference the display
# signal (the substring "gmp" covers both the bare module and the pipelines.gmp
# dotted path). The record must also stay free of any modelling library.
PREDICTOR_FORBIDDEN = (
    "gmp",
    "xgboost",
    "mapie",
    "sklearn",
    "shap",
)


def test_loader_package_is_import_light_and_display_isolated() -> None:
    """pipelines.forecast (the loader __init__) gates through is_known_drhp_id and
    references no display signal and no modelling library — it is import-light
    (FCAST-02 Direction 2; T-05-03-PATH allow-list gate)."""
    src = inspect.getsource(pipelines.forecast)
    assert "is_known_drhp_id" in src, (
        "the loader must gate drhp_id through the catalogue allow-list "
        "(T-05-03-PATH) before forming any path."
    )
    for token in PREDICTOR_FORBIDDEN:
        assert token not in src, (
            f"pipelines/forecast/__init__.py must not reference {token!r} "
            f"(FCAST-02 Direction 2: the predictor/loader is isolated from the "
            f"display signal and imports no modelling library)."
        )


def test_forecast_schema_is_import_light_and_display_isolated() -> None:
    """agent/forecast_schema.py (the record boundary) references no modelling
    library, no downstream pipeline, and no display signal — pydantic + stdlib
    only (FCAST-02)."""
    src = inspect.getsource(agent.forecast_schema)
    for token in (
        "xgboost",
        "mapie",
        "sklearn",
        "shap",
        "pipelines.forecast",
        "pipelines.features",
        "pipelines.historical",
        "gmp",
    ):
        assert token not in src, (
            f"agent/forecast_schema.py must not reference {token!r} "
            f"(FCAST-02: the record is the import-light isolation boundary)."
        )


@pytest.mark.parametrize(
    "modname",
    [
        "pipelines.forecast.model",
        "pipelines.forecast.walkforward",
        "pipelines.features",
    ],
)
def test_model_and_feature_modules_never_import_display_signal(modname: str) -> None:
    """Once the model / walk-forward / feature modules land (05-05), their source
    must reference no display signal — the model never sees it (FCAST-02
    Direction 2). importorskip keeps this GREEN until the modules exist."""
    mod = pytest.importorskip(
        modname,
        reason=f"{modname} lands in 05-05; the reverse audit runs once it exists.",
    )
    src = inspect.getsource(mod)
    assert "gmp" not in src, (
        f"{modname} must not reference the display signal 'gmp' "
        f"(FCAST-02 Direction 2: the predictor is isolated from display data)."
    )


# ---------------------------------------------------------------------------
# Allow-list gate (T-05-03-PATH) + loader behavior
# ---------------------------------------------------------------------------


def test_load_forecast_rejects_unknown_id() -> None:
    """An un-allow-listed id raises ValueError BEFORE any filesystem path is formed
    (T-05-03-PATH path-traversal mitigation)."""
    from pipelines.forecast import load_forecast

    with pytest.raises(ValueError):
        load_forecast("not_a_real_id")

    # a path-traversal attempt is likewise rejected by the allow-list, not sanitized
    with pytest.raises(ValueError):
        load_forecast("../../etc/passwd")


def test_load_forecast_reads_committed_seed() -> None:
    """load_forecast('swiggy_2024_11') returns the ForecastRecord read from the
    05-01 committed seed (a full-render covered band)."""
    from pipelines.forecast import load_forecast

    rec = load_forecast("swiggy_2024_11")
    assert rec.drhp_id == "swiggy_2024_11"
    assert rec.is_abstain is False
    assert rec.interval is not None
    assert rec.interval.low_pct == -4.2
    assert rec.metrics.n == 247


def test_load_forecast_abstain_seed_carries_no_interval() -> None:
    """The hyundai_2024_10 committed seed is the first-class abstain state:
    is_abstain True, interval None, honest reason."""
    from pipelines.forecast import load_forecast

    rec = load_forecast("hyundai_2024_10")
    assert rec.is_abstain is True
    assert rec.interval is None
    assert rec.abstain_reason == "insufficient_history"


def test_load_forecast_missing_file_raises_filenotfound() -> None:
    """An allow-listed id with no committed forecast file raises FileNotFoundError
    (the render's honest 'no calibrated forecast available yet' empty-state) —
    distinct from the ValueError of an un-allow-listed id."""
    from data.catalogue_loader import load_catalogue
    from pipelines.forecast import FORECASTS_DIR, load_forecast

    missing = next(
        ipo.drhp_id
        for ipo in load_catalogue()
        if not (FORECASTS_DIR / f"{ipo.drhp_id}.json").exists()
    )
    with pytest.raises(FileNotFoundError):
        load_forecast(missing)
