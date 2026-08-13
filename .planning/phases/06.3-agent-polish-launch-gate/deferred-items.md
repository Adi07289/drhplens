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

## Blocking HITL items from 06.3-10 (launch gate — human-in-the-loop)

These are the human-in-the-loop launch-gate items the 06.3-10 executor could NOT complete
alone (D-14). The **auto (code) half is done + committed** (SEBI self-audit DRAFT, WR-03
dependency sync, `.github/workflows/eval-gate.yml`); the **human half is drafted-where-
draftable and recorded PENDING** — not faked, not hard-halted. Full UAT-format detail +
expected outcomes are in `06.3-HUMAN-UAT.md` (items H-1…H-5). This **extends** the four
disclosed 6.1 follow-ups (`06.1-.../deferred-items.md`: judge calibration, CI gate lane,
gold-set span-tightening, WR-03) — it does not duplicate them; WR-03 is now CLOSED and the
CI-lane code half is now DRAFTED.

- **H-1 — SEBI self-audit human sign-off (D-10/D-11).** `compliance/SEBI-REVIEW.md` is
  drafted with a prominent "AWAITING HUMAN SEBI-LITERATE SIGN-OFF" status and an empty
  Sign-off Record (Section 7). A SEBI-compliance-literate reviewer (or the operator standing
  in per D-10) must read it against the enforcing code + D-09 stress suite and close/leave-
  open the 3 §1b flags. **Blocking.** `result: pending`.
- **H-2 — CI repo secrets + PR gate verification (D-14).** `eval-gate.yml` is drafted (code
  half); the user must add `GEMINI_API_KEY` / `QDRANT_URL` / `QDRANT_API_KEY` / `LANGFUSE_*`
  repo Actions secrets and confirm the gate runs + blocks on a forced regression. **Blocking.**
  `result: pending`.
- **H-3 — Public HF Spaces deploy (OPS-02 / D-12).** Create the Space, set Space Secrets,
  seed Qdrant Cloud, deploy Streamlit, replace `<user>` in `ping.yml`, verify mobile fused
  answer + C4 cap fallback + read-only surfaces + keep-warm, and re-verify the deploy
  daily-cap live. **Blocking.** `result: pending`.
- **H-4 — Judge-vs-human calibration ≥50 examples, ≥0.7 (D-14).** SEBI-literate reviewer
  labels ≥50 examples; record in `eval/reports/judge_calibration.md` (pending record
  drafted). A real (non `-1`) faithfulness number is committed **only** if correlation ≥0.7;
  otherwise the surface **STAYS `-1`** (T-6.3-THEATER / P10 guard). Burns Gemini quota.
  **Blocking.** `result: pending`.
- **H-5 — Gold-set span-tightening by a human reading the Swiggy DRHP (D-14).** An IPO
  analyst reads the Swiggy DRHP PDF to set real `expected_sources` pages (≤2–3pp). **Do NOT
  re-run auto-substring matching** — refused on honesty grounds in 6.1. Until done,
  `recall@10` / `citation_accuracy` remain honest saturated floors. **Blocking.**
  `result: pending`.
