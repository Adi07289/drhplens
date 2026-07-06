"""
agent/peer_schema.py — PeerRecord, the Phase 4 peer-comparator cache schema.

Per 04-03-PLAN.md Task 1: a mirror of agent/redflag_schema.py. The DRHP's own
disclosed peer SET (PEER-01) is stored as `peer_set`, whose value is EITHER a
serialized `GroundedAnswer` (claim_id-bearing, cited — the peer names + DRHP page)
OR a `RefusalResponse` (the D4-06 honest empty-state: "This DRHP disclosed no
listed-peer comparison"). Both classes are reused VERBATIM from agent/schemas.py
— no field renames, no new citation shape (the cross-phase locked GroundedAnswer /
Claim contract and the claim_id regex r'^c_[a-z0-9]{6,16}$' are what the Phase 1
citation-chip renderer + Phase 3 METHOD-01 depend on).

The on-disk peer_set codec is the SAME {"refusal": ...} discriminator convention
as RedFlagRecord — copied, not reinvented (04-PATTERNS.md §"Union-discriminator
cache codec").

Phase-4 delta — per-cell provenance across TWO dimensions (PEER-02, D4-05 + the
locked orchestration decision): the peer MULTIPLES have no red-flag analog. Each
`(company, metric)` multiple is a `PeerMetric` carrying:
  - `current`: a `PeerCell` for the current-market value (primary), and
  - `drhp_date`: an OPTIONAL `PeerCell` for the value as-of the DRHP date where a
    source supplies it (BOTH dimensions where available, clearly labelled).
Each `PeerCell` records WHICH source supplied the value (source-priority ladder,
D4-05: screener.in `s` → yfinance `y` → NSE/BSE `n`, plus the DRHP-derived `d`)
and WHICH as-of dimension it is. A value missing from every source is
`PeerCell()` (value None) → renders `—` (never interpolated, never zero). A
negative/undefined P/E (loss-making issuer) carries the `not_meaningful` sentinel
→ renders `NM`, distinguishable from both a real value and a missing cell.

On-disk shape (data/peers/<drhp_id>.json):
{
  "drhp_id": "swiggy_2024_11",
  "computed_at": "2026-07-06T00:00:00Z",
  "as_of": "2026-07-06",
  "peer_set": { ...GroundedAnswer.model_dump()... }   # or {"refusal": {...}}
  "companies": [
    {"name": "Swiggy Limited", "is_ipo": true, "metrics": [
       {"metric": "pb",
        "current":   {"value": 9.4, "source": "s", "as_of": "current", "not_meaningful": false},
        "drhp_date": {"value": 7.1, "source": "d", "as_of": "drhp_date", "not_meaningful": false}},
       {"metric": "ev_ebitda",
        "current":   {"value": null, "source": null, "as_of": null, "not_meaningful": false},
        "drhp_date": null},
       ...
    ]},
    ...
  ]
}

A peer_set dict containing the "refusal" key is reconstructed as a
RefusalResponse; any other value dict is reconstructed as a GroundedAnswer. This
discriminator is unambiguous because GroundedAnswer.model_dump() always contains
"answer_prose"/"claims" and never a top-level "refusal" key.

Path safety (T-04-03-PATH): this module does NOT create the directory and does
NOT interpolate any untrusted id into a path — pipelines/peers.py gates <drhp_id>
through the Phase 2 is_known_drhp_id allow-list (data/catalogue_loader.py) BEFORE
forming any data/peers/<id>.json path.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from agent.schemas import GroundedAnswer, RefusalResponse

# The 4 canonical peer-multiple metric keys, in the UI-SPEC R-2 fixed column
# order — kept in sync with pipelines.peer_sources (the fetchers return exactly
# these keys). The fields_keys_known validator rejects any drift.
PEER_METRIC_KEYS: frozenset[str] = frozenset({"pe", "pb", "ev_ebitda", "roe"})

# The legal per-cell source flags (D4-05 source-priority ladder + the DRHP flag):
#   "s" screener.in (primary) · "y" yfinance (.NS/.BO fallback) · "n" NSE/BSE
#   · "d" DRHP-derived (the IPO's own as-of-DRHP row)
PeerSource = Literal["s", "y", "n", "d"]

# The as-of dimension a cell belongs to (BOTH kept where available).
PeerAsOf = Literal["current", "drhp_date"]


class PeerCell(BaseModel):
    """One (company, metric, as-of) cell with its per-cell provenance (D4-05).

    value: the multiple's numeric value, or None when NO source supplied it
        (renders `—` — never interpolated, never coerced to zero).
    source: WHICH source supplied the value (the D4-05 ladder flag), or None when
        the cell is missing. The Literal rejects any unknown source flag.
    as_of: WHICH as-of dimension this cell is ("current" market or "drhp_date").
    not_meaningful: the NM sentinel — True for a negative/undefined ratio (a
        loss-making issuer's P/E), so the renderer shows `NM` rather than a
        misleading number. Distinguishable from a real value AND a missing cell.
    """

    value: float | None = None
    source: PeerSource | None = None
    as_of: PeerAsOf | None = None
    not_meaningful: bool = False


class PeerMetric(BaseModel):
    """One peer multiple (P/E, P/B, EV/EBITDA, or ROE) across as-of dimensions.

    metric: the locked metric key (rejected by fields_keys_known if unknown).
    current: the current-market cell (primary — always present).
    drhp_date: the as-of-DRHP-date cell where a source supplies it (the locked
        orchestration decision — BOTH dimensions where available), else None.
    """

    metric: str
    current: PeerCell
    drhp_date: PeerCell | None = None

    @field_validator("metric")
    @classmethod
    def metric_key_known(cls, v: str) -> str:
        """Reject a metric key outside the locked 4-key peer-multiple contract.

        T-04-03-VALID: rejects unknown/hostile keys at schema validation time.
        """
        if v not in PEER_METRIC_KEYS:
            raise ValueError(
                f"Unknown peer metric key {v!r}; "
                f"must be one of {sorted(PEER_METRIC_KEYS)}"
            )
        return v


class PeerCompany(BaseModel):
    """One row of the peer table: a company and its per-cell-sourced multiples.

    name: the company name EXACTLY as disclosed in the DRHP (untrusted scraped /
        DRHP-derived string — the renderer HTML-escapes it, T-04-03 XSS control).
    is_ipo: True for the IPO issuer's own row (the DRHP-derived `d`/`drhp_date`
        row), False for a listed peer.
    metrics: the P/E, P/B, EV/EBITDA, ROE multiples (each a PeerMetric). A metric
        a company has no cell for is simply omitted from the list.
    """

    name: str
    is_ipo: bool = False
    metrics: list[PeerMetric] = Field(default_factory=list)


class PeerRecord(BaseModel):
    """The pre-computed peer-comparator cache record for one drhp_id.

    Mirrors RedFlagRecord: peer_set is (de)serialized with the {"refusal": ...}
    wrapper convention via to_dict()/from_dict(). companies is the ordered list of
    peer rows (the IPO issuer's own row first, then the DRHP-named listed peers).

    peer_set: the DRHP's own disclosed peer SET — a cited GroundedAnswer (PEER-01)
        OR the D4-06 honest empty-state RefusalResponse (no fabricated set).
    as_of: the record's headline as-of date (the current-market multiples are
        "current market values as of {as_of}", stated plainly in the sub-line).
    """

    drhp_id: str
    computed_at: str
    peer_set: GroundedAnswer | RefusalResponse
    companies: list[PeerCompany] = Field(default_factory=list)
    as_of: str

    model_config = {"arbitrary_types_allowed": True}

    def to_dict(self) -> dict:
        """Serialize to the on-disk dict shape (the {"refusal": ...} convention)."""
        return {
            "drhp_id": self.drhp_id,
            "computed_at": self.computed_at,
            "as_of": self.as_of,
            "peer_set": _dump_peer_set(self.peer_set),
            "companies": [company.model_dump() for company in self.companies],
        }

    def to_json(self) -> str:
        """Serialize to a JSON string (indent=2 — diff-reviewable committed cache)."""
        import json

        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, raw: dict) -> "PeerRecord":
        """Reconstruct a PeerRecord from the on-disk dict shape."""
        companies = [
            PeerCompany.model_validate(company)
            for company in raw.get("companies", [])
        ]
        return cls(
            drhp_id=raw["drhp_id"],
            computed_at=raw["computed_at"],
            as_of=raw["as_of"],
            peer_set=_load_peer_set(raw["peer_set"]),
            companies=companies,
        )

    @classmethod
    def from_json(cls, text: str) -> "PeerRecord":
        """Reconstruct a PeerRecord from a JSON string."""
        import json

        return cls.from_dict(json.loads(text))


def _dump_peer_set(value: GroundedAnswer | RefusalResponse) -> dict:
    """Serialize the peer-SET value to its on-disk dict form.

    Mirrors agent.redflag_schema._dump_field_value — the {"refusal": ...} wrapper.
    """
    if isinstance(value, RefusalResponse):
        return {"refusal": value.model_dump()}
    return value.model_dump()


def _load_peer_set(raw: dict) -> GroundedAnswer | RefusalResponse:
    """Reconstruct the peer-SET value from its on-disk dict form.

    Discriminator: a dict with a "refusal" key is a RefusalResponse wrapper;
    anything else is a GroundedAnswer dump (it always carries "answer_prose").
    Mirrors agent.redflag_schema._load_field_value.
    """
    if "refusal" in raw:
        return RefusalResponse.model_validate(raw["refusal"])
    return GroundedAnswer.model_validate(raw)
