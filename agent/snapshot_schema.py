"""
agent/snapshot_schema.py — SnapshotRecord, the Wave 3 snapshot cache schema.

Per 02-04-PLAN.md Task 1: each of the 6 snapshot fields is stored as EITHER a
serialized `GroundedAnswer` (claim_id-bearing, cited) OR a `RefusalResponse`
(honest "not disclosed" — critical for SNAP-07 pledging). Both classes are
reused verbatim from agent/schemas.py — no field renames, no new citation
shape (Phase 3 METHOD-01 depends on the locked GroundedAnswer/Claim contract).

On-disk shape (data/snapshots/<drhp_id>.json):
{
  "drhp_id": "swiggy_2024_11",
  "computed_at": "2026-06-23T00:00:00Z",
  "fields": {
    "metadata": { ...GroundedAnswer.model_dump()... },
    "promoter": { "refusal": { ...RefusalResponse.model_dump()... } },
    ...
  },
  "ofs_fresh": {"ofs_pct": 30.0, "fresh_pct": 70.0} | null
}

A field dict containing the "refusal" key is reconstructed as a
RefusalResponse; any other field dict is reconstructed as a GroundedAnswer.
This discriminator is unambiguous because GroundedAnswer.model_dump() always
contains "answer_prose"/"claims" keys and never a top-level "refusal" key.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from agent.schemas import GroundedAnswer, RefusalResponse

# The 6 contract field keys — kept in sync with pipelines.snapshot_queries.SNAPSHOT_QUERIES.
SNAPSHOT_FIELD_KEYS: frozenset[str] = frozenset(
    {"metadata", "business", "financials", "risks", "use_of_proceeds", "promoter"}
)


def _dump_field(value: GroundedAnswer | RefusalResponse) -> dict:
    """Serialize one snapshot field to its on-disk dict form."""
    if isinstance(value, RefusalResponse):
        return {"refusal": value.model_dump()}
    return value.model_dump()


def _load_field(raw: dict) -> GroundedAnswer | RefusalResponse:
    """Reconstruct one snapshot field from its on-disk dict form.

    Discriminator: a dict with a "refusal" key is a RefusalResponse wrapper;
    anything else is a GroundedAnswer dump (it always carries "answer_prose").
    """
    if "refusal" in raw:
        return RefusalResponse.model_validate(raw["refusal"])
    return GroundedAnswer.model_validate(raw)


class SnapshotRecord(BaseModel):
    """The pre-computed 6-field snapshot cache record for one drhp_id.

    fields: dict[field_key -> GroundedAnswer | RefusalResponse]. Pydantic does
    not natively support this on-disk union shape (GroundedAnswer has no
    discriminator field of its own — changing that schema is out of scope per
    the locked-schema note in agent/schemas.py), so SnapshotRecord stores the
    reconstructed Python objects in `fields` and provides to_json()/from_json()
    helpers that apply the {"refusal": ...} wrapper convention on (de)serialize.
    """

    drhp_id: str
    computed_at: str
    fields: dict[str, GroundedAnswer | RefusalResponse] = Field(default_factory=dict)
    ofs_fresh: dict | None = None

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("fields")
    @classmethod
    def fields_keys_known(
        cls, v: dict[str, GroundedAnswer | RefusalResponse]
    ) -> dict[str, GroundedAnswer | RefusalResponse]:
        """Reject field keys outside the locked 6-key snapshot contract."""
        unknown = set(v.keys()) - SNAPSHOT_FIELD_KEYS
        if unknown:
            raise ValueError(
                f"Unknown snapshot field key(s): {sorted(unknown)}; "
                f"must be a subset of {sorted(SNAPSHOT_FIELD_KEYS)}"
            )
        return v

    def to_dict(self) -> dict:
        """Serialize to the on-disk dict shape (the {"refusal": ...} wrapper convention)."""
        return {
            "drhp_id": self.drhp_id,
            "computed_at": self.computed_at,
            "fields": {key: _dump_field(value) for key, value in self.fields.items()},
            "ofs_fresh": self.ofs_fresh,
        }

    def to_json(self) -> str:
        """Serialize to a JSON string (indent=2 — diff-reviewable per RESEARCH §3)."""
        import json

        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, raw: dict) -> "SnapshotRecord":
        """Reconstruct a SnapshotRecord from the on-disk dict shape."""
        fields = {key: _load_field(value) for key, value in raw.get("fields", {}).items()}
        return cls(
            drhp_id=raw["drhp_id"],
            computed_at=raw["computed_at"],
            fields=fields,
            ofs_fresh=raw.get("ofs_fresh"),
        )

    @classmethod
    def from_json(cls, text: str) -> "SnapshotRecord":
        """Reconstruct a SnapshotRecord from a JSON string."""
        import json

        return cls.from_dict(json.loads(text))
