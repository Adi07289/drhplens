"""
tests/unit/conftest.py — unit-test-local fixture re-exports.

``synthetic_redflag_record`` is defined once in tests/eval/conftest.py (LOCKED at
Wave 0, 03-01-PLAN Task 2). The methodology-pane unit test (Plan 06) consumes it,
so it is re-exported here to make it visible to tests/unit/ without duplicating the
fixture body (single source of truth).
"""
from __future__ import annotations

from tests.eval.conftest import synthetic_redflag_record  # noqa: F401
