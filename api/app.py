from __future__ import annotations

from math import isfinite
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from gurobean import Scenario, solve_round
from gurobean.assistant import ask as ask_assistant, evidence_context

app = FastAPI(title="Gurobean Engine API", version="0.2.6", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


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

    @model_validator(mode="after")
    def validate_scenario_contract(self) -> "ScenarioInput":
        numeric_fields = (
            "lambda_total", "p_hot", "p_cold", "revenue_hot", "revenue_cold",
            "cost_hot", "cost_cold", "salvage_hot", "salvage_cold",
            "beans_available", "water_available", "beans_hot", "beans_cold",
            "water_hot", "water_cold",
        )
        if any(not isfinite(getattr(self, name)) for name in numeric_fields):
            raise ValueError("scenario numeric values must be finite")
        if abs((self.p_hot + self.p_cold) - 1.0) > 1e-12:
            raise ValueError("p_hot + p_cold must equal 1")
        return self


class SolveRequest(BaseModel):
    round_number: int = Field(ge=1, le=8)
    scenario: ScenarioInput
    backend: Literal["scipy", "gurobi", "closed_form"] = "scipy"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "gurobean-engine", "version": "0.2.6", "ai": "grounded-local"}


@app.get("/metadata")
def metadata() -> dict:
    return {
        "rounds": {"implemented": [1, 2, 3, 4], "calibration_required": [5, 6, 7, 8]},
        "backends": ["scipy", "gurobi", "closed_form"],
        "gurobi_backend": "solver-backed-pwl",
        "gurobi_license_required": True,
        "ai": {"enabled": True, "provider": "local-evidence-or-ollama", "grounded": True},
        "note": "R1-R4 Gurobi adapter uses solver-backed PWL validation of the analytical Normal-newsvendor objective; API metadata never claims license availability.",
    }


@app.get("/ai/context")
def ai_context() -> dict:
    return evidence_context()


@app.post("/ai/ask")
def ai_ask(request: AskRequest) -> dict:
    try:
        return ask_assistant(request.question)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
