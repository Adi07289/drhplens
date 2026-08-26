from types import SimpleNamespace

from fastapi.testclient import TestClient

import api.main as apimod
from api.main import app

client = TestClient(app)


def _model(payload: dict):
    return SimpleNamespace(model_dump=lambda: payload)


def test_ask_prefers_fused(monkeypatch):
    state = {
        "fused_answer": _model({"answer_prose": "F"}),
        "grounded_answer": _model({"answer_prose": "G"}),
        "refusal": None,
    }
    monkeypatch.setattr(apimod, "invoke_supervisor", lambda q, d: state)
    body = client.post("/ask", json={"question": "q", "drhp_id": "swiggy"}).json()
    assert body["kind"] == "fused"
    assert body["answer"]["answer_prose"] == "F"


def test_ask_falls_back_to_grounded(monkeypatch):
    state = {"fused_answer": None, "grounded_answer": _model({"answer_prose": "G"}), "refusal": None}
    monkeypatch.setattr(apimod, "invoke_supervisor", lambda q, d: state)
    assert client.post("/ask", json={"question": "q", "drhp_id": "swiggy"}).json()["kind"] == "grounded"


def test_ask_refusal(monkeypatch):
    state = {"fused_answer": None, "grounded_answer": None, "refusal": _model({"reason": "no_grounding"})}
    monkeypatch.setattr(apimod, "invoke_supervisor", lambda q, d: state)
    assert client.post("/ask", json={"question": "q", "drhp_id": "swiggy"}).json()["kind"] == "refusal"
