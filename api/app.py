from __future__ import annotations

from math import isfinite
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator

from gurobean import Scenario, solve_round
from gurobean.assistant import ask as ask_assistant, evidence_context
from gurobean.evaluation import evaluate_scenario
from gurobean.full_rounds import DynamicRoundParams, solve_dynamic_round

API_VERSION = "0.3.3"
RELEASE_MARKER = "r9-release-candidate"

app = FastAPI(title="Gurobean Engine API", version=API_VERSION, docs_url="/docs", redoc_url="/redoc")
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
        numeric_fields = ("lambda_total", "p_hot", "p_cold", "revenue_hot", "revenue_cold", "cost_hot", "cost_cold", "salvage_hot", "salvage_cold", "beans_available", "water_available", "beans_hot", "beans_cold", "water_hot", "water_cold")
        if any(not isfinite(getattr(self, name)) for name in numeric_fields):
            raise ValueError("scenario numeric values must be finite")
        if abs((self.p_hot + self.p_cold) - 1.0) > 1e-12:
            raise ValueError("p_hot + p_cold must equal 1")
        return self

class DynamicInput(BaseModel):
    arrival_baseline_rate: float = Field(default=60.0, gt=0)
    arrival_reference_rate: float = Field(default=36.0, gt=0)
    reference_markup: float = Field(default=1.0, gt=0)
    markup_min: float = Field(default=0.0, ge=0)
    markup_max: float = Field(default=5.0, gt=0)
    balking_a: float = 2.0
    balking_b: float = -0.15
    multi_cup_theta: float = Field(default=1.0, ge=0)
    service_rate_base: float = Field(default=65.0, gt=0)
    service_rate_min: float = Field(default=50.0, gt=0)
    service_rate_max: float = Field(default=90.0, gt=0)
    service_cost_fixed: float = Field(default=0.0, ge=0)
    service_cost_linear: float = Field(default=4.0, ge=0)
    service_cost_quadratic: float = Field(default=0.0, ge=0)
    hours: int = Field(default=120, ge=1, le=240)
    warmup_hours: int = Field(default=0, ge=0, lt=240)
    replications: int = Field(default=4, ge=1, le=32)
    seed: int = Field(default=42)
    coordinate_points: int = Field(default=7, ge=3, le=15)

    @model_validator(mode="after")
    def validate_dynamic(self) -> "DynamicInput":
        values = self.model_dump()
        if any(not isfinite(float(v)) for v in values.values() if isinstance(v, (int, float))):
            raise ValueError("dynamic numeric values must be finite")
        if self.markup_max <= self.markup_min:
            raise ValueError("markup_max must be greater than markup_min")
        # Be tolerant of an older cached frontend. The service base must always
        # be feasible; expand the bounds to include it rather than rejecting a
        # stale payload with HTTP 422.
        if self.service_rate_base < self.service_rate_min:
            self.service_rate_min = self.service_rate_base
        if self.service_rate_base > self.service_rate_max:
            self.service_rate_max = self.service_rate_base
        if self.warmup_hours >= self.hours:
            raise ValueError("warmup_hours must be smaller than hours")
        if self.arrival_reference_rate > self.arrival_baseline_rate:
            raise ValueError("arrival_reference_rate must be <= arrival_baseline_rate")
        return self

class SolveRequest(BaseModel):
    round_number: int = Field(ge=1, le=8)
    scenario: ScenarioInput
    backend: Literal["scipy", "gurobi", "closed_form", "simulation"] = "scipy"
    dynamic: DynamicInput = Field(default_factory=DynamicInput)

    @model_validator(mode="before")
    @classmethod
    def normalize_public_payload(cls, data):
        if not isinstance(data, dict) or "scenario" in data:
            return data
        scenario_fields = {"lambda_total", "p_hot", "p_cold", "revenue_hot", "revenue_cold", "cost_hot", "cost_cold", "salvage_hot", "salvage_cold", "beans_available", "water_available", "beans_hot", "beans_cold", "water_hot", "water_cold"}
        scenario = {key: data[key] for key in scenario_fields if key in data}
        if not scenario:
            return data
        cold = float(scenario.get("p_cold", 0)) > 0
        scenario.setdefault("p_hot", 0.7 if cold else 1.0)
        scenario.setdefault("p_cold", 0.3 if cold else 0.0)
        scenario.setdefault("revenue_cold", scenario.get("revenue_hot", 0.0))
        scenario.setdefault("cost_hot", 0.0)
        scenario.setdefault("cost_cold", 0.0)
        scenario.setdefault("salvage_hot", 0.0)
        scenario.setdefault("salvage_cold", 0.0)
        scenario.setdefault("beans_hot", 10.0)
        scenario.setdefault("beans_cold", scenario.get("beans_hot", 10.0))
        scenario.setdefault("water_hot", 6.0)
        scenario.setdefault("water_cold", scenario.get("water_hot", 6.0))
        scenario.setdefault("beans_available", 0.0)
        scenario.setdefault("water_available", 0.0)
        scenario.setdefault("lambda_total", 0.0)
        data = dict(data)
        data["scenario"] = scenario
        return data

    @model_validator(mode="after")
    def normalize_dynamic_against_scenario(self) -> "SolveRequest":
        if self.dynamic.arrival_reference_rate > self.scenario.lambda_total:
            self.dynamic = self.dynamic.model_copy(update={"arrival_reference_rate": max(self.scenario.lambda_total, 1e-9)})
        return self

class EvaluateRequest(BaseModel):
    round_number: int = Field(ge=1, le=8)
    scenario: ScenarioInput
    q_hot: float = Field(ge=0)
    q_cold: float = Field(ge=0)
    markup: float = Field(default=0.0, ge=0)
    service_rate: float = Field(default=65.0, gt=0)
    replications: int = Field(default=30, ge=1, le=1000)
    seed: int = Field(default=42)
    hours: int = Field(default=120, ge=1, le=240)
    warmup_hours: int = Field(default=0, ge=0, lt=240)
    barista_cost_per_hour: float = Field(default=0.0, ge=0)
    dynamic: DynamicInput = Field(default_factory=DynamicInput)

    @model_validator(mode="after")
    def validate_evaluation(self) -> "EvaluateRequest":
        values = self.model_dump(exclude={"dynamic"})
        if any(not isfinite(float(v)) for v in values.values() if isinstance(v, (int, float))):
            raise ValueError("evaluation numeric values must be finite")
        if self.warmup_hours >= self.hours:
            raise ValueError("warmup_hours must be smaller than hours")
        return self

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

@app.get("/")
@app.get("/api/")
def root():
    frontend = Path(__file__).resolve().parent.parent / "web" / "index.html"
    if not frontend.is_file():
        raise HTTPException(status_code=500, detail="web/index.html not found")
    return FileResponse(frontend, media_type="text/html")

@app.get("/health")
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "gurobean-engine", "version": API_VERSION, "release_marker": RELEASE_MARKER, "ai": "grounded-local"}

@app.get("/metadata")
@app.get("/api/metadata")
def metadata() -> dict:
    return {"rounds": {"implemented": [1, 2, 3, 4, 5, 6, 7, 8], "analytical_gurobi_certified": [1, 2, 3, 4], "simulation_enabled": [5, 6, 7, 8], "formal_game_certification_required": [5, 6, 7, 8]}, "backends": ["scipy", "gurobi", "closed_form", "simulation"], "gurobi_backend": "solver-backed-pwl-for-r1-r4", "gurobi_license_required": True, "simulation_backend": "common-random-numbers-monte-carlo-coordinate-search", "evaluation_backend": "repeated-simulation-with-95ci", "ai": {"enabled": True, "provider": "local-evidence-or-ollama", "grounded": True}, "note": "R5-R8 are operational simulation rounds. Their coefficients are explicit inputs; the engine does not present them as formal game-parity certification until real-game evidence passes the evidence gate."}

@app.get("/ai/context")
@app.get("/api/ai/context")
def ai_context() -> dict:
    return evidence_context()

@app.post("/ai/ask")
@app.post("/api/ai/ask")
def ai_ask(request: AskRequest) -> dict:
    try:
        return ask_assistant(request.question)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

@app.post("/solve")
@app.post("/api/solve")
def solve(request: SolveRequest) -> dict:
    if request.round_number <= 4:
        if request.backend == "simulation":
            raise HTTPException(status_code=400, detail="simulation backend is reserved for R5-R8")
        if request.backend == "closed_form" and request.round_number != 1:
            raise HTTPException(status_code=400, detail="closed_form backend is available only for R1")
        try:
            sc = Scenario(**request.scenario.model_dump())
            result = solve_round(request.round_number, sc, backend=request.backend)
        except (ValueError, RuntimeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"ok": True, "round": request.round_number, "result": result}
    if request.backend in {"gurobi", "closed_form"}:
        raise HTTPException(status_code=400, detail="R5-R8 use the simulation backend; Gurobi/PWL certification currently covers R1-R4")
    try:
        sc = Scenario(**request.scenario.model_dump())
        dp = DynamicRoundParams(**request.dynamic.model_dump())
        result = solve_dynamic_round(sc, request.round_number, dp)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "round": request.round_number, "result": result}

@app.post("/evaluate")
@app.post("/api/evaluate")
def evaluate(request: EvaluateRequest) -> dict:
    try:
        scenario = Scenario(**request.scenario.model_dump())
        dynamic = DynamicRoundParams(**request.dynamic.model_dump())
        cost = request.barista_cost_per_hour if request.round_number >= 8 else 0.0
        summary = evaluate_scenario(scenario, markup=request.markup, q_hot=request.q_hot, q_cold=request.q_cold, service_rate=request.service_rate, replications=request.replications, seed=request.seed, hours=request.hours, warmup_hours=request.warmup_hours, barista_cost_per_hour=cost, dynamic=dynamic if request.round_number >= 5 else None, round_number=request.round_number)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "round": request.round_number, "candidate": {"Q_hot": request.q_hot, "Q_cold": request.q_cold, "markup": request.markup, "service_rate": request.service_rate}, "evaluation": summary.as_dict(), "formal_game_certified": False, "note": "Evaluation is a repeated simulation estimate; it is not a Gurobean game certification claim."}
