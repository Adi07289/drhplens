"""
agent/gmp_schema.py — GmpRecord, the Phase 4 grey-market-premium cache schema.

Per 04-04-PLAN.md Task 1. Grey-market premium (GMP) is an UNOFFICIAL, unreliable
signal quoted by a handful of public aggregator sites. DRHPLens treats it as
read-only, cache-only DISPLAY data with caveats — never a demand indicator. A
GmpRecord captures 2-3 aggregator quotes as SEPARATE GmpQuote entries so their
disagreement (the honesty signal, D4-01) is preserved rather than averaged away.

Two states are FIRST-CLASS, not error/edge cases:
  - Absent GMP (`quotes == []`) — the COMMON case: 7 of 8 catalogue IPOs are
    already listed, so no live grey-market premium is being reported. This is the
    honest "No grey-market premium is being reported" state, NOT a fabricated
    zero and NOT an error.
  - Single-source GMP (`len(quotes) == 1`) — a valid record with no cross-source
    check available ("Only one source reported").

A spread (low/high/n across quotes) is DERIVED on demand via spread(); it is
None whenever there are fewer than two quotes (absent or single-source — a spread
needs at least two sources to be meaningful). The spread is intentionally not
stored on disk: it is a pure function of the committed quotes, so the cache stays
minimal and diff-reviewable.

ISOLATION (GMP-02, D4-03): this module imports ONLY pydantic + stdlib. It pulls
in NO modelling library and NO downstream prediction/historical pipeline. The
invariant is pinned by tests/unit/test_gmp_isolation.py (an inspect.getsource
substring audit). GMP is display-only and must stay computationally isolated.

On-disk shape (data/gmp/<drhp_id>.json):
{
  "drhp_id": "hyundai_2024_10",
  "computed_at": "2026-07-06T00:00:00Z",
  "as_of": "2024-10-14",
  "quotes": [
    {"source": "investorgain", "value": 25.0, "as_of": "2024-10-14"},
    {"source": "ipowatch",     "value": 67.0, "as_of": "2024-10-14"}
  ]
}

An absent-GMP record is the same shape with "quotes": []. This module does NOT
create the directory and does NOT interpolate any untrusted id into a path — the
pipeline (pipelines/gmp.py) gates <drhp_id> through the Phase 2 is_known_drhp_id
allow-list BEFORE forming any path (T-04-04-PATH).
"""
from __future__ import annotations

import json

from pydantic import BaseModel


class GmpQuote(BaseModel):
    """One aggregator's grey-market-premium quote.

    source: the aggregator label (e.g. "investorgain") — an untrusted scraped
        string; any renderer HTML-escapes it before display.
    value: the reported premium (₹ per share). A real reported number only —
        absence of a quote is modelled as its ABSENCE from the quotes list, never
        as a zero here.
    as_of: the date the aggregator reported this quote (ISO "YYYY-MM-DD"). Kept
        per-quote because aggregators report on slightly different days.
    """

    source: str
    value: float
    as_of: str


class GmpSpread(BaseModel):
    """The derived cross-source spread over >= 2 quotes (the divergence signal).

    low/high: the min/max reported premium across aggregators.
    n: how many aggregators reported (>= 2 — a spread needs at least two sources).

    A GmpSpread is only ever produced when there are two or more quotes; absent
    and single-source records report no spread (GmpRecord.spread() is None).
    """

    low: float
    high: float
    n: int


class GmpRecord(BaseModel):
    """The pre-computed grey-market-premium cache record for one drhp_id.

    quotes: the per-aggregator quotes, kept SEPARATE so their disagreement is
        preserved (D4-01). An empty list is the honest absent-GMP state (the
        common already-listed case); a single-entry list is the single-source
        state. Neither is a fabricated number.
    as_of: the record's headline as-of date (the sub-line reads "as of {as_of}").
    """

    drhp_id: str
    computed_at: str
    quotes: list[GmpQuote] = []
    as_of: str

    @property
    def is_absent(self) -> bool:
        """True when no aggregator reported — the honest absent-GMP state."""
        return len(self.quotes) == 0

    @property
    def is_single_source(self) -> bool:
        """True when exactly one aggregator reported (no cross-source check)."""
        return len(self.quotes) == 1

    def spread(self) -> GmpSpread | None:
        """Derive the cross-source spread (min/max/n) over the quotes.

        Returns None for the absent (0 quotes) and single-source (1 quote) states
        — a spread requires at least two sources to be meaningful. Otherwise
        returns a GmpSpread carrying the honest low/high divergence range.
        """
        if len(self.quotes) < 2:
            return None
        values = [q.value for q in self.quotes]
        return GmpSpread(low=min(values), high=max(values), n=len(values))

    def to_dict(self) -> dict:
        """Serialize to the flat on-disk dict shape."""
        return {
            "drhp_id": self.drhp_id,
            "computed_at": self.computed_at,
            "as_of": self.as_of,
            "quotes": [
                {"source": q.source, "value": q.value, "as_of": q.as_of}
                for q in self.quotes
            ],
        }

    def to_json(self) -> str:
        """Serialize to a JSON string (indent=2 — diff-reviewable committed cache)."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, raw: dict) -> "GmpRecord":
        """Reconstruct a GmpRecord from the on-disk dict shape."""
        quotes = [GmpQuote.model_validate(q) for q in raw.get("quotes", [])]
        return cls(
            drhp_id=raw["drhp_id"],
            computed_at=raw["computed_at"],
            as_of=raw["as_of"],
            quotes=quotes,
        )

    @classmethod
    def from_json(cls, text: str) -> "GmpRecord":
        """Reconstruct a GmpRecord from a JSON string."""
        return cls.from_dict(json.loads(text))
