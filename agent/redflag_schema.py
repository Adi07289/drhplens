"""
agent/redflag_schema.py — RedFlagRecord, the Phase 3 red-flag cache schema.

Per 03-01-PLAN.md Task 1: an EXACT mirror of agent/snapshot_schema.py. Each of
the 7 canonical red-flag fields is stored as a `RedFlagField` whose `value` is
EITHER a serialized `GroundedAnswer` (claim_id-bearing, cited) OR a
`RefusalResponse` (honest "Not disclosed in DRHP" — D3-03). Both classes are
reused verbatim from agent/schemas.py — no field renames, no new citation shape
(Phase 3 METHOD-01 + the chip renderer depend on the locked GroundedAnswer/Claim
contract and the claim_id regex r'^c_[a-z0-9]{6,16}$').

The on-disk field codec is the SAME {"refusal": ...} discriminator convention as
SnapshotRecord — copied, not reinvented (03-PATTERNS.md §"Union-discriminator
cache codec").

On-disk shape (data/redflag/<drhp_id>.json):
{
  "drhp_id": "swiggy_2024_11",
  "computed_at": "2026-06-25T00:00:00Z",
  "fields": {
    "rpt_pct": {"value": { ...GroundedAnswer.model_dump()... },
                "confidence_tier": "high", "confidence_score": 0.9},
    "promoter_pledge_pct": {"value": {"refusal": { ...RefusalResponse.model_dump()... }},
                            "confidence_tier": null, "confidence_score": null},
    ...
  },
  "ranked_risks": [
    {"claim_id": "c_abc123", "idf_score": 4.2, "specificity_band": "issuer_specific"},
    ...
  ]
}

A field's `value` dict containing the "refusal" key is reconstructed as a
RefusalResponse; any other value dict is reconstructed as a GroundedAnswer.
This discriminator is unambiguous because GroundedAnswer.model_dump() always
contains "answer_prose"/"claims" keys and never a top-level "refusal" key.

Cache path convention: data/redflag/<drhp_id>.json (a new directory mirroring
data/snapshots/). This module does NOT create the directory and does NOT
interpolate any untrusted id into a path — STRIDE T-03-01: write/read-time path
construction (Plans 03/04) MUST gate <drhp_id> through the existing Phase 2
`is_known_drhp_id` allow-list (data/catalogue_loader.py) before forming a path.

D3-02/D3-03 invariants:
  - confidence_tier is None when a field is not-disclosed (a RefusalResponse value).
  - confidence_score (0.00-1.00) is surfaced ONLY in the methodology pane.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from agent.schemas import GroundedAnswer, RefusalResponse

# The 7 canonical red-flag field keys, in the UI-SPEC R-1 fixed order — kept in
# sync with pipelines.redflag_queries.REDFLAG_QUERIES (the key_links contract:
# REDFLAG_QUERIES keys == this allow-list).
REDFLAG_FIELD_KEYS: frozenset[str] = frozenset(
    {
        "rpt_pct",
        "ofs_vs_fresh",
        "promoter_pledge_pct",
        "customer_concentration",
        "auditor_history",
        "debt_trajectory",
        "going_concern",
    }
)


def _dump_field_value(value: GroundedAnswer | RefusalResponse) -> dict:
    """Serialize one red-flag field's value to its on-disk dict form.

    Mirrors agent.snapshot_schema._dump_field — the {"refusal": ...} wrapper.
    """
    if isinstance(value, RefusalResponse):
        return {"refusal": value.model_dump()}
    return value.model_dump()


def _load_field_value(raw: dict) -> GroundedAnswer | RefusalResponse:
    """Reconstruct one red-flag field's value from its on-disk dict form.

    Discriminator: a dict with a "refusal" key is a RefusalResponse wrapper;
    anything else is a GroundedAnswer dump (it always carries "answer_prose").
    Mirrors agent.snapshot_schema._load_field.
    """
    if "refusal" in raw:
        return RefusalResponse.model_validate(raw["refusal"])
    return GroundedAnswer.model_validate(raw)


class RedFlagField(BaseModel):
    """One red-flag table field: a cited value plus its derived confidence.

    value: a GroundedAnswer (cited, claim_id-bearing) OR a RefusalResponse
    ("Not disclosed in DRHP", D3-03 — absence is an honest signal).

    confidence_tier: high/medium/low per the deterministic source-grounding
    rubric (D3-01). None when the field is not-disclosed (a RefusalResponse
    value carries no confidence — D3-03).

    confidence_score: 0.00-1.00, the numeric behind the tier, surfaced ONLY in
    the methodology pane (D3-02). None for a not-disclosed field.
    """

    value: GroundedAnswer | RefusalResponse
    confidence_tier: Literal["high", "medium", "low"] | None = None
    confidence_score: float | None = None


class RankedRisk(BaseModel):
    """One ranked risk in the IDF-ordered single risk list (D3-15).

    claim_id: references the GroundedAnswer.Claim this risk derives from (the
    locked claim_id contract — the methodology pane reads per-claim traces).
    idf_score: in-corpus IDF specificity score; higher = more issuer-specific.
    specificity_band: the neutral UI band (no red/green) — issuer-specific
    foregrounded by rank (D3-14/D3-15).
    """

    claim_id: str
    idf_score: float
    specificity_band: Literal[
        "issuer_specific", "mostly_issuer_specific", "industry_standard"
    ]


class RedFlagRecord(BaseModel):
    """The pre-computed 7-field red-flag cache record for one drhp_id.

    Mirrors SnapshotRecord (agent/snapshot_schema.py): fields is a
    dict[field_key -> RedFlagField], (de)serialized with the {"refusal": ...}
    wrapper convention via to_dict()/from_dict(). ranked_risks is the single
    IDF-ordered risk list (descending idf_score, D3-15).
    """

    drhp_id: str
    computed_at: str
    fields: dict[str, RedFlagField] = Field(default_factory=dict)
    ranked_risks: list[RankedRisk] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("fields")
    @classmethod
    def fields_keys_known(
        cls, v: dict[str, RedFlagField]
    ) -> dict[str, RedFlagField]:
        """Reject field keys outside the locked 7-key red-flag contract.

        STRIDE T-03-02: rejects unknown/hostile keys at schema validation time;
        the value-level GroundedAnswer/Claim validators (claim_id regex,
        span_offsets start<=end) are reused verbatim and reject malformed dicts.
        """
        unknown = set(v.keys()) - REDFLAG_FIELD_KEYS
        if unknown:
            raise ValueError(
                f"Unknown red-flag field key(s): {sorted(unknown)}; "
                f"must be a subset of {sorted(REDFLAG_FIELD_KEYS)}"
            )
        return v

    def to_dict(self) -> dict:
        """Serialize to the on-disk dict shape (the {"refusal": ...} convention)."""
        return {
            "drhp_id": self.drhp_id,
            "computed_at": self.computed_at,
            "fields": {
                key: {
                    "value": _dump_field_value(field.value),
                    "confidence_tier": field.confidence_tier,
                    "confidence_score": field.confidence_score,
                }
                for key, field in self.fields.items()
            },
            "ranked_risks": [risk.model_dump() for risk in self.ranked_risks],
        }

    def to_json(self) -> str:
        """Serialize to a JSON string (indent=2 — diff-reviewable per RESEARCH §3)."""
        import json

        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, raw: dict) -> "RedFlagRecord":
        """Reconstruct a RedFlagRecord from the on-disk dict shape."""
        fields = {
            key: RedFlagField(
                value=_load_field_value(field["value"]),
                confidence_tier=field.get("confidence_tier"),
                confidence_score=field.get("confidence_score"),
            )
            for key, field in raw.get("fields", {}).items()
        }
        ranked_risks = [
            RankedRisk.model_validate(risk) for risk in raw.get("ranked_risks", [])
        ]
        return cls(
            drhp_id=raw["drhp_id"],
            computed_at=raw["computed_at"],
            fields=fields,
            ranked_risks=ranked_risks,
        )

    @classmethod
    def from_json(cls, text: str) -> "RedFlagRecord":
        """Reconstruct a RedFlagRecord from a JSON string."""
        import json

        return cls.from_dict(json.loads(text))
