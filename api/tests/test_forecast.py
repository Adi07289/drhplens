from types import SimpleNamespace

from fastapi.testclient import TestClient

import api.main as apimod
from api.main import app

client = TestClient(app)


def _fake_record(abstain: bool):
    return SimpleNamespace(
        abstain=abstain,
        model_dump=lambda: {"drhp_id": "swiggy", "abstain": abstain},
    )


def test_forecast_not_found(monkeypatch):
    monkeypatch.setattr(apimod, "load_forecast", lambda drhp_id: None)
    r = client.get("/forecast/unknown")
    assert r.status_code == 200
    assert r.json() == {"state": "not_found", "record": None}


def test_forecast_covered(monkeypatch):
    monkeypatch.setattr(apimod, "load_forecast", lambda drhp_id: _fake_record(False))
    body = client.get("/forecast/swiggy").json()
    assert body["state"] == "covered"
    assert body["record"]["drhp_id"] == "swiggy"


def test_forecast_abstain(monkeypatch):
    monkeypatch.setattr(apimod, "load_forecast", lambda drhp_id: _fake_record(True))
    assert client.get("/forecast/swiggy_2024_11").json()["state"] == "abstain"


def test_forecast_unknown_id_is_not_found(monkeypatch):
    """load_forecast raises ValueError for ids outside the catalogue allow-list
    (path-traversal guard) — the endpoint must translate that to not_found, not 500."""

    def _raise(drhp_id):
        raise ValueError("Unknown drhp_id; refusing to form a cache path.")

    monkeypatch.setattr(apimod, "load_forecast", _raise)
    r = client.get("/forecast/nope")
    assert r.status_code == 200
    assert r.json() == {"state": "not_found", "record": None}
