"""
Unit tests — the in-process semantic tool-result cache (D-06).

Deterministic + offline: a FAKE `embed` maps known strings to fixed small vectors
(so cosine similarity is exactly controllable) and a COUNTING `compute` records how
many times the quota-scarce work actually ran. Pins the D-06 contract:
  - an identical question hits the cache (compute called ONCE);
  - a question above DEDUP_THRESHOLD dedups (compute once) while one below it does
    not (compute twice);
  - an entry older than CACHE_TTL_S is swept on the next access (TTL, mock clock);
  - two different drhp_ids keep DISJOINT buckets (no cross-IPO leakage, Pitfall #5).
"""
from __future__ import annotations

import pytest

import agent.cache.semantic_cache as sc
from agent.cache.semantic_cache import cached_answer
from agent.policies import CACHE_TTL_S, DEDUP_THRESHOLD

# Fixed vectors: identical text -> identical vec; SIMILAR pair has cos ~0.999
# (>= 0.95 DEDUP_THRESHOLD); the DISSIMILAR vector is orthogonal (cos 0 < 0.95).
_VECS = {
    "what is the forecast?": [1.0, 0.0, 0.0],
    "what's the forecast?": [0.999, 0.0447, 0.0],   # cos ~0.999 vs the first
    "tell me about the peers": [0.0, 1.0, 0.0],       # orthogonal -> cos 0
}


def _embed(text: str) -> list[float]:
    return list(_VECS[text])


class _Counter:
    """A compute() stub that counts calls and returns a fixed value."""

    def __init__(self, value):
        self.value = value
        self.n = 0

    def __call__(self):
        self.n += 1
        return self.value


@pytest.fixture(autouse=True)
def _clear_store():
    """Each test starts from an empty cache (best-effort store, no durability)."""
    sc.clear()
    yield
    sc.clear()


def test_identical_question_hits_cache_compute_once():
    compute = _Counter({"answer": "A"})
    v1 = cached_answer("swiggy_2024_11", "what is the forecast?", _embed, compute)
    v2 = cached_answer("swiggy_2024_11", "what is the forecast?", _embed, compute)
    assert v1 == v2 == {"answer": "A"}
    assert compute.n == 1                       # second call served from cache


def test_similar_dedups_dissimilar_does_not():
    # SIMILAR (cos >= DEDUP_THRESHOLD) -> compute once for the pair.
    compute_sim = _Counter({"answer": "sim"})
    cached_answer("swiggy_2024_11", "what is the forecast?", _embed, compute_sim)
    hit = cached_answer("swiggy_2024_11", "what's the forecast?", _embed, compute_sim)
    assert hit == {"answer": "sim"}
    assert compute_sim.n == 1

    # DISSIMILAR (cos < DEDUP_THRESHOLD) -> compute a SECOND time.
    miss = cached_answer("swiggy_2024_11", "tell me about the peers", _embed, compute_sim)
    assert miss == {"answer": "sim"}            # value from THIS compute call
    assert compute_sim.n == 2


def test_entry_past_ttl_is_swept(monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr(sc, "_now", lambda: clock["t"])

    compute = _Counter({"answer": "ttl"})
    cached_answer("swiggy_2024_11", "what is the forecast?", _embed, compute)
    assert compute.n == 1

    # advance past the TTL -> the stale entry is swept, compute runs again.
    clock["t"] = 1000.0 + CACHE_TTL_S + 1
    cached_answer("swiggy_2024_11", "what is the forecast?", _embed, compute)
    assert compute.n == 2

    # a within-TTL access does NOT sweep (sanity on the boundary).
    clock["t"] = clock["t"] + (CACHE_TTL_S - 1)
    cached_answer("swiggy_2024_11", "what is the forecast?", _embed, compute)
    assert compute.n == 2


def test_different_drhp_ids_keep_disjoint_buckets():
    compute = _Counter({"answer": "iso"})
    cached_answer("swiggy_2024_11", "what is the forecast?", _embed, compute)
    # SAME question text, DIFFERENT ipo -> must NOT hit swiggy's entry.
    cached_answer("hyundai_2024_10", "what is the forecast?", _embed, compute)
    assert compute.n == 2                       # no cross-IPO leak (Pitfall #5)

    # and each bucket now serves its own hit.
    cached_answer("swiggy_2024_11", "what is the forecast?", _embed, compute)
    cached_answer("hyundai_2024_10", "what is the forecast?", _embed, compute)
    assert compute.n == 2


def test_reads_policy_constants_not_magic_numbers():
    # The thresholds are the single-source policy constants (no local re-definition).
    assert 0.0 < DEDUP_THRESHOLD <= 1.0
    assert CACHE_TTL_S > 0
