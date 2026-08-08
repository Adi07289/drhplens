# DRHPLens — deploy tooling.
#
# `make release` is the RELEASE GATE (EVAL-03 / D3-12 / D-09). It runs THREE lanes
# via scripts/release_gate.py, each EXITING NON-ZERO on breach (Make stops on the
# non-zero exit, so a regression physically blocks deploy — enforcement over
# discipline, RESEARCH Pitfall 4):
#   1. deterministic eval gate  — citation_accuracy >= 0.95 AND recall@10 >= 0.85 (offline)
#   2. deterministic D-09 stress gate — the offline weird-query envelope suite (offline)
#   3. numeric-faithfulness gate — numeric_faithfulness >= 0.95 (LIVE)
# Lanes 1-2 are offline (committed artifact + stubbed-LLM stress suite); lane 3
# requires GEMINI_API_KEY / QDRANT_URL / QDRANT_API_KEY and the gold-set DRHP(s)
# ingested into live Qdrant.
#
# The gate LOGIC is CI-tested offline (no live infra): the numeric/eval lanes in
# tests/eval/test_release_gate.py (0.94 fail / 0.95 / 0.96 pass) and the stress lane
# in tests/unit/test_release_gate_stress.py (green stub passes / red stub exits 1).

PYTHON ?= .venv/bin/python

.PHONY: release gate-test stress-gate

## release: run all three release-gate lanes (eval + stress offline, numeric live); non-zero exit blocks deploy
release:
	$(PYTHON) scripts/release_gate.py

## gate-test: run the offline gate-logic fixture tests — eval/numeric + stress lanes (no live infra)
gate-test:
	$(PYTHON) -m pytest tests/eval/test_release_gate.py tests/unit/test_release_gate_stress.py -q

## stress-gate: run the offline D-09 stress envelope suite directly (no live LLM, no --run flag)
stress-gate:
	$(PYTHON) -m pytest tests/eval/test_stress_suite.py -q
