"""
tests/unit/conftest.py — unit-test-local fixture re-exports.

``synthetic_redflag_record`` is defined once in tests/eval/conftest.py (LOCKED at
Wave 0, 03-01-PLAN Task 2). The methodology-pane unit test (Plan 06) consumes it,
so it is re-exported here to make it visible to tests/unit/ without duplicating the
fixture body (single source of truth).

The ``forecast_*`` fixtures below wrap the pure, offline builders in
tests/unit/fixtures/forecast_fixtures.py so the Phase 5 modeling tests (Wave 2-6)
can inject a deterministic synthetic panel / feature matrix / out-of-sample rows by
name. The builders remain importable directly for tests that need custom args.
"""
from __future__ import annotations

import pytest

from tests.eval.conftest import synthetic_redflag_record  # noqa: F401
from tests.unit.fixtures.forecast_fixtures import (
    oos_rows,
    synthetic_features,
    synthetic_panel,
)


@pytest.fixture
def forecast_synthetic_panel():
    """A deterministic synthetic historical IPO panel (offline, seed=0)."""
    return synthetic_panel()


@pytest.fixture
def forecast_synthetic_features(forecast_synthetic_panel):
    """The issue-structure feature matrix aligned to ``forecast_synthetic_panel``."""
    return synthetic_features(forecast_synthetic_panel)


@pytest.fixture
def forecast_oos_rows():
    """A small deterministic per-IPO out-of-sample frame for metrics/baselines."""
    return oos_rows()
