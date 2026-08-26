from __future__ import annotations

from fastapi import FastAPI

from pipelines.forecast import load_forecast

app = FastAPI(title="DRHPLens API", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/forecast/{drhp_id}")
def forecast(drhp_id: str) -> dict:
    record = load_forecast(drhp_id)
    if record is None:
        return {"state": "not_found", "record": None}
    state = "abstain" if getattr(record, "abstain", False) else "covered"
    return {"state": state, "record": record.model_dump()}
