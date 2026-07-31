"""
Integration smoke — live NSE ``public-past-issues`` endpoint (05-02 · FCAST-03).

Hits the Source-A LISTED-CORE feed the survivorship panel builder repointed onto
(D5-04): ``pipelines.historical.sources.fetch_nse_past_issues`` over NSE's
``/api/public-past-issues``. On failure it FAILS with a maintainer-facing verdict
rather than silently degrading the universe build — a silent 0-row build is exactly
the 04-07 failure mode (RESEARCH Pitfall 7). CLAUDE.md requires a nightly integration
test against the NSE endpoints; this is the past-issues canary.

Live network required, so it is SKIPPED unless ``NSE_LIVE_SMOKE=1`` (set by the
nightly ``nightly-nse.yml`` workflow). It is DESELECTED from the quick unit loop
(``pytest tests/unit -q``) — it lives under ``tests/integration/`` and carries the
``integration`` marker. The ``nse`` library is NOT required (gated behind the 05-11
human-verify checkpoint, T-05-02-SC): the fetcher falls back to a cookie-primed GET.
"""
from __future__ import annotations

import datetime as _dt
import os

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("NSE_LIVE_SMOKE") != "1",
        reason="live NSE past-issues smoke — set NSE_LIVE_SMOKE=1 to run (nightly CI / 05-02).",
    ),
]


def test_nse_past_issues_returns_rows() -> None:
    """The listed-core feed returns non-zero rows carrying the panel's field contract."""
    from pipelines.historical import sources as s

    to_date = _dt.date.today()
    from_date = _dt.date(to_date.year - 1, 1, 1)
    try:
        rows = s.fetch_nse_past_issues(from_date, to_date)
    except Exception as exc:  # noqa: BLE001 — surface the drift verdict clearly
        pytest.fail(
            "NSE public-past-issues endpoint broken as of this run "
            f"({type(exc).__name__}: {exc}); the survivorship universe builder "
            "(05-02 Source A) must be repointed / the `nse` library refreshed "
            "(Pitfall 7 — a silent 0-row build is the 04-07 failure mode)."
        )

    assert rows, (
        "NSE past-issues returned 0 rows — a silent source failure (Pitfall 7). "
        "The listed-core universe is empty; check NSE cookie priming / endpoint shape."
    )
    # Every parsed row must carry the raw panel-row contract the builder consumes.
    sample = rows[0]
    assert "issuer" in sample and "issue_date" in sample
