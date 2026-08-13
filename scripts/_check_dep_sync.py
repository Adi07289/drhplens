"""
scripts/_check_dep_sync.py — WR-03 dependency-sync checker (Plan 06.3-10, D-14).

The DEPLOYED app is installed on HF Spaces straight from `requirements.txt`, while
local/dev installs use `pyproject.toml`. If the two drift, an HF-Spaces install can
be missing a package the app imports at runtime (the WR-03 bug: `requirements.txt`
historically omitted `google-genai`, `fastembed`, and the Phase 4/5 runtime deps).

This checker enforces that the RUNTIME dependency set is IDENTICAL in both manifests:
every package in `requirements.txt` appears in `pyproject.toml [project.dependencies]`
at the SAME version specifier, and vice-versa. It exits non-zero (with a readable
diff) on any drift, so a future dependency edit that touches only one file is caught.

SCOPE (intentional): only `[project.dependencies]` (the CORE runtime set) is compared.
`[project.optional-dependencies]` groups (`dev`, `eval`) are the dev/CI-only extras and
are DELIBERATELY excluded — they are not installed on the Space. In particular `ragas`
lives in the `[eval]` extra (D-14 decision: heavy on HF Spaces, offline cross-check
only, never imported in CI / the release gate), so its ABSENCE from `requirements.txt`
is correct, not drift.

Usage:
    .venv/bin/python scripts/_check_dep_sync.py     # exit 0 in sync, 1 (with diff) on drift
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

PROJECT_ROOT = Path(__file__).parent.parent
REQUIREMENTS_TXT = PROJECT_ROOT / "requirements.txt"
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"


def _parse_requirement(line: str) -> tuple[str, str] | None:
    """Parse one requirement line → (canonical_name, normalized_specifier).

    Returns None for blank lines and comments. Uses `packaging` so the name is
    PEP 503-canonicalized and the specifier is compared set-wise (so `>=1.2,<2`
    and `<2,>=1.2` are equal). An unpinned package normalizes to an empty spec.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    # Drop any trailing inline comment (only when clearly a comment, i.e. " #").
    if " #" in stripped:
        stripped = stripped.split(" #", 1)[0].strip()
    req = Requirement(stripped)
    return canonicalize_name(req.name), str(req.specifier)


def _load_requirements_txt(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_requirement(line)
        if parsed is not None:
            name, spec = parsed
            out[name] = spec
    return out


def _load_pyproject_core(path: Path) -> dict[str, str]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies", [])
    out: dict[str, str] = {}
    for dep in deps:
        parsed = _parse_requirement(dep)
        if parsed is not None:
            name, spec = parsed
            out[name] = spec
    return out


def check() -> int:
    req = _load_requirements_txt(REQUIREMENTS_TXT)
    core = _load_pyproject_core(PYPROJECT_TOML)

    only_in_req = sorted(set(req) - set(core))
    only_in_core = sorted(set(core) - set(req))
    mismatched = sorted(
        name for name in set(req) & set(core) if req[name] != core[name]
    )

    if not (only_in_req or only_in_core or mismatched):
        print(
            f"DEP SYNC OK: requirements.txt and pyproject.toml "
            f"[project.dependencies] are in sync ({len(req)} runtime packages). "
            f"(ragas correctly lives in the [eval] extra, excluded by design.)"
        )
        return 0

    print("DEP SYNC FAILED: requirements.txt <-> pyproject.toml [project.dependencies] drift.")
    if only_in_req:
        print("\n  In requirements.txt but NOT pyproject core:")
        for name in only_in_req:
            print(f"    - {name}{req[name]}")
    if only_in_core:
        print("\n  In pyproject core but NOT requirements.txt:")
        for name in only_in_core:
            print(f"    - {name}{core[name]}")
    if mismatched:
        print("\n  Version-specifier mismatch (name: requirements.txt vs pyproject):")
        for name in mismatched:
            print(f"    - {name}: '{req[name]}' vs '{core[name]}'")
    print(
        "\nReconcile the two manifests (same package, same pin in BOTH). Note: the "
        "[dev] / [eval] optional-extras are intentionally NOT part of the runtime "
        "deploy set and must NOT be added to requirements.txt."
    )
    return 1


if __name__ == "__main__":
    sys.exit(check())
