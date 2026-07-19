"""
tests/unit/test_methodology_render.py — the /methodology forecaster model-card
section (UI-03, the destination of the snapshot forecast block's "Full model card →"
link).

Two invariants, both pinned as on-disk source audits of ``pages/01_methodology.py``
(the page is a Streamlit script — importing it would execute it, so it is read from
disk, mirroring the 05-07 snapshot-page isolation audit):

  1. The page GAINS the forecaster model-card section — it embeds the committed
     ``calibration.png`` / ``pit.png`` / ``shap.png`` (via ``st.image`` from
     ``model_card/``), renders the four-baselines + Diebold–Mariano ``.drhp-metrics``
     table with the P9 verdict, the ``available_at`` leakage audit (incl. the anchor
     pre-open audit, D5-08), the n-per-sector report (D5-10), and a limitations grid.

  2. RENDER-ONLY isolation (T-05-10-ISO): the page IMPORTS no modelling /
     training / explainability module (xgboost / mapie / sklearn / shap / the model
     pipeline). The check is IMPORT-pattern based rather than a bare-substring scan
     because the page legitimately REFERENCES the committed ``shap.png`` static
     artifact — the well-known ``shap`` filename-vs-import collision (the same class
     as the project's documented ``shape``→``shap`` gotcha). Referencing a committed
     PNG is the opposite of importing the explainability library.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAGE = REPO_ROOT / "pages" / "01_methodology.py"


def _page_source() -> str:
    assert PAGE.exists(), f"expected the methodology page at {PAGE}"
    return PAGE.read_text(encoding="utf-8")


def test_page_embeds_the_three_committed_plots():
    src = _page_source()
    assert "model_card" in src
    for png in ("calibration.png", "pit.png", "shap.png"):
        assert png in src, f"the model-card section must embed {png!r}"
    assert "st.image(" in src


def test_page_renders_baselines_diebold_mariano_table_with_p9_verdict():
    src = _page_source()
    assert "Diebold" in src
    assert "drhp-metrics" in src  # reuses the inherited metrics-table grammar
    assert "P9 release gate" in src
    assert '_card.get("baselines"' in src  # the DM rows come from the committed data


def test_page_renders_available_at_leakage_and_anchor_audit():
    src = _page_source()
    assert "available_at" in src
    assert '_card.get("leakage_audit"' in src
    assert "Anchor pre-open leakage audit" in src  # D5-08
    assert '_card.get("anchor_audit"' in src


def test_page_renders_n_per_sector_and_limitations_grid():
    src = _page_source()
    assert "n_per_sector" in src  # D5-10 thinness report
    assert "drhp-hiw-card" in src  # the limitations grid grammar
    assert '_card.get("limitations"' in src


def test_page_is_render_only_imports_no_model_module():
    """The page imports NO modelling / training / explainability module — it is a
    cache-only read over the committed model_card/ artifacts (T-05-10-ISO)."""
    src = _page_source()
    forbidden_imports = (
        "import xgboost",
        "import mapie",
        "import sklearn",
        "import shap",
        "from xgboost",
        "from mapie",
        "from sklearn",
        "from shap",
        "pipelines.forecast.model",
        "pipelines.forecast.walkforward",
        "pipelines.forecast.baselines",
        "pipelines.forecast.card",
        "pipelines.forecast.diagnostics",
        "pipelines.features",
        "pipelines.historical",
    )
    for token in forbidden_imports:
        assert token not in src, (
            f"pages/01_methodology.py must not reference {token!r} "
            f"(T-05-10-ISO: the model-card section is render-only, reading the "
            f"committed model_card/ artifacts — it never imports the model pipeline)."
        )


def test_committed_card_artifacts_exist_for_offline_render():
    """The committed artifacts the section reads must exist so /methodology renders
    offline (CODE-NOW-DEFER; real regeneration at the live build)."""
    mc = REPO_ROOT / "model_card"
    for artifact in ("card_data.json", "calibration.png", "pit.png", "shap.png"):
        p = mc / artifact
        assert p.is_file() and p.stat().st_size > 0, f"missing committed {artifact}"
