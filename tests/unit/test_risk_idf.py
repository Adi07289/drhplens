"""
Unit test — in-corpus IDF risk specificity (P12 / D3-14): issuer-specific risks
rank above boilerplate; the hand-curated boilerplate floor clamps a matching
phrase to the bottom band regardless of IDF.

Requirement: P12 mitigation. Plan 03 implements pipelines/risk_idf.py.
Function names test_issuer_specific_ranks_above_boilerplate /
test_boilerplate_floor_clamps are LOCKED (Wave 0 scaffold, 03-01).

The 3-doc corpus mirrors the idf_corpus_3doc fixture (kept local here because
tests/eval/conftest fixtures are not visible across the unit<->eval boundary).
Fully offline: stdlib + rapidfuzz only.
"""
from __future__ import annotations

from agent.redflag_schema import RankedRisk

# Docs 0 and 1 share a boilerplate phrase; doc 2 is issuer-unique (mirror of the
# idf_corpus_3doc eval fixture).
_BOILERPLATE = "Our business is subject to extensive government regulation."
CORPUS_3DOC = [
    f"{_BOILERPLATE} We may be unable to obtain or renew required licences.",
    f"{_BOILERPLATE} Changes in tax law could adversely affect operations.",
    (
        "A single anchor customer accounted for 62% of fiscal 2024 revenue, "
        "and the loss of this customer would materially harm our business."
    ),
]


def test_issuer_specific_ranks_above_boilerplate() -> None:
    """A risk with unique (high-IDF) terms ranks above a shared-boilerplate risk."""
    from pipelines.risk_idf import rank_risks

    risk_claims = [
        (
            "c_unique1",
            "A single anchor customer accounted for 62% of fiscal 2024 revenue.",
        ),
        ("c_boiler1", "Our business is subject to extensive government regulation."),
    ]

    ranked = rank_risks(risk_claims, CORPUS_3DOC)

    assert isinstance(ranked, list)
    assert all(isinstance(r, RankedRisk) for r in ranked)
    # Sorted by descending idf_score.
    scores = [r.idf_score for r in ranked]
    assert scores == sorted(scores, reverse=True)
    # The unique issuer-specific risk outranks the shared boilerplate one.
    order = [r.claim_id for r in ranked]
    assert order.index("c_unique1") < order.index("c_boiler1")


def test_boilerplate_floor_clamps() -> None:
    """A risk matching a boilerplate-floor phrase (token_set_ratio >=
    IDF_BOILERPLATE_FUZZ_THRESHOLD) clamps to the industry_standard band,
    regardless of its IDF score."""
    from pipelines.risk_idf import rank_risks

    # This phrase matches a line in eval/gold/boilerplate_phrases.txt — it must
    # be clamped to the bottom band even if its in-corpus IDF is high.
    risk_claims = [
        (
            "c_boilerfloor",
            "The company is subject to extensive government regulation and "
            "changes in regulatory policy.",
        ),
    ]
    # A corpus where this phrase is unique (would otherwise score HIGH IDF).
    corpus = [
        "An unrelated risk about foreign exchange exposure on imports.",
        "An unrelated risk about seasonality of demand in the retail segment.",
    ]

    ranked = rank_risks(risk_claims, corpus)

    assert len(ranked) == 1
    assert ranked[0].specificity_band == "industry_standard"
