"""eval.metrics — the ONE deterministic-metric implementation for DRHPLens RAG eval.

Both the eval runner (``scripts/run_eval.py``, 06.1-04) and the release gate
(``scripts/release_gate.py``, 06.1-05) import these pure functions so the committed
``eval_summary.json`` report and the CI gate can never diverge — mirroring how
``compute_numeric_faithfulness`` is already the single importable numeric implementation.

Exports: ``recall_at_k``, ``citation_accuracy``, ``EvalSummary`` (plus ``Aggregate`` /
``Corpus`` for callers that validate per-IPO blocks directly).
"""
from __future__ import annotations

from eval.metrics.citation import citation_accuracy
from eval.metrics.recall import recall_at_k
from eval.metrics.schema import Aggregate, Corpus, EvalSummary

__all__ = [
    "recall_at_k",
    "citation_accuracy",
    "EvalSummary",
    "Aggregate",
    "Corpus",
]
