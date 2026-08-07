#!/usr/bin/env python
"""
scripts/_check_stress_fixtures.py — the D-07/D-09 committed adversarial-corpus counter.

Task 1 verify for 06.3-04. A tiny, dependency-free parser + category counter over the
committed weird-query stress fixtures under ``eval/gold/stress/*.jsonl``. It proves the
corpus parses as JSON and satisfies the D-07 four-category coverage floor BEFORE the
importorskip-guarded stress suite (``tests/eval/test_stress_suite.py``) auto-activates
when ``agent/supervisor.py`` lands (Wave 3 / Plan 07).

Exit code 0 on success; non-zero with a human-readable reason on any breach.

Checks (06.3-04-PLAN Task 1 acceptance_criteria):
  1. Every row parses as JSON and carries the keyed fields id / category / question / drhp_id.
  2. Total rows across the FOUR D-07 categories >= 20, and EACH of
     compliance_bait / jailbreak / offtopic / cross_ipo has >= 5 rows.
  3. compliance_bait has >= 6 rows and includes >= 2 advice-by-implication rows
     (clean-token, posture-breaching; flagged ``"implication": true``) — AI-SPEC §5.
  4. Every ``id`` is unique across the whole corpus (parametrize ids must not collide).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# eval/gold/stress lives at the repo root; scripts/_check_stress_fixtures.py -> scripts -> repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
STRESS_DIR = REPO_ROOT / "eval" / "gold" / "stress"

# The four D-07 weird-query categories (each has its own committed .jsonl).
D07_CATEGORIES = ("compliance_bait", "jailbreak", "offtopic", "cross_ipo")
REQUIRED_KEYS = ("id", "category", "question", "drhp_id")

MIN_PER_D07_CATEGORY = 5
MIN_D07_TOTAL = 20
MIN_COMPLIANCE_BAIT = 6
MIN_IMPLICATION_ROWS = 2


def _fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if not STRESS_DIR.is_dir():
        _fail(f"stress fixture directory not found: {STRESS_DIR}")

    files = sorted(STRESS_DIR.glob("*.jsonl"))
    if not files:
        _fail(f"no .jsonl fixtures under {STRESS_DIR}")

    rows: list[dict] = []
    for path in files:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                _fail(f"{path.name}:{lineno} is not valid JSON — {exc}")
            missing = [k for k in REQUIRED_KEYS if k not in row]
            if missing:
                _fail(f"{path.name}:{lineno} missing keyed field(s): {missing}")
            rows.append(row)

    # Category counts
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["category"]] = counts.get(row["category"], 0) + 1

    # Check 2: each D-07 category >= 5, and the four sum to >= 20
    for cat in D07_CATEGORIES:
        n = counts.get(cat, 0)
        if n < MIN_PER_D07_CATEGORY:
            _fail(f"category {cat!r} has {n} rows; need >= {MIN_PER_D07_CATEGORY}")
    d07_total = sum(counts.get(cat, 0) for cat in D07_CATEGORIES)
    if d07_total < MIN_D07_TOTAL:
        _fail(f"D-07 four-category total is {d07_total}; need >= {MIN_D07_TOTAL}")

    # Check 3: compliance_bait >= 6 with >= 2 advice-by-implication rows
    cb_rows = [r for r in rows if r["category"] == "compliance_bait"]
    if len(cb_rows) < MIN_COMPLIANCE_BAIT:
        _fail(f"compliance_bait has {len(cb_rows)} rows; need >= {MIN_COMPLIANCE_BAIT}")
    implication = [r for r in cb_rows if r.get("implication") is True]
    if len(implication) < MIN_IMPLICATION_ROWS:
        _fail(
            f"compliance_bait has {len(implication)} advice-by-implication rows "
            f"(implication=true); need >= {MIN_IMPLICATION_ROWS} (AI-SPEC §5)"
        )

    # Check 4: unique ids
    ids = [r["id"] for r in rows]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        _fail(f"duplicate row id(s): {dupes}")

    # Summary (success)
    print("OK: stress corpus valid.")
    print(f"  files: {[p.name for p in files]}")
    for cat in sorted(counts):
        print(f"  {cat}: {counts[cat]}")
    print(f"  D-07 four-category total: {d07_total} (>= {MIN_D07_TOTAL})")
    print(f"  compliance_bait advice-by-implication rows: {len(implication)} (>= {MIN_IMPLICATION_ROWS})")
    print(f"  total rows: {len(rows)}")


if __name__ == "__main__":
    main()
