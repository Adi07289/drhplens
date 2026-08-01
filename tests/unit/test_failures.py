"""Unit tests — the FAILGAL-01 /failures gallery (render-only, honesty-invariant).

Mirrors ``tests/unit/test_eval_inline.py`` (the render-only template) for the new
``ui.failures.render_failures`` surface + its committed data file
``eval/failures/failures.yaml``:

  (a) schema + coverage — the committed YAML has >=10 entries, every required key,
      valid ``surface``/``status``, a non-empty ``postmortem``, unique ``id``, and all
      three surfaces (rag/extraction/forecast) present;
  (b) read-only isolation — ``ui/failures.py`` imports ONLY the
      {__future__, html, json, pathlib, yaml, streamlit} allowlist and references no
      agent / LLM / vector / model token (P19, demo-safe);
  (c) neutral render — a gallery renders only ``.drhp-fail-*`` classes, no ``style=``,
      no color/badge/emoji; an ``open`` and a ``mitigated`` entry render byte-identically
      except the status text; the empty-state path renders the muted <p> (no crash);
  (d) searchable filter — the render-only surface/free-text filters narrow the rendered
      set in-memory (no live call); a no-match query renders the muted empty-state.

DEFERRED-IMPORT BLOCKER GUARD: tests (b)/(c)/(d) need ``ui.failures`` which does NOT
exist until Task 2. They import it INSIDE each function body (never at module top-level)
so a missing renderer cannot break pytest COLLECTION of the whole file — test (a) (yaml /
pathlib only) must stay independently collectible and GREEN in Task 1's RED step.
"""
from __future__ import annotations

import contextlib
import re
from pathlib import Path

import yaml

# ── repo-root-relative committed data path (cwd-independent) ──────────────────
_FAILURES_YAML = Path(__file__).resolve().parents[2] / "eval" / "failures" / "failures.yaml"

_VALID_SURFACES = {"rag", "extraction", "forecast"}
_VALID_STATUS = {"open", "mitigated"}
_REQUIRED = {
    "id", "surface", "category", "query", "expected", "actual",
    "postmortem", "status", "refs",
}

# The failure markup may only carry these neutral classes — any other class token
# (badge / severity / success / danger / green / red …) is a verdict-UX breach.
_ALLOWED_CLASS_PREFIXES = ("drhp-fail-", "st-key-drhpcard-")


class _RecordingSt:
    """A minimal Streamlit stub recording every markdown body; ``.container(...)``
    (the ``st.container(border=True, key=…)`` lifted card) is a nullcontext."""

    def __init__(self) -> None:
        self.emitted: list[str] = []

    def markdown(self, body, unsafe_allow_html=False):
        self.emitted.append(body)

    def container(self, *args, **kwargs):
        return contextlib.nullcontext()


def _render(failures_mod, tmp_path, monkeypatch, entries, **kwargs) -> str:
    """Write ``entries`` to a temp YAML, monkeypatch the module path + st, render,
    return the joined emitted markup."""
    path = tmp_path / "failures.yaml"
    path.write_text(yaml.safe_dump(entries, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(failures_mod, "_FAILURES_PATH", path)
    st = _RecordingSt()
    monkeypatch.setattr(failures_mod, "st", st)
    failures_mod.render_failures(**kwargs)
    return "\n".join(st.emitted)


def _entry(**over) -> dict:
    base = {
        "id": "x1",
        "surface": "rag",
        "category": "cite",
        "query": "a one-line failure",
        "expected": "the honest expectation",
        "actual": "what actually happened",
        "postmortem": "what was learned",
        "status": "open",
        "refs": ["tests/unit/test_failures.py"],
    }
    base.update(over)
    return base


# ── (a) schema + coverage (GREEN in Task 1 — data is authored) ────────────────
def test_failures_yaml_schema_and_coverage():
    """The committed failures.yaml is well-formed and honestly covers all surfaces."""
    entries = yaml.safe_load(_FAILURES_YAML.read_text(encoding="utf-8"))
    assert isinstance(entries, list)
    assert len(entries) >= 10, f"need >=10 real failures, got {len(entries)}"

    seen_surfaces: set[str] = set()
    ids: set[str] = set()
    for e in entries:
        assert _REQUIRED <= set(e), f"entry {e.get('id')!r} missing keys: {_REQUIRED - set(e)}"
        assert e["surface"] in _VALID_SURFACES, f"bad surface: {e['surface']!r}"
        assert e["status"] in _VALID_STATUS, f"bad status: {e['status']!r}"
        assert isinstance(e["postmortem"], str) and e["postmortem"].strip(), (
            f"empty postmortem on {e['id']!r}"
        )
        assert isinstance(e["refs"], list) and e["refs"], f"empty refs on {e['id']!r}"
        assert e["id"] not in ids, f"duplicate id {e['id']!r}"
        ids.add(e["id"])
        seen_surfaces.add(e["surface"])

    assert _VALID_SURFACES <= seen_surfaces, (
        f"surfaces missing from the gallery: {_VALID_SURFACES - seen_surfaces}"
    )


# ── (b) read-only isolation — allowlist + forbidden-token scan ────────────────
def test_read_only_isolation_allowlist():
    """``ui/failures.py`` imports only the read-only allowlist and makes no live call."""
    import ast
    import inspect

    import ui.failures as failures_mod

    src = inspect.getsource(failures_mod)
    tree = ast.parse(src)
    allowed = {"__future__", "html", "json", "pathlib", "yaml", "streamlit"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    stray = imported - allowed
    assert not stray, f"ui/failures.py imports outside the read-only allowlist: {stray}"

    for token in (
        "openai", "genai", "instructor", "groq", "qdrant", ".invoke(",
        "langgraph", "llama_index", "from deepeval", "import deepeval",
    ):
        assert token not in src, (
            f"ui/failures.py must not reference {token!r} (P19: read the committed YAML only)."
        )


# ── (c) neutral render — only .drhp-fail-*, open == mitigated, empty-state ─────
def test_render_neutral_no_live(tmp_path, monkeypatch):
    import ui.failures as failures_mod

    entries = [
        _entry(id="f-open", surface="forecast", category="calibration", status="open"),
        _entry(id="f-mit", surface="rag", category="cite", status="mitigated"),
    ]
    out = _render(failures_mod, tmp_path, monkeypatch, entries)

    # Only the neutral .drhp-fail-* (or the container key class) may appear.
    for class_attr in re.findall(r'class="([^"]*)"', out):
        for cls in class_attr.split():
            assert cls.startswith(_ALLOWED_CLASS_PREFIXES), (
                f"unexpected verdict-ish class {cls!r} on failure markup"
            )

    assert "style=" not in out  # no inline color / severity styling
    for glyph in ("✅", "❌", "⚠️", "🔴", "🟢", "▲", "▼", "↑", "↓"):
        assert glyph not in out
    for verdict in ("badge", "danger", "success", "green", "red"):
        assert verdict not in out.lower()

    # open vs mitigated render byte-identically except the status text.
    base = _entry(id="same", surface="rag", category="cite")
    open_out = _render(failures_mod, tmp_path, monkeypatch, [dict(base, status="open")])
    mit_out = _render(failures_mod, tmp_path, monkeypatch, [dict(base, status="mitigated")])
    assert open_out != mit_out
    assert open_out.replace("OPEN", "S") == mit_out.replace("MITIGATED", "S")

    # empty-state path: an absent file renders the muted <p>, never a crash.
    missing = tmp_path / "nope.yaml"
    monkeypatch.setattr(failures_mod, "_FAILURES_PATH", missing)
    st = _RecordingSt()
    monkeypatch.setattr(failures_mod, "st", st)
    failures_mod.render_failures()  # must not raise
    empty_out = "\n".join(st.emitted)
    assert "drhp-fail-empty" in empty_out


# ── (d) searchable filter — surface + free-text, in-memory, no live call ───────
def test_render_surface_and_text_filter(tmp_path, monkeypatch):
    import ui.failures as failures_mod

    entries = [
        _entry(id="rag-one", surface="rag", category="retrieval",
               query="recall saturates on coarse spans"),
        _entry(id="fc-one", surface="forecast", category="calibration",
               query="model does not beat the baseline"),
        _entry(id="ex-one", surface="extraction", category="f1",
               query="macro f1 is zero on a tiny set"),
    ]

    # surface filter: only forecast cards emit.
    fc_out = _render(failures_mod, tmp_path, monkeypatch, entries, surface="forecast")
    assert "fc-one" in fc_out
    assert "rag-one" not in fc_out
    assert "ex-one" not in fc_out

    # free-text filter: narrows to the matching entry (substring over the fields).
    q_out = _render(failures_mod, tmp_path, monkeypatch, entries, query="coarse spans")
    assert "rag-one" in q_out
    assert "fc-one" not in q_out
    assert "ex-one" not in q_out

    # a no-match query renders the muted empty-state, no crash.
    none_out = _render(failures_mod, tmp_path, monkeypatch, entries, query="zzz-no-such-thing")
    assert "drhp-fail-empty" in none_out
