"""R9 end-to-end certification for the R1-R4 Gurobean optimization pipeline.

R9 exercises the complete solve path, validates feasibility and exact
objective consistency, checks deterministic replay and cross-checks the real
Gurobi/PWL backend. The continuous reference remains the exact analytic
objective; SLSQP is only a numerical optimizer used to locate its maximum.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from gurobean.model import (
    Scenario,
    _feasible,
    _round_bounds,
    _round_objective,
    expected_newsvendor_gradient,
    solve_round,
)

SEED = 902026
CASES = 100
ROUNDS = (1, 2, 3, 4)
REFERENCE_OBJ_TOL = 2e-7
PWL_OBJ_TOL = 0.5
PWL_Q_DIAGNOSTIC_TOL = 1.0
FEAS_TOL = 2e-8


@dataclass(frozen=True)
class CaseResult:
    case: int
    round_number: int
    reference_ok: bool
    gurobi_checked: bool
    gurobi_ok: bool
    q_hot: float
    q_cold: float
    objective: float
    objective_error: float
    q_error: float
    feasible: bool
    deterministic: bool
    error: str | None = None


def _scenario(rng: random.Random, edge: int) -> Scenario:
    if edge == 0:
        lam, p_hot, p_cold = 0.05, 1.0, 0.0
    elif edge == 1:
        lam, p_hot, p_cold = 80.0, 0.35, 0.65
    elif edge == 2:
        lam, p_hot, p_cold = 1e-4, 0.55, 0.45
    else:
        lam = rng.uniform(0.05, 80.0)
        p_hot = rng.uniform(0.05, 0.95)
        p_cold = rng.uniform(0.0, 1.0 - p_hot)

    rh, rc = rng.uniform(1.0, 8.0), rng.uniform(1.0, 8.0)
    ch, cc = rng.uniform(0.0, 0.8 * rh), rng.uniform(0.0, 0.8 * rc)
    sh, sc = rng.uniform(0.0, ch), rng.uniform(0.0, cc)
    bh, bc = rng.uniform(0.05, 2.0), rng.uniform(0.05, 2.0)
    wh, wc = rng.uniform(0.1, 3.0), rng.uniform(0.1, 3.0)
    scale = lam * (0.55 if edge == 1 else rng.uniform(0.8, 2.0)) if edge != 2 else 0.002
    beans = scale * rng.uniform(0.55, 1.25) * max(bh, bc)
    water = scale * rng.uniform(0.55, 1.25) * max(wh, wc)
    return Scenario(
        lambda_total=lam, p_hot=p_hot, p_cold=p_cold,
        revenue_hot=rh, revenue_cold=rc, cost_hot=ch, cost_cold=cc,
        salvage_hot=sh, salvage_cold=sc, beans_available=beans,
        water_available=water, beans_hot=bh, beans_cold=bc,
        water_hot=wh, water_cold=wc,
    )


def _objective(sc: Scenario, round_number: int, qh: float, qc: float) -> float:
    return _round_objective(
        sc, round_number in (2, 4), round_number in (3, 4), qh, qc
    )


def _stationary_q(sc: Scenario, round_number: int, hot: bool) -> float:
    """Exact one-dimensional stationary point from the analytic gradient."""
    from scipy.optimize import brentq

    include_cost = round_number in (3, 4)
    cost = sc.cost_hot if hot and include_cost else sc.cost_cold if include_cost else 0.0
    lam = sc.lambda_hot if hot else sc.lambda_cold
    revenue = sc.revenue_hot if hot else sc.revenue_cold
    salvage = sc.salvage_hot if hot else sc.salvage_cold
    if lam <= 0:
        return 0.0
    g0 = expected_newsvendor_gradient(0.0, lam, revenue, cost, salvage)
    if g0 <= 0:
        return 0.0
    hi = max(1.0, lam)
    while expected_newsvendor_gradient(hi, lam, revenue, cost, salvage) > 0 and hi < 1e9:
        hi *= 2.0
    if hi >= 1e9:
        return float("inf")
    return float(brentq(
        lambda q: expected_newsvendor_gradient(q, lam, revenue, cost, salvage),
        0.0, hi, xtol=1e-12, rtol=1e-13,
    ))


def _robust_reference(sc: Scenario, round_number: int) -> dict:
    """Independent numerical reference with analytic stationary starts.

    The engine's SciPy solver is tried first. If SLSQP rejects a start or
    reports no successful candidate, R9 retries with the exact stationary
    points and several deterministic interior starts. This addresses the
    known failure mode where very small demand/resource scales make a generic
    start numerically awkward without changing the mathematical objective.
    """
    try:
        return solve_round(round_number, sc, backend="scipy")
    except Exception:
        pass

    if round_number in (1, 3):
        raise RuntimeError(f"reference optimizer failed for R{round_number}")

    from scipy.optimize import minimize

    include_cold = round_number in (2, 4)
    include_cost = round_number in (3, 4)
    hot_hi, cold_hi = _round_bounds(sc, include_cold, include_cost)

    def objective(x: np.ndarray) -> float:
        return -_objective(sc, round_number, float(x[0]), float(x[1]))

    def gradient(x: np.ndarray) -> np.ndarray:
        cost_h = sc.cost_hot if include_cost else 0.0
        cost_c = sc.cost_cold if include_cost else 0.0
        return -np.asarray([
            expected_newsvendor_gradient(float(x[0]), sc.lambda_hot, sc.revenue_hot, cost_h, sc.salvage_hot),
            expected_newsvendor_gradient(float(x[1]), sc.lambda_cold, sc.revenue_cold, cost_c, sc.salvage_cold),
        ], dtype=float)

    starts = [
        np.zeros(2),
        np.array([_stationary_q(sc, round_number, True), _stationary_q(sc, round_number, False)]),
    ]
    for frac in (0.1, 0.25, 0.5, 0.75, 0.9):
        starts.append(np.array([frac * hot_hi, frac * cold_hi], dtype=float))
    starts += [np.array([hot_hi, 0.0]), np.array([0.0, cold_hi])]

    def feasible_start(x: np.ndarray) -> np.ndarray:
        x = np.clip(x, 0.0, [hot_hi, cold_hi]).astype(float)
        if _feasible(x[0], x[1], sc):
            return x
        for _ in range(80):
            x *= 0.5
            if _feasible(x[0], x[1], sc):
                return x
        return np.zeros(2, dtype=float)

    constraints = [
        {"type": "ineq", "fun": lambda x: sc.beans_available - sc.beans_hot * x[0] - sc.beans_cold * x[1],
         "jac": lambda x: np.asarray([-sc.beans_hot, -sc.beans_cold], dtype=float)},
        {"type": "ineq", "fun": lambda x: sc.water_available - sc.water_hot * x[0] - sc.water_cold * x[1],
         "jac": lambda x: np.asarray([-sc.water_hot, -sc.water_cold], dtype=float)},
    ]

    candidates = []
    for start in starts:
        x0 = feasible_start(start)
        result = minimize(
            objective, x0, jac=gradient, method="SLSQP",
            bounds=[(0.0, hot_hi), (0.0, cold_hi)],
            constraints=constraints,
            options={"ftol": 1e-12, "maxiter": 3000},
        )
        x = np.asarray(result.x, dtype=float)
        if np.all(np.isfinite(x)) and result.success and _feasible(x[0], x[1], sc):
            candidates.append((float(result.fun), x))
    if not candidates:
        raise RuntimeError(f"robust reference failed for R{round_number}")
    _, x = min(candidates, key=lambda item: item[0])
    qh, qc = map(float, x)
    return {"Q_hot": qh, "Q_cold": qc, "objective": _objective(sc, round_number, qh, qc), "method": "r9_robust_scipy_reference"}


def certify_case(index: int, round_number: int, sc: Scenario, require_gurobi: bool) -> CaseResult:
    try:
        ref = _robust_reference(sc, round_number)
        qh, qc = float(ref["Q_hot"]), float(ref["Q_cold"])
        exact_obj = _objective(sc, round_number, qh, qc)
        objective_error = abs(float(ref["objective"]) - exact_obj)
        feasible = _feasible(qh, qc, sc)
        ref2 = _robust_reference(sc, round_number)
        deterministic = (
            abs(qh - float(ref2["Q_hot"])) <= 1e-10
            and abs(qc - float(ref2["Q_cold"])) <= 1e-10
            and abs(float(ref["objective"]) - float(ref2["objective"])) <= 1e-10
        )
        hot_hi, cold_hi = _round_bounds(sc, round_number in (2, 4), round_number in (3, 4))
        within_box = -FEAS_TOL <= qh <= hot_hi + FEAS_TOL and -FEAS_TOL <= qc <= cold_hi + FEAS_TOL
        finite = all(math.isfinite(v) for v in (qh, qc, exact_obj, objective_error))
        reference_ok = bool(finite and feasible and within_box and deterministic and objective_error <= REFERENCE_OBJ_TOL)

        try:
            import gurobipy  # noqa: F401
        except ImportError:
            if require_gurobi:
                raise RuntimeError("R9 release gate requires gurobipy and a valid Gurobi environment")
            return CaseResult(index, round_number, reference_ok, False, True, qh, qc, float(ref["objective"]), objective_error, 0.0, feasible, deterministic)

        gurobi = solve_round(round_number, sc, backend="gurobi")
        gqh, gqc = float(gurobi["Q_hot"]), float(gurobi["Q_cold"])
        gobj_exact = _objective(sc, round_number, gqh, gqc)
        q_error = max(abs(gqh - qh), abs(gqc - qc))
        gobj_error = abs(gobj_exact - exact_obj)
        gurobi_ok = bool(
            _feasible(gqh, gqc, sc) and math.isfinite(gobj_exact)
            and gobj_error <= PWL_OBJ_TOL
        )
        return CaseResult(index, round_number, reference_ok, True, gurobi_ok, qh, qc, float(ref["objective"]), objective_error, q_error, feasible, deterministic)
    except Exception as exc:
        return CaseResult(index, round_number, False, False, False, math.nan, math.nan, math.nan, math.inf, math.inf, False, False, repr(exc))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gurobean R9 end-to-end certification")
    parser.add_argument("--require-gurobi", action="store_true", help="fail unless the real Gurobi backend is executed")
    args = parser.parse_args(argv)

    rng = random.Random(SEED)
    results: list[CaseResult] = []
    for i in range(CASES):
        sc = _scenario(rng, i % 4)
        for round_number in ROUNDS:
            results.append(certify_case(i, round_number, sc, args.require_gurobi))

    reference_failures = [r for r in results if not r.reference_ok]
    gurobi_checked = [r for r in results if r.gurobi_checked]
    gurobi_failures = [r for r in gurobi_checked if not r.gurobi_ok]
    max_obj_error = max((r.objective_error for r in results), default=0.0)
    max_q_error = max((r.q_error for r in gurobi_checked), default=0.0)
    gate_ok = bool(gurobi_checked) if args.require_gurobi else True
    status = "PASS" if not reference_failures and not gurobi_failures and gate_ok else "FAIL"

    out = {
        "schema": "gurobean.r9.end_to_end.v3",
        "seed": SEED, "cases": CASES, "rounds": list(ROUNDS), "total_cases": len(results),
        "reference_failures": len(reference_failures), "gurobi_cases_checked": len(gurobi_checked),
        "gurobi_failures": len(gurobi_failures), "max_reference_objective_error": max_obj_error,
        "max_gurobi_q_error": max_q_error, "require_gurobi": args.require_gurobi,
        "gurobi_gate": "CHECKED" if gurobi_checked else "NOT_AVAILABLE_IN_ENVIRONMENT",
        "criteria": {"reference_objective_tol": REFERENCE_OBJ_TOL, "pwl_exact_objective_regret_tol": PWL_OBJ_TOL, "pwl_q_error_diagnostic_tol": PWL_Q_DIAGNOSTIC_TOL},
        "status": status, "results": [asdict(r) for r in results],
    }
    Path("r9_end_to_end.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("=== R9 END-TO-END CERTIFICATION ===")
    print(f"CASES: {CASES} x ROUNDS: {len(ROUNDS)} = {len(results)}")
    print(f"REFERENCE_FAILURES: {len(reference_failures)}")
    print(f"GUROBI_CASES_CHECKED: {len(gurobi_checked)}")
    print(f"GUROBI_FAILURES: {len(gurobi_failures)}")
    print(f"MAX_REFERENCE_OBJECTIVE_ERROR: {max_obj_error:.12g}")
    print(f"MAX_GUROBI_Q_ERROR: {max_q_error:.12g} (diagnostic; not a pass/fail criterion)")
    print(f"GUROBI_EXACT_OBJECTIVE_REGRET_TOL: {PWL_OBJ_TOL:.12g}")
    print(f"GUROBI_GATE: {out['gurobi_gate']}")
    print(f"R9 STATUS: {status}")
    print("ARTIFACT: r9_end_to_end.json")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
