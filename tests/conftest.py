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
    """Return path to a tiny 5-page synthetic DRHP PDF used in integration tests.

    The synthetic PDF is created by Wave 2 ingestion task at:
        tests/fixtures/synthetic_drhp.pdf

    Wave 0 stub: skipped because the file does not exist yet.
    Wave 2 will create the fixture file and remove the skip.
    """
    pytest.skip(reason="Wave 2 creates tests/fixtures/synthetic_drhp.pdf and fills this fixture")


@pytest.fixture
def mock_qdrant_client():
    """Return an in-memory QdrantClient instance for unit/integration tests.

    Uses qdrant-client's `:memory:` mode so tests do not require a live Qdrant server.
    Collection setup (create_collection, upsert) happens per-test as needed.

    Wave 0 stub: skipped because qdrant-client is not installed yet.
    Wave 2 will install qdrant-client and fill this fixture body.
    """
    pytest.skip(reason="Wave 2 installs qdrant-client and wires the in-memory client fixture")


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
