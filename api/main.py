from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent.supervisor import invoke_supervisor
from pipelines.forecast import load_forecast

app = FastAPI(title="DRHPLens API", version="0.1.0")


class AskRequest(BaseModel):
    question: str
    drhp_id: str


# Answer priority mirrors ui/snapshot_chat.py: fused > grounded > refusal.
_ANSWER_KEYS = (
    ("fused_answer", "fused"),
    ("grounded_answer", "grounded"),
    ("refusal", "refusal"),
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/ask")
def ask(req: AskRequest) -> dict:
    state = invoke_supervisor(req.question, req.drhp_id)
    for state_key, kind in _ANSWER_KEYS:
        val = state.get(state_key)
        if val is not None:
            answer = val.model_dump() if hasattr(val, "model_dump") else val
            return {"kind": kind, "answer": answer}
    raise HTTPException(status_code=502, detail="agent returned no answer")


@app.get("/forecast/{drhp_id}")
def forecast(drhp_id: str) -> dict:
    # load_forecast raises ValueError for ids outside the catalogue allow-list
    # (path-traversal guard). Treat unknown / uncached ids as "not_found".
    try:
        record = load_forecast(drhp_id)
    except (ValueError, FileNotFoundError):
        return {"state": "not_found", "record": None}
    if record is None:
        return {"state": "not_found", "record": None}
    state = "abstain" if getattr(record, "abstain", False) else "covered"
    return {"state": state, "record": record.model_dump()}
