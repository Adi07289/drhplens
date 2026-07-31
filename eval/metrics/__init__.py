"""eval.metrics — the ONE deterministic-metric implementation for DRHPLens RAG eval.

Both the eval runner (``scripts/run_eval.py``, 06.1-04) and the release gate
(``scripts/release_gate.py``, 06.1-05) import these pure functions so the committed
``eval_summary.json`` report and the CI gate can never diverge — mirroring how
``compute_numeric_faithfulness`` is already the single importable numeric implementation.

The one non-deterministic member — ``faithfulness_deepeval`` (DeepEval LLM-judge on a native
Gemini judge) — is REPORTED, never gated: it measures (records) and never raises on a low
score, returning the ``-1`` "not measured" sentinel on infra failure. The deterministic
``recall_at_k`` / ``citation_accuracy`` carry the release gate.

Exports: ``recall_at_k``, ``citation_accuracy``, ``faithfulness_deepeval``, ``EvalSummary``
(plus ``Aggregate`` / ``Corpus`` for callers that validate per-IPO blocks directly).
"""
from __future__ import annotations

from eval.metrics.citation import citation_accuracy
from eval.metrics.faithfulness_deepeval import faithfulness_deepeval
from eval.metrics.recall import recall_at_k
from eval.metrics.schema import Aggregate, Corpus, EvalSummary

__all__ = [
    "recall_at_k",
    "citation_accuracy",
    "faithfulness_deepeval",
    "EvalSummary",
    "Aggregate",
    "Corpus",
]
