from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_peers_swiggy_ok():
    r = client.get("/peers/swiggy_2024_11")
    assert r.status_code == 200
    body = r.json()
    assert body["state"] == "ok"
    rec = body["record"]
    assert rec["drhp_id"] == "swiggy_2024_11"
    # peer_set is unwrapped by model_dump(): a GroundedAnswer (answer_prose) or a refusal.
    assert "answer_prose" in rec["peer_set"] or "reason" in rec["peer_set"]
    # issuer row first, 4 metrics per company.
    assert rec["companies"][0]["is_ipo"] is True
    metrics = {m["metric"] for m in rec["companies"][0]["metrics"]}
    assert metrics <= {"pe", "pb", "ev_ebitda", "roe"}


def test_peers_unknown_id_not_found():
    r = client.get("/peers/not_a_real_id")
    assert r.status_code == 200
    assert r.json() == {"state": "not_found", "record": None}
