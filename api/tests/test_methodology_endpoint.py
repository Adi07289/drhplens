from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_methodology_returns_four_blocks():
    r = client.get("/methodology")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"card", "plots", "eval", "panel_sanity"}
    # committed artifacts are present in the repo -> non-null, with the real seams.
    assert body["card"]["gate_passed"] is False
    assert body["card"]["coverage"] == 0.8004
    assert body["eval"]["aggregate"]["faithfulness_deepeval"] == -1.0
    assert len(body["plots"]["pit"]["counts"]) == 10
    assert body["panel_sanity"]["n_scored"] == 1245


def test_methodology_missing_artifact_is_null_not_500(monkeypatch):
    import api.methodology as m

    monkeypatch.setattr(m, "_EVAL_SUMMARY", m._REPO / "eval" / "reports" / "does_not_exist.json")
    r = client.get("/methodology")
    assert r.status_code == 200
    assert r.json()["eval"] is None  # honest null, never a fabricated number


def test_methodology_corrupt_artifact_is_null_not_500(monkeypatch, tmp_path):
    """A committed artifact that is present but unreadable JSON degrades to None
    (exercises _load's except-ValueError branch) — never a 500, never a fake number."""
    import api.methodology as m

    bad = tmp_path / "corrupt.json"
    bad.write_text("{ not: valid json ", encoding="utf-8")
    monkeypatch.setattr(m, "_CARD", bad)
    r = client.get("/methodology")
    assert r.status_code == 200
    assert r.json()["card"] is None
