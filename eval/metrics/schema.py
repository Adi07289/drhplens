"""eval.metrics.schema — the pinned EvalSummary Pydantic model (the UI contract).

The committed ``eval/reports/eval_summary.json`` IS this structured output. It is validated
at write time by the runner (06.1-04) and re-checked at read time by the inline renderer
(06.1-02) and the release gate (06.1-05), so the report and the gate can never diverge.
Defined EXACTLY per AI-SPEC §4b / design doc §4.3.

Load-bearing invariants (threat register T-6.1-02 / T-6.1-03):
  - honesty: ``_named_judge`` forbids an empty ``judge_model`` — never surface a figure
    without naming the judge (provenance / SEBI AI-disclosure posture);
  - ``faithfulness_deepeval`` is bounded [-1.0, 1.0] where -1.0 is the ONLY sub-zero value,
    the documented "not measured" sentinel (rate-limited / key unset), never a real 0.0;
  - the GATED metrics (``citation_accuracy``, ``recall_at_5/10/30``) stay in [0.0, 1.0].
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Aggregate(BaseModel):
    """The aggregate metric block (and each per-IPO block)."""

    faithfulness_deepeval: float = Field(ge=-1.0, le=1.0)  # -1 = not measured (report-only)
    citation_accuracy: float = Field(ge=0.0, le=1.0)  # GATED >= 0.95
    recall_at_5: float = Field(ge=0.0, le=1.0)
    recall_at_10: float = Field(ge=0.0, le=1.0)  # GATED >= 0.85 (labelled regression floor)
    recall_at_30: float = Field(ge=0.0, le=1.0)


class Corpus(BaseModel):
    """Provenance of the gold set the figures were measured over."""

    gold_set: str
    ipo: str
    n_questions: int = Field(gt=0)


class EvalSummary(BaseModel):
    """The pinned eval_summary.json contract read by the UI and the release gate."""

    generated: str  # ISO date
    judge_model: str  # provenance, e.g. "gemini-3.5-flash"
    corpus: Corpus
    aggregate: Aggregate
    per_ipo: dict[str, Aggregate] = {}  # only IPOs with a real gold set
    report: str  # path to the .md report

    @field_validator("judge_model")
    @classmethod
    def _named_judge(cls, v: str) -> str:
        """Honesty invariant: never surface a figure without a named judge."""
        if not v:
            raise ValueError("judge_model is required for provenance")
        return v
