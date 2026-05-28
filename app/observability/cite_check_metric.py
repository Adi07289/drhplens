"""
app/observability/cite_check_metric.py — Custom Langfuse faithfulness score.

Logs a `faithfulness_via_cite_check` score to Langfuse after the cite_check node
completes. Score is 1.0 if all claims are grounded, 0.0 if any claim is unsupported.

Per plan: this is the Wave-5 piece of the EVAL-01 baseline measurement.
Phase 1 measures; Phase 3 EVAL-03 and Phase 6 EVAL-01 release-gate against the
running mean of this score.

No-op when LANGFUSE_PUBLIC_KEY is unset (local dev / CI without credentials).
"""
from __future__ import annotations

import json

from app.observability.langfuse_client import get_client, is_enabled


def score_cite_check(
    trace_id: str,
    all_grounded: bool,
    per_claim_results: list[dict],
) -> None:
    """Log a faithfulness_via_cite_check custom score to Langfuse.

    Called by agent/nodes/cite_check.py after the deterministic check completes.
    The score is claim-level faithfulness: 1.0 = all grounded, 0.0 = any unsupported.

    Args:
        trace_id: Langfuse trace_id for this agent run.
        all_grounded: True iff every claim passed the cite-check.
        per_claim_results: List of dicts, one per claim, with keys:
            claim_id, grounded (bool), failure_reason (str or None).
            Truncated to 1000 chars in the Langfuse comment field.
    """
    if not is_enabled():
        return

    client = get_client()
    if client is None:
        return

    try:
        comment_text = json.dumps(per_claim_results)[:1000]
        client.score(
            trace_id=trace_id,
            name="faithfulness_via_cite_check",
            value=1.0 if all_grounded else 0.0,
            comment=comment_text,
        )
    except Exception:
        # Never let Langfuse errors crash the agent response path.
        pass
