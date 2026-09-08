from __future__ import annotations

"""Solver parity and numerical regression checks for the R1-R4 engine.

Parity policy
-------------
The mathematical objective and feasibility are the primary solver invariants.
Decision-variable equality is enforced only when the optimum is identifiable.

The Gurobi R1-R4 adapter currently validates the analytical Normal objective
through a dense PWL representation. Multiple decision vectors can therefore
represent the same optimal objective, especially in degenerate cases.
"""

from dataclasses import dataclass, asdict
from typing import Iterable

import numpy as np

from .model import Scenario, solve_round_scipy, solve_gurobi_round


@dataclass(frozen=True)
class ParityCase:
    round_number: int
    scenario: Scenario
    label: str = ""


@dataclass(frozen=True)
class ParityResult:
    label: str
    round_number: int
    passed: bool
    scipy_objective: float
    gurobi_objective: float | None
    objective_abs_error: float | None
    q_hot_abs_error: float | None
    q_cold_abs_error: float | None
    status: str

    def to_dict(self) -> dict:
        return asdict(self)


def default_parity_cases(seed: int = 20260907, count: int = 24) -> list[ParityCase]:
    """Generate deterministic, feasible stress cases covering R1-R4."""
    if count < 4:
        raise ValueError("count must be >= 4")

    rng = np.random.default_rng(seed)
    cases: list[ParityCase] = []

    for i in range(count):
        round_number = (i % 4) + 1
        lam = float(rng.uniform(1.0, 80.0))
        p_hot = 1.0 if round_number == 1 else float(rng.uniform(0.35, 0.85))
        p_cold = 0.0 if round_number == 1 else 1.0 - p_hot
        revenue_hot = float(rng.uniform(1.0, 6.0))
        revenue_cold = float(rng.uniform(1.0, 6.0))
        cost_hot = 0.0 if round_number < 3 else float(rng.uniform(0.1, 2.0))
        cost_cold = 0.0 if round_number < 3 else float(rng.uniform(0.1, 2.0))
        beans = float(rng.uniform(35.0, 110.0))
        water = float(rng.uniform(40.0, 140.0))

        cases.append(
            ParityCase(
                round_number,
                Scenario(
                    lambda_total=lam,
                    p_hot=p_hot,
                    p_cold=p_cold,
                    revenue_hot=revenue_hot,
                    revenue_cold=revenue_cold,
                    cost_hot=cost_hot,
                    cost_cold=cost_cold,
                    beans_available=beans,
                    water_available=water,
                    beans_hot=float(rng.uniform(0.5, 1.5)),
                    beans_cold=(float(rng.uniform(0.5, 1.5)) if round_number >= 2 else 0.0),
                    water_hot=float(rng.uniform(0.5, 2.0)),
                    water_cold=(float(rng.uniform(0.5, 2.0)) if round_number >= 2 else 0.0),
                ),
                label=f"random_{i:03d}_r{round_number}",
            )
        )

    return cases


def _scenario_feasible(
    scenario: Scenario,
    round_number: int,
    q_hot: float,
    q_cold: float,
    tolerance: float = 1e-7,
) -> bool:
    """Check the physical/resource feasibility of a candidate solution."""
    if q_hot < -tolerance or q_cold < -tolerance:
        return False
    if round_number == 1:
        q_cold = 0.0
    beans_used = q_hot * scenario.beans_hot + q_cold * scenario.beans_cold
    water_used = q_hot * scenario.water_hot + q_cold * scenario.water_cold
    return (
        beans_used <= scenario.beans_available + tolerance
        and water_used <= scenario.water_available + tolerance
    )


def run_parity_suite(
    cases: Iterable[ParityCase] | None = None,
    *,
    pwl_points: int = 2001,
    objective_tolerance: float = 2e-3,
    quantity_tolerance: float = 2e-2,
) -> list[ParityResult]:
    """Compare the analytical/SciPy reference against the Gurobi adapter."""
    if pwl_points < 101:
        raise ValueError("pwl_points must be >= 101")
    if objective_tolerance <= 0 or quantity_tolerance <= 0:
        raise ValueError("tolerances must be > 0")

    cases = list(cases or default_parity_cases())
    results: list[ParityResult] = []

    for case in cases:
        ref = solve_round_scipy(case.scenario, case.round_number)
        try:
            got = solve_gurobi_round(case.scenario, case.round_number, pwl_points=pwl_points)
        except RuntimeError as exc:
            if "gurobipy is not installed" in str(exc):
                results.append(ParityResult(case.label, case.round_number, False, float(ref["objective"]), None, None, None, None, "skipped_gurobi_unavailable"))
                continue
            raise

        scipy_objective = float(ref["objective"])
        gurobi_objective = float(got["objective"])
        obj_err = abs(scipy_objective - gurobi_objective)
        qh_err = abs(float(ref["Q_hot"]) - float(got["Q_hot"]))
        qc_err = abs(float(ref["Q_cold"]) - float(got["Q_cold"]))
        feasible = _scenario_feasible(case.scenario, case.round_number, float(got["Q_hot"]), float(got["Q_cold"]))
        objective_ok = obj_err <= objective_tolerance
        quantities_ok = qh_err <= quantity_tolerance and qc_err <= quantity_tolerance

        if not feasible:
            status, passed = "gurobi_infeasible", False
        elif not objective_ok:
            status, passed = "objective_mismatch", False
        elif quantities_ok:
            status, passed = "passed_exact", True
        else:
            status, passed = "passed_alternative_optimum", True

        results.append(ParityResult(case.label, case.round_number, passed, scipy_objective, gurobi_objective, obj_err, qh_err, qc_err, status))

    return results
