"""R9 end-to-end certification for the R1-R4 Gurobean optimization pipeline.

The continuous reference is solved independently from the Gurobi/PWL adapter.
For R1/R3 the reference is the analytic one-dimensional Newsvendor optimum.
For R2/R4 the exact objective is separable and concave over a 2-D polygon;
R9 therefore enumerates the polygon vertices, optimizes every edge by a
monotone ternary search, and checks the unconstrained stationary point. This
avoids using SLSQP as a mathematical certifier and removes its scale-sensitive
failure modes.

The Gurobi certification mesh is intentionally smaller than the production
adapter default. R9 validates the solver against the exact analytic objective
at the returned point; the mesh only supplies the numerical PWL encoding.
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
    solve_gurobi_round,
)

SEED = 902026
CASES = 100
ROUNDS = (1, 2, 3, 4)
REFERENCE_OBJ_TOL = 2e-7
PWL_OBJ_TOL = 0.5
PWL_Q_DIAGNOSTIC_TOL = 1.0
FEAS_TOL = 2e-8
R9_PWL_POINTS = 2001


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
        p_cold = 1.0 - p_hot

    rh, rc = rng.uniform(1.0, 8.0), rng.uniform(1.0, 8.0)
    ch, cc = rng.uniform(0.0, 0.8 * rh), rng.uniform(0.0, 0.8 * rc)
    # The official game treats unsold coffee as waste; no positive salvage
    # value is part of the R1-R4 game objective.
    sh, sc = 0.0, 0.0
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
    return _round_objective(sc, round_number in (2, 4), round_number in (3, 4), qh, qc)


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


def _ternary_max(sc: Scenario, round_number: int, a: np.ndarray, b: np.ndarray) -> tuple[float, np.ndarray]:
    """Deterministic maximization of a concave objective on a line segment."""
    lo, hi = 0.0, 1.0
    for _ in range(100):
        m1 = (2.0 * lo + hi) / 3.0
        m2 = (lo + 2.0 * hi) / 3.0
        x1 = a + m1 * (b - a)
        x2 = a + m2 * (b - a)
        f1 = _objective(sc, round_number, float(x1[0]), float(x1[1]))
        f2 = _objective(sc, round_number, float(x2[0]), float(x2[1]))
        if f1 < f2:
            lo = m1
        else:
            hi = m2
    candidates = (lo, (lo + hi) / 2.0, hi, 0.0, 1.0)
    best_t = max(candidates, key=lambda t: _objective(sc, round_number, *(a + t * (b - a))))
    x = a + best_t * (b - a)
    return float(_objective(sc, round_number, float(x[0]), float(x[1]))), x


def _polygon_vertices(sc: Scenario, round_number: int) -> list[np.ndarray]:
    """Enumerate all feasible vertices of the 2-D R2/R4 feasible polygon."""
    hot_hi, cold_hi = _round_bounds(sc, round_number in (2, 4), round_number in (3, 4))
    lines = [
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (1.0, 0.0, hot_hi),
        (0.0, 1.0, cold_hi),
        (sc.beans_hot, sc.beans_cold, sc.beans_available),
        (sc.water_hot, sc.water_cold, sc.water_available),
    ]
    vertices: list[np.ndarray] = []
    scale = max(1.0, hot_hi, cold_hi, abs(sc.beans_available), abs(sc.water_available))
    tol = 1e-9 * scale
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            a1, b1, c1 = lines[i]
            a2, b2, c2 = lines[j]
            det = a1 * b2 - a2 * b1
            if abs(det) <= 1e-14 * max(1.0, abs(a1), abs(b1), abs(a2), abs(b2)):
                continue
            qh = (c1 * b2 - c2 * b1) / det
            qc = (a1 * c2 - a2 * c1) / det
            if qh < -tol or qc < -tol or qh > hot_hi + tol or qc > cold_hi + tol:
                continue
            if sc.beans_hot * qh + sc.beans_cold * qc > sc.beans_available + tol:
                continue
            if sc.water_hot * qh + sc.water_cold * qc > sc.water_available + tol:
                continue
            x = np.array([max(0.0, min(hot_hi, qh)), max(0.0, min(cold_hi, qc))], dtype=float)
            if not any(np.max(np.abs(x - y)) <= 1e-9 * max(1.0, np.max(np.abs(x)), np.max(np.abs(y))) for y in vertices):
                vertices.append(x)
    if not vertices:
        raise RuntimeError("R9 reference polygon has no feasible vertex")
    return vertices


def _concave_polygon_reference(sc: Scenario, round_number: int) -> dict:
    """Global reference for the separable concave R2/R4 problem."""
    vertices = _polygon_vertices(sc, round_number)
    hot_hi, cold_hi = _round_bounds(sc, True, round_number == 4)
    stationary = np.array([
        min(hot_hi, _stationary_q(sc, round_number, True)),
        min(cold_hi, _stationary_q(sc, round_number, False)),
    ], dtype=float)
    candidates: list[tuple[float, np.ndarray]] = []
    if _feasible(float(stationary[0]), float(stationary[1]), sc):
        candidates.append((_objective(sc, round_number, float(stationary[0]), float(stationary[1])), stationary))
    for v in vertices:
        candidates.append((_objective(sc, round_number, float(v[0]), float(v[1])), v))
    if len(vertices) >= 2:
        center = np.mean(np.stack(vertices), axis=0)
        ordered = sorted(vertices, key=lambda x: math.atan2(float(x[1] - center[1]), float(x[0] - center[0])))
        for i, a in enumerate(ordered):
            b = ordered[(i + 1) % len(ordered)]
            if np.max(np.abs(a - b)) <= 1e-12:
                continue
            candidates.append(_ternary_max(sc, round_number, a, b))
    value, x = max(candidates, key=lambda item: item[0])
    qh, qc = float(x[0]), float(x[1])
    return {"Q_hot": qh, "Q_cold": qc, "objective": float(value), "method": "r9_exact_concave_polygon"}


def _robust_reference(sc: Scenario, round_number: int) -> dict:
    """Independent reference for R1-R4; never uses Gurobi."""
    if round_number in (1, 3):
        include_cost = round_number == 3
        hot_hi, _ = _round_bounds(sc, False, include_cost)
        q = min(hot_hi, _stationary_q(sc, round_number, True))
        q = max(0.0, float(q))
        return {"Q_hot": q, "Q_cold": 0.0, "objective": _objective(sc, round_number, q, 0.0), "method": "r9_exact_1d"}
    return _concave_polygon_reference(sc, round_number)


def _gurobi_feasible(qh: float, qc: float, sc: Scenario) -> bool:
    """Validate solver output with an explicit floating-point certification tolerance."""
    beans_usage = sc.beans_hot * qh + sc.beans_cold * qc
    water_usage = sc.water_hot * qh + sc.water_cold * qc
    return bool(
        math.isfinite(qh) and math.isfinite(qc)
        and qh >= -FEAS_TOL and qc >= -FEAS_TOL
        and beans_usage <= sc.beans_available + FEAS_TOL
        and water_usage <= sc.water_available + FEAS_TOL
    )


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

        gurobi = solve_gurobi_round(sc, round_number, pwl_points=R9_PWL_POINTS)
        gqh, gqc = float(gurobi["Q_hot"]), float(gurobi["Q_cold"])
        gobj_exact = _objective(sc, round_number, gqh, gqc)
        q_error = max(abs(gqh - qh), abs(gqc - qc))
        gobj_error = abs(gobj_exact - exact_obj)
        gurobi_ok = bool(_gurobi_feasible(gqh, gqc, sc) and math.isfinite(gobj_exact) and gobj_error <= PWL_OBJ_TOL)
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

    artifact = {
        "schema": "gurobean.r9.end-to-end.v2",
        "seed": SEED,
        "cases": CASES,
        "rounds": list(ROUNDS),
        "total_cases": len(results),
        "reference_failures": len(reference_failures),
        "gurobi_cases_checked": len(gurobi_checked),
        "gurobi_failures": len(gurobi_failures),
        "max_reference_objective_error": max_obj_error,
        "max_gurobi_q_error": max_q_error,
        "status": status,
        "criteria": {
            "reference_objective_tol": REFERENCE_OBJ_TOL,
            "pwl_exact_objective_regret_tol": PWL_OBJ_TOL,
            "pwl_q_error_diagnostic_tol": PWL_Q_DIAGNOSTIC_TOL,
            "solver_feasibility_tol": FEAS_TOL,
            "r9_pwl_points": R9_PWL_POINTS,
        },
        "require_gurobi": bool(args.require_gurobi),
        "failures": [asdict(r) for r in results if not r.reference_ok or not r.gurobi_ok],
        "results": [asdict(r) for r in results],
    }
    Path("r9_end_to_end.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    print("=== R9 END-TO-END CERTIFICATION ===")
    print(f"CASES: {CASES} x ROUNDS: {len(ROUNDS)} = {len(results)}")
    print(f"REFERENCE_FAILURES: {len(reference_failures)}")
    print(f"GUROBI_CASES_CHECKED: {len(gurobi_checked)}")
    print(f"GUROBI_FAILURES: {len(gurobi_failures)}")
    print(f"MAX_REFERENCE_OBJECTIVE_ERROR: {max_obj_error:.12g}")
    print(f"MAX_GUROBI_Q_ERROR: {max_q_error:.12g} (diagnostic; not a pass/fail criterion)")
    print(f"GUROBI_EXACT_OBJECTIVE_REGRET_TOL: {PWL_OBJ_TOL}")
    print(f"GUROBI_SOLVER_FEASIBILITY_TOL: {FEAS_TOL}")
    print(f"R9_PWL_POINTS: {R9_PWL_POINTS}")
    print(f"GUROBI_GATE: {'CHECKED' if args.require_gurobi else 'OPTIONAL'}")
    print(f"R9 STATUS: {status}")
    print("ARTIFACT: r9_end_to_end.json")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
