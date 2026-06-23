"""
Unit test — data/catalogue.json loads + validates against schema (no threat).

Requirement: SNAP-01, OPS-01. Threat: none (trusted repo config; see threat
register T-02-02 in 02-02-PLAN.md — accept, PR-reviewed).
Secure behavior: catalogue.json loads + validates against schema; all entries
have required fields.

Wave 1 implementation (02-VALIDATION.md row "2-catalogue-loader").
"""
from __future__ import annotations

from data.catalogue_loader import CatalogueIPO, load_catalogue

EXPECTED_DRHP_IDS = {
    "swiggy_2024_11",
    "hyundai_2024_10",
    "ola_electric_2024_08",
    "zomato_2021_07",
    "nykaa_2021_10",
    "paytm_2021_11",
    "lic_2022_05",
    "honasa_2023_11",
}


def test_catalogue_loads_and_validates_schema() -> None:
    """load_catalogue() returns a list of validated IPO models with all required fields."""
    load_catalogue.cache_clear()
    ipos = load_catalogue()

    assert len(ipos) > 0
    for ipo in ipos:
        assert isinstance(ipo, CatalogueIPO)
        assert ipo.drhp_id
        assert ipo.issuer
        assert ipo.sector
        assert ipo.listing_date
        assert ipo.doc_type in ("DRHP", "RHP", "Prospectus")
        assert ipo.source_url
        assert ipo.front_matter_pages > 0
        assert ipo.snapshot_path
        assert ipo.status in ("listed", "open")


def test_catalogue_contains_exactly_the_8_curated_ipos() -> None:
    """load_catalogue() contains exactly the 8 curated drhp_ids."""
    load_catalogue.cache_clear()
    ipos = load_catalogue()

    actual_ids = {ipo.drhp_id for ipo in ipos}
    assert actual_ids == EXPECTED_DRHP_IDS
    assert len(ipos) == 8
