"""
tests/unit/test_readme_links.py — OPS-03b portfolio README audit.

The README is the recruiter's first landing on GitHub. This pins the honesty +
navigation contract as an on-disk audit (NO network): the Hugging Face Spaces
front-matter is preserved verbatim (the deploy depends on it), a Mermaid
architecture diagram of the REAL pipeline is present (Docling absent), every
repo-relative file link resolves to a committed non-empty file, and the D-01
hybrid shape (hook + architecture + evals + honest-limitations) is present.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
README = REPO_ROOT / "README.md"

_MD_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")

# The committed artifacts the README MUST cross-link (OPS-03b).
_REQUIRED_TARGETS = (
    "model_card/MODEL_CARD.md",
    "eval/dashboards/eval-dashboard.html",
    "eval/failures/failures.yaml",
)


def _readme() -> str:
    assert README.is_file(), f"expected README at {README}"
    return README.read_text(encoding="utf-8")


def test_hf_spaces_front_matter_preserved():
    """The HF Spaces deploy depends on the YAML front-matter — it must stay verbatim."""
    src = _readme()
    assert src.startswith("---\n"), "README must open with the HF Spaces YAML front-matter"
    head = src.split("---", 2)[1]  # content between the first two --- fences
    assert "title: DRHPLens" in head
    assert "sdk: streamlit" in head
    assert "app_file: app.py" in head


def test_mermaid_architecture_diagram_present():
    src = _readme()
    assert "```mermaid" in src, "the architecture diagram must be a ```mermaid fenced block"


def test_architecture_diagram_names_the_real_pipeline_no_docling():
    src = _readme()
    for component in ("PyMuPDF", "Qdrant", "LangGraph", "MAPIE"):
        assert component in src, f"the architecture diagram must name {component!r}"
    assert "Docling" not in src, (
        "Docling must be absent — the README depicts the REAL pipeline "
        "(PyMuPDF + pdfplumber), never the parser that cannot run in-env (D-02)."
    )


def test_required_committed_targets_are_linked_and_exist():
    src = _readme()
    for target in _REQUIRED_TARGETS:
        assert target in src, f"README must cross-link {target!r}"
        p = REPO_ROOT / target
        assert p.is_file() and p.stat().st_size > 0, f"linked target missing/empty: {target}"


def test_every_repo_relative_file_link_resolves():
    """Every repo-relative file link resolves to a committed non-empty file (no
    network). App routes (/methodology, /failures), external URLs, and anchors are
    not repo files and are skipped."""
    src = _readme()
    for target in _MD_LINK.findall(src):
        t = target.strip()
        if t.startswith(("http://", "https://", "#", "/", "mailto:")):
            continue  # external URL, anchor, or app route — not a repo file
        t = t.split("#", 1)[0]  # drop any anchor fragment
        if not t:
            continue
        # NB: Path normalizes a leading "./" itself — do NOT str.lstrip("./"),
        # which strips a char-set and would mangle "./.env.example" -> "env.example".
        p = (REPO_ROOT / t).resolve()
        assert p.is_file() and p.stat().st_size > 0, (
            f"broken repo-relative link in README: {target!r} -> {p}"
        )


def test_no_external_image_assets():
    """Self-contained: no external image URLs (Mermaid is text; no remote images, D-04)."""
    src = _readme()
    for img in _MD_IMAGE.findall(src):
        assert not img.strip().startswith(("http://", "https://")), (
            f"external image asset not allowed: {img!r}"
        )


def test_hybrid_shape_sections_present():
    """D-01 hybrid shape: a hook, an architecture section, an evals section, and an
    honest-limitations section are all present."""
    src = _readme().lower()
    assert "## architecture" in src or "## how it works" in src, "architecture section required"
    assert "## evaluation" in src or "## evals" in src, "evals section required"
    assert "limitation" in src, "an honest-limitations section is required"
