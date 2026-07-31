"""Unit tests for the pinned EvalSummary schema — the eval_summary.json UI contract.

The schema (AI-SPEC §4b; design doc §4.3) is the contract crossing from the trusted
runner to the inline renderer + the release gate. Changing a field name is a breaking
change these tests must catch. Load-bearing invariants:
  - honesty: an empty ``judge_model`` is rejected (never a figure without a named judge);
  - ``faithfulness_deepeval`` accepts the -1.0 "not measured" sentinel but nothing else <0;
  - gated metrics stay in [0, 1]; ``n_questions`` > 0; ``per_ipo`` defaults to {}.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from eval.metrics import EvalSummary as EvalSummaryFromPackage
from eval.metrics.schema import Aggregate, Corpus, EvalSummary


def _valid_aggregate() -> dict:
    return {
        "faithfulness_deepeval": 1.0,
        "citation_accuracy": 1.0,
        "recall_at_5": 1.0,
        "recall_at_10": 1.0,
        "recall_at_30": 1.0,
    }


def _valid_summary() -> dict:
    """A well-formed summary mirroring design doc §4.3 (per_ipo values are Aggregate)."""
    return {
        "generated": "2026-07-28",
        "judge_model": "gemini-3.5-flash",
        "corpus": {
            "gold_set": "tests/eval/gold_set.jsonl",
            "ipo": "Swiggy DRHP",
            "n_questions": 13,
        },
        "aggregate": _valid_aggregate(),
        "per_ipo": {"swiggy_2024_11": _valid_aggregate()},
        "report": "eval/reports/2026-07-28-rag-eval.md",
    }


def test_wellformed_summary_validates_and_round_trips_byte_stably():
    m = EvalSummary.model_validate(_valid_summary())
    j1 = m.model_dump_json(indent=2)
    m2 = EvalSummary.model_validate_json(j1)
    j2 = m2.model_dump_json(indent=2)
    assert j1 == j2  # byte-stable round-trip through the pinned model


def test_package_reexports_the_same_evalsummary():
    assert EvalSummaryFromPackage is EvalSummary


def test_corpus_and_aggregate_parse_as_models():
    m = EvalSummary.model_validate(_valid_summary())
    assert isinstance(m.corpus, Corpus)
    assert m.corpus.n_questions == 13
    assert isinstance(m.aggregate, Aggregate)


def test_empty_judge_model_is_rejected():
    data = _valid_summary()
    data["judge_model"] = ""
    with pytest.raises(ValidationError):
        EvalSummary.model_validate(data)


def test_faithfulness_accepts_not_measured_sentinel():
    data = _valid_summary()
    data["aggregate"]["faithfulness_deepeval"] = -1.0
    m = EvalSummary.model_validate(data)
    assert m.aggregate.faithfulness_deepeval == -1.0


@pytest.mark.parametrize("bad", [-2.0, 1.5])
def test_faithfulness_rejects_out_of_bounds(bad):
    data = _valid_summary()
    data["aggregate"]["faithfulness_deepeval"] = bad
    with pytest.raises(ValidationError):
        EvalSummary.model_validate(data)


@pytest.mark.parametrize(
    "field", ["citation_accuracy", "recall_at_5", "recall_at_10", "recall_at_30"]
)
@pytest.mark.parametrize("bad", [-0.01, 1.01])
def test_gated_metrics_reject_values_outside_unit_range(field, bad):
    data = _valid_summary()
    data["aggregate"][field] = bad
    with pytest.raises(ValidationError):
        EvalSummary.model_validate(data)


def test_per_ipo_defaults_to_empty_dict():
    data = _valid_summary()
    del data["per_ipo"]
    m = EvalSummary.model_validate(data)
    assert m.per_ipo == {}


def test_per_ipo_values_validate_as_aggregate():
    m = EvalSummary.model_validate(_valid_summary())
    assert isinstance(m.per_ipo["swiggy_2024_11"], Aggregate)
    bad = _valid_summary()
    bad["per_ipo"]["swiggy_2024_11"]["citation_accuracy"] = 2.0
    with pytest.raises(ValidationError):
        EvalSummary.model_validate(bad)


def test_n_questions_must_be_positive():
    data = _valid_summary()
    data["corpus"]["n_questions"] = 0
    with pytest.raises(ValidationError):
        EvalSummary.model_validate(data)
