# DRHPLens — deploy tooling.
#
# `make release` is the numeric-faithfulness RELEASE GATE (EVAL-03 / D3-12):
# it runs the numeric eval track against live services and EXITS NON-ZERO when
# numeric_faithfulness < agent.policies.NUMERIC_FAITHFULNESS_GATE (0.95). Make
# stops on the non-zero exit, so a hallucinated number physically blocks deploy
# (enforcement over discipline, RESEARCH Pitfall 4). Requires GEMINI_API_KEY /
# QDRANT_URL / QDRANT_API_KEY in the environment and the gold-set DRHP(s)
# ingested into live Qdrant.
#
# The gate LOGIC is CI-tested offline (no live infra) in
# tests/eval/test_release_gate.py at 0.94 (fail) / 0.95 / 0.96 (pass).

PYTHON ?= .venv/bin/python

.PHONY: release gate-test

## release: run the numeric-faithfulness gate against live services; non-zero exit blocks deploy
release:
	$(PYTHON) scripts/release_gate.py

## gate-test: run the offline gate-logic fixture test (no live infra)
gate-test:
	$(PYTHON) -m pytest tests/eval/test_release_gate.py -q
