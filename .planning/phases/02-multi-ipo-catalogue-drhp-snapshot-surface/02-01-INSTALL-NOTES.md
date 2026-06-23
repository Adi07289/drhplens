# 02-01 Install Notes

- Python 3.11.15 venv active at `.venv` — confirmed.
- Baseline `pytest tests/unit -q --timeout=15` (before Wave 0 changes): **226 passed, 1 failed**
  (not 219 as the execution-context brief assumed). The 1 failure is pre-existing and
  out of scope for Wave 0:
  - `tests/unit/test_embedder.py::test_bge_m3_real_embed_query_1024_dim` fails because
    `sentence-transformers` is not installed in this venv (`RuntimeError: sentence-transformers
    is not installed`). This is a real dependency gap unrelated to any Phase 2 Wave 0 stub work
    (pure scaffolding — no embedder code touched). Logged here per the deviation-rules scope
    boundary; not auto-fixed (would require a package install, excluded from auto-fix per Rule 3
    exclusion, and is unrelated to this plan's files anyway).
- Wave 0 success bar used in this execution: **226 passed before, 226 passed after** (the
  pre-existing failure must not regress further; new xfail stubs must collect without adding
  failures or errors).
