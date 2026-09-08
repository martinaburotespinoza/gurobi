from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from gurobean import Scenario, solve_round

app = FastAPI(title="Gurobean Engine API", version="0.2.6", docs_url="/docs", redoc_url="/redoc")


class ScenarioInput(BaseModel):
    lambda_total: float = Field(ge=0)
    p_hot: float = Field(ge=0, le=1)
    p_cold: float = Field(ge=0, le=1)
    revenue_hot: float = Field(ge=0)
    revenue_cold: float = Field(ge=0)
    cost_hot: float = Field(ge=0)
    cost_cold: float = Field(ge=0)
    salvage_hot: float = Field(ge=0, default=0)
    salvage_cold: float = Field(ge=0, default=0)
    beans_available: float = Field(ge=0)
    water_available: float = Field(ge=0)
    beans_hot: float = Field(ge=0)
    beans_cold: float = Field(ge=0)
    water_hot: float = Field(ge=0)
    water_cold: float = Field(ge=0)


class SolveRequest(BaseModel):
    round_number: int = Field(ge=1, le=8)
    scenario: ScenarioInput
    backend: Literal["scipy", "gurobi", "closed_form"] = "scipy"


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "gurobean-engine", "version": "0.2.6"}


@app.get("/metadata")
def metadata() -> dict:
    return {
        "rounds": {"implemented": [1, 2, 3, 4], "calibration_required": [5, 6, 7, 8]},
        "backends": ["scipy", "gurobi", "closed_form"],
        "gurobi_native": False,
        "note": "R1-R4 Gurobi adapter uses solver-backed PWL validation of the analytical Normal-newsvendor objective.",
    }


@app.post("/solve")
def solve(request: SolveRequest) -> dict:
    if request.round_number > 4:
        raise HTTPException(status_code=501, detail=f"R{request.round_number} is calibration-gated and is not enabled for solving")
    if request.backend == "closed_form" and request.round_number != 1:
        raise HTTPException(status_code=400, detail="closed_form backend is available only for R1")
    try:
        sc = Scenario(**request.scenario.model_dump())
        result = solve_round(request.round_number, sc, backend=request.backend)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "round": request.round_number, "result": result}
