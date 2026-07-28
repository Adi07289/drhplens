"""eval.metrics — the ONE deterministic-metric implementation for DRHPLens RAG eval.

Both the eval runner (``scripts/run_eval.py``, 06.1-04) and the release gate
(``scripts/release_gate.py``, 06.1-05) import these pure functions so the committed
``eval_summary.json`` report and the CI gate can never diverge — mirroring how
``compute_numeric_faithfulness`` is already the single importable numeric implementation.

Exports (wired in 06.1-01 Task 3): ``recall_at_k``, ``citation_accuracy``, ``EvalSummary``.
"""
