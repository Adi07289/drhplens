"""WR-03 regression guard — requirements.txt must stay in sync with pyproject core.

`scripts/_check_dep_sync.py` is the checker; this test wires it into the offline unit
suite so a future dependency edit that touches only ONE manifest reds CI immediately
(the WR-03 bug was exactly that drift). It also pins the D-14 decision that `ragas`
lives in the pyproject `[eval]` optional-extra, NOT in the runtime deploy set.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CHECKER = PROJECT_ROOT / "scripts" / "_check_dep_sync.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location("_check_dep_sync", CHECKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_requirements_and_pyproject_core_in_sync() -> None:
    """The runtime dependency set is identical in both manifests (checker exits 0)."""
    checker = _load_checker()
    assert checker.check() == 0


def test_ragas_is_eval_extra_not_runtime() -> None:
    """D-14: ragas is in the [eval] optional-extra, absent from the core runtime set."""
    checker = _load_checker()
    req = checker._load_requirements_txt(checker.REQUIREMENTS_TXT)
    core = checker._load_pyproject_core(checker.PYPROJECT_TOML)
    assert "ragas" not in req, "ragas must NOT be in requirements.txt (D-14: [eval] extra)"
    assert "ragas" not in core, "ragas must NOT be in pyproject core (D-14: [eval] extra)"

    import tomllib

    data = tomllib.loads(checker.PYPROJECT_TOML.read_text(encoding="utf-8"))
    eval_extra = data["project"]["optional-dependencies"]["eval"]
    assert any(dep.startswith("ragas") for dep in eval_extra), (
        "ragas must live in the pyproject [eval] optional-dependencies group"
    )
