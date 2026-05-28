"""
Shared pytest fixtures for DRHPLens test suite.

Fixture names and signatures are LOCKED at Wave 0 (per 01-01-PLAN.md Task 3).
Later waves fill in the bodies — do NOT rename these fixtures.
Later tests import these names directly; renaming causes collection failures.

Wave assignment:
- fixture_synthetic_drhp_path: body filled in Wave 2 (creates tiny 5-page synthetic DRHP)
- mock_qdrant_client: body filled in Wave 2 (in-memory QdrantClient for unit tests)
- mock_llm: body filled in Wave 3 (canned GroundedAnswer-shaped JSON mock)
- gold_set: body filled in Wave 5 (loads tests/eval/gold_set.jsonl)
"""
from __future__ import annotations

import pathlib

import pytest


@pytest.fixture
def fixture_synthetic_drhp_path() -> pathlib.Path:
    """Return path to the tiny 5-page synthetic DRHP PDF used in integration tests.

    The PDF is committed at tests/fixtures/synthetic_drhp.pdf.
    Created by Wave 2 via pymupdf with 5 pages:
      page 0: Cover Page (Swiggy Limited / Prospectus / SEBI)
      page 1: Risk Factors
      page 2: Issue Size
      page 3: Promoter Background
      page 4: Financial Statements
    """
    pdf_path = pathlib.Path(__file__).parent / "fixtures" / "synthetic_drhp.pdf"
    if not pdf_path.exists():
        pytest.skip(reason="tests/fixtures/synthetic_drhp.pdf not found — run Wave 2 setup")
    return pdf_path


@pytest.fixture
def mock_qdrant_client():
    """Return an in-memory QdrantClient instance for unit/integration tests.

    Uses qdrant-client's ':memory:' mode so tests do not require a live Qdrant server.
    Collection setup (create_collection, upsert) happens per-test as needed.

    Wave 2 implementation: uses QdrantClient(':memory:') for fully in-process testing.
    """
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        pytest.skip(reason="qdrant-client not installed — install Wave 2 deps")

    c = QdrantClient(":memory:")
    yield c
    c.close()


@pytest.fixture
def mock_llm():
    """Return a Mock whose interface matches Instructor-wrapped LLM responses.

    The mock's `chat.completions.create` returns a canned GroundedAnswer-shaped JSON
    matching the agent/schemas.py contract (claim_id, sources, answer_prose).

    Wave 0 stub: skipped because agent/schemas.py does not exist yet.
    Wave 3 fills the body alongside the generate node implementation.
    """
    pytest.skip(reason="Wave 3 implements agent/schemas.py and wires the mock LLM fixture")


@pytest.fixture
def gold_set() -> list[dict]:
    """Load tests/eval/gold_set.jsonl line-by-line as a list of dicts.

    Each entry is a JSON object with keys:
        qid, category, question, expected_answer_contains, expected_sources, is_refusal_expected

    Wave 0 stub: skipped because gold_set.jsonl contains only schema-stub entries.
    Wave 5 populates the gold set and removes the skip so eval tests run.
    """
    pytest.skip(reason="Wave 5 populates tests/eval/gold_set.jsonl and fills this fixture")
