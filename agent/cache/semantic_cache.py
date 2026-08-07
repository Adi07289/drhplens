"""
agent/cache/semantic_cache.py — in-process semantic tool-result cache (D-06).

WHAT THIS CACHES: the QUOTA-SCARCE LLM hops — classify / DRHP-RAG / synthesis —
keyed by the free-text SEMANTICS of the question. That is where semantic
similarity earns its keep: two near-identical questions should not each burn a
Gemini call against the tight free-tier RPD.

WHAT THIS DOES *NOT* CACHE: the deterministic static tool loaders
(`agent/tools/query_{peers,forecast,redflags}`). Their result is a pure function of
`(tool, drhp_id)` — a cheap committed-file read, NOT free text — so embedding them
into cosine similarity would be over-engineering (RESEARCH anti-pattern). Cache
those by an exact key or just re-read the file; never route them through here.

SCOPING / NO CROSS-IPO LEAK (RESEARCH Pitfall #5): every entry lives in a bucket
keyed by `drhp_id`. A lookup only ever compares against entries in the SAME
`drhp_id` bucket, so one IPO's cached answer can never be served for another —
no cross-IPO leakage by construction. The cache is independent of any LangGraph
`thread_id`, so it composes with the checkpointer (which isolates conversation
state per fresh `thread_id`) without interfering; sharing a grounded answer across
SESSIONS for the SAME IPO is safe and desired (answers are deterministic-grounded,
not personalized — no PII, no per-user state).

PERSISTENCE: best-effort, in-process only. It is LOST on an HF Spaces cold start
(`/tmp` is ephemeral). That is acceptable — this is a quota OPTIMIZER, not a source
of truth. Do NOT back it with a `/tmp` sqlite expecting durability.

The dedup threshold + TTL are the SINGLE-SOURCE policy constants
`agent.policies.DEDUP_THRESHOLD` / `agent.policies.CACHE_TTL_S` (no magic numbers
here). No new third-party package is added — the embedder is injected by the caller
(the already-loaded bge-m3 `st.cache_resource`).
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from typing import Callable

from agent.policies import CACHE_TTL_S, DEDUP_THRESHOLD


@dataclass
class _Entry:
    """One cached answer: its question embedding, the stored value, and its
    monotonic store timestamp (for the TTL sweep)."""

    vec: list[float]
    value: object
    ts: float


# Module-level store keyed by drhp_id -> live entries. Entries NEVER cross the
# IPO bucket (no cross-IPO leakage by construction, Pitfall #5).
_STORE: dict[str, list[_Entry]] = {}
_LOCK = threading.Lock()


def _now() -> float:
    """Monotonic clock (indirection so tests can mock it)."""
    return time.monotonic()


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two vectors; 0.0 for an empty or zero-norm vector."""
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def cached_answer(
    drhp_id: str,
    question: str,
    embed: Callable[[str], list[float]],
    compute: Callable[[], object],
) -> object:
    """Return a cached answer for a semantically-equivalent prior question, else compute.

    Sweeps the `drhp_id` bucket of entries older than `CACHE_TTL_S`, embeds the
    question via the injected `embed` (the reused bge-m3 embedder), and returns the
    stored value of the FIRST live entry whose cosine similarity to the question is
    >= `DEDUP_THRESHOLD` (a quota-saving hit). On a miss it calls `compute()` (the
    quota-scarce LLM run), stores `(vec, value, now)` under `drhp_id`, and returns it.

    Args:
        drhp_id: the IPO scope — its own bucket; entries never cross it (Pitfall #5).
        question: the free-text user question (the semantic key).
        embed: str -> vector; the reused bge-m3 `st.cache_resource` embedder.
        compute: () -> value; the quota-scarce work run only on a cache miss.

    Returns:
        The cached value on a semantic hit, otherwise the freshly computed value.
    """
    now = _now()
    query_vec = embed(question)

    with _LOCK:
        live = [e for e in _STORE.get(drhp_id, []) if now - e.ts < CACHE_TTL_S]
        _STORE[drhp_id] = live  # persist the TTL sweep
        for entry in live:
            if _cosine(query_vec, entry.vec) >= DEDUP_THRESHOLD:
                return entry.value  # quota-saving hit

    # Miss — run the quota-scarce work OUTSIDE the lock (compute may be slow), then
    # store. A concurrent duplicate compute is acceptable for a best-effort cache.
    value = compute()
    with _LOCK:
        _STORE.setdefault(drhp_id, []).append(_Entry(query_vec, value, now))
    return value


def clear() -> None:
    """Drop all cached entries. Best-effort cache: safe to call anytime (tests, or a
    manual flush). Not a durability boundary — the store is in-process only."""
    with _LOCK:
        _STORE.clear()


__all__ = ["cached_answer", "clear"]
