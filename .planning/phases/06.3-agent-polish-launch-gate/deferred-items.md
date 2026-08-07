# Phase 6.3 — Deferred / Out-of-Scope Items

Out-of-scope discoveries logged during execution (SCOPE BOUNDARY rule — not fixed,
because they are pre-existing and unrelated to the current plan's changes).

## Flaky (intermittent) test (observed during 06.3-03)

- **Test:** `tests/unit/test_diagnostics_plots.py::test_shap_summary_writes_nonempty_png_from_fitted_model`
- **Observation:** FAILED on the pre-implementation baseline run (1 failed, 666 passed,
  12 skipped, 2 xfailed) but PASSED on the post-implementation full-suite run
  (688 passed, 0 failed). 06.3-03 touched no forecaster/diagnostics code, so this is
  an **intermittent (flaky)** SHAP-plot test, not a persistent failure.
- **Scope:** Phase 5 forecaster SHAP-diagnostics plotting — entirely unrelated to the
  06.3-03 read-only tool surface / semantic cache (no `agent/tools`, `agent/cache`,
  or `semantic_cache` reference).
- **Disposition:** OUT OF SCOPE for 06.3-03. Not touched here (SCOPE BOUNDARY). Flag for
  the forecaster/diagnostics owner to de-flake (likely matplotlib/SHAP nondeterminism).
