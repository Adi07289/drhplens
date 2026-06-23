"""
data/catalogue_loader.py — Validated loader for data/catalogue.json + the
drhp_id allow-list (V5 security control).

Threat model (02-02-PLAN.md threat register):
  T-02-V5: drhp_id from session/query-param is untrusted until checked against
  this allow-list. is_known_drhp_id() MUST be called BEFORE any
  storage.vector.search(drhp_id=...) call — never pass raw user input to the
  Qdrant filter.
  T-02-02: catalogue.json itself is repo-committed, PR-reviewed, trusted
  config — the Pydantic model validates each row so a malformed entry fails
  fast at load time, not at query time.

This module is read by both the agent (agent/nodes/retrieve.py) and the
(Wave 4) Streamlit UI.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

CATALOGUE_PATH: Path = Path(__file__).parent / "catalogue.json"


class CatalogueIPO(BaseModel):
    """One curated IPO row from data/catalogue.json.

    Field names mirror the catalogue.json schema established in Wave 0
    (the Swiggy row is the canonical shape).
    """

    drhp_id: str
    issuer: str
    sector: str
    listing_date: str
    issue_size_cr: int | None = None
    doc_type: Literal["DRHP", "RHP", "Prospectus"]
    fresh_vs_ofs: dict | None = None
    lead_managers: list[str] = Field(default_factory=list)
    source_url: str
    source_sha256: str | None = None
    front_matter_pages: int = 20
    snapshot_path: str
    status: Literal["listed", "open"]


@lru_cache(maxsize=1)
def load_catalogue() -> list[CatalogueIPO]:
    """Load + validate data/catalogue.json into a list of CatalogueIPO models.

    Cached via lru_cache — catalogue.json is repo-committed, trusted config
    that does not change at runtime.

    Returns:
        List of validated CatalogueIPO models, in catalogue.json order.

    Raises:
        FileNotFoundError: if catalogue.json is missing.
        pydantic.ValidationError: if any row fails schema validation.
    """
    raw = json.loads(CATALOGUE_PATH.read_text())
    return [CatalogueIPO.model_validate(row) for row in raw["ipos"]]


@lru_cache(maxsize=1)
def _known_drhp_ids() -> frozenset[str]:
    """Return the set of valid drhp_ids from the loaded catalogue."""
    return frozenset(ipo.drhp_id for ipo in load_catalogue())


def is_known_drhp_id(drhp_id: str) -> bool:
    """V5 allow-list check — True iff drhp_id is a known catalogue entry.

    This is the control that MUST gate every drhp_id before it reaches
    storage.vector.search(). Any string not in the catalogue (including
    injection attempts, typos, or unrelated values) returns False.

    Args:
        drhp_id: The candidate drhp_id to validate.

    Returns:
        True iff drhp_id exactly matches a catalogue.json entry's drhp_id.
    """
    return drhp_id in _known_drhp_ids()
