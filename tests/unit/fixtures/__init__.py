"""
tests/unit/fixtures/ — shared, pure, offline test-data builders for Phase 5.

This package holds deterministic, no-network builders that the Wave 2-6 modeling
tests (CQR / walk-forward / metrics / baselines) import to construct a tiny
synthetic IPO panel + feature matrix + out-of-sample rows without touching the
network or training a live model. Keep every builder here seed-deterministic and
dependency-light (numpy + pandas + the pipelines.historical column contract only).
"""
