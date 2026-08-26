from types import SimpleNamespace

from fastapi.testclient import TestClient

import api.main as apimod
from api.main import app

client = TestClient(app)


def _record():
    return SimpleNamespace(
        model_dump=lambda: {"drhp_id": "swiggy_2024_11", "fields": {}, "ranked_risks": []}
    )


def test_redflags_ok(monkeypatch):
    monkeypatch.setattr(apimod, "load_redflag", lambda d: _record())
    body = client.get("/redflags/swiggy_2024_11").json()
    assert body["state"] == "ok"
    assert body["record"]["drhp_id"] == "swiggy_2024_11"


def test_redflags_unknown_is_not_found(monkeypatch):
    def _raise(d):
        raise ValueError("unknown drhp_id")

    monkeypatch.setattr(apimod, "load_redflag", _raise)
    assert client.get("/redflags/nope").json() == {"state": "not_found", "record": None}


def test_redflags_none_is_not_found(monkeypatch):
    monkeypatch.setattr(apimod, "load_redflag", lambda d: None)
    assert client.get("/redflags/x").json() == {"state": "not_found", "record": None}
