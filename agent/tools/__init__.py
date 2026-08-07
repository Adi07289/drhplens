"""
agent/tools/ — the read-only tool surface the bounded supervisor dispatches (D-01).

Three deterministic loader NODES — `query_peers`, `query_forecast` (with the
read-only GMP-vs-model gap fold, D-04), and `query_redflags` — each a plain
`SupervisorState`-in / `SupervisorState`-out function in the exact shape of
`agent/nodes/retrieve.run`. Storage IS the integration bus (D-01): every tool
READS a committed `data/*.json` record via the existing pipeline loader and
returns the already-validated Pydantic record. They call NO LLM and burn NO
quota — the ONLY LLM authority in the supervisor is the single clamped classify
hop. This module intentionally has no top-level logic; import the submodules.

Two honesty invariants every tool obeys:
  - Path-safety allow-list (T-6.3-PATH): each tool gates `drhp_id` through
    `data.catalogue_loader.is_known_drhp_id` BEFORE any `data/*` path is formed —
    a non-allow-listed / traversal id is rejected before any read.
  - Honest abstain (P14): a MISSING record (FileNotFoundError) yields an honest
    `abstain=True, record=None` state — NEVER a fabricated record.

The isolation invariant (tools import no model/LLM code) is pinned by
tests/unit/test_tools_isolation.py (an inspect.getsource audit mirroring
tests/unit/test_gmp_isolation.py).
"""
