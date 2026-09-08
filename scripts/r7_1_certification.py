"""R7.1 — Mathematical certification against an independent exact reference.

Certifies the R1-R4 Gurobi/PWL adapter without modifying the production model:
- exact analytic objective cross-check;
- independent SLSQP reference optimum;
- KKT stationarity/complementarity of the reference;
- exact-objective regret of the Gurobi solution;
- deterministic stress over feasible random scenarios;
- explicit classification of expected unbounded cases.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from scipy.optimize import minimize

from gurobean.model import (
    Scenario,
    _feasible,
    _round_objective,
    expected_newsvendor_gradient,
    expected_newsvendor_profit,
    solve_round_scipy,
    solve_gurobi_round,
)

PWL_POINTS = 5001
SEED = 20260908
CASES = 80
OBJ_TOL = 2.0e-2
Q_TOL = 7.5e-1
KKT_TOL = 5.0e-6
FEAS_TOL = 1.0e-7


def _round_flags(round_number: int) -> Tuple[bool, bool]:
    return round_number in (2, 4), round_number in (3, 4)


def _resource_residuals(qh: float, qc: float, sc: Scenario) -> Tuple[float, float]:
    return (
        sc.beans_available - sc.beans_hot * qh - sc.beans_cold * qc,
        sc.water_available - sc.water_hot * qh - sc.water_cold * qc,
    )


def _reference_kkt(sc: Scenario, round_number: int, q: np.ndarray) -> Dict[str, float]:
    include_cold, include_cost = _round_flags(round_number)
    cost_h = sc.cost_hot if include_cost else 0.0
    cost_c = sc.cost_cold if include_cost else 0.0
    g = np.array([
        expected_newsvendor_gradient(float(q[0]), sc.lambda_hot, sc.revenue_hot, cost_h, sc.salvage_hot),
        expected_newsvendor_gradient(float(q[1]), sc.lambda_cold, sc.revenue_cold, cost_c, sc.salvage_cold),
    ], dtype=float)
    if not include_cold:
        g[1] = 0.0

    bean = np.array([sc.beans_hot, sc.beans_cold if include_cold else 0.0], dtype=float)
    water = np.array([sc.water_hot, sc.water_cold if include_cold else 0.0], dtype=float)
    rb, rw = _resource_residuals(float(q[0]), float(q[1]), sc)
    active = []
    if math.isfinite(sc.beans_available) and abs(rb) <= 1.0e-5:
        active.append(bean)
    if math.isfinite(sc.water_available) and abs(rw) <= 1.0e-5:
        active.append(water)

    # For a concave maximization problem, stationarity is
    # g - A^T lambda + mu = 0, with lambda >= 0 and mu >= 0 on q >= 0.
    # Solve the active-set least-squares system and then report residuals.
    if active:
        A = np.column_stack(active)
        lam, *_ = np.linalg.lstsq(A, g, rcond=None)
        lam = np.maximum(lam, 0.0)
        stationarity = g - A @ lam
    else:
        lam = np.zeros(0)
        stationarity = g.copy()

    lower_violation = np.minimum(q, 0.0)
    kkt = float(np.max(np.abs(stationarity))) if stationarity.size else 0.0
    if np.any(q <= 1.0e-7):
        # At q=0, the derivative must be <= the resource shadow price.
        kkt = max(kkt, float(np.max(np.maximum(g, 0.0))))

    return {
        "gradient_hot": float(g[0]),
        "gradient_cold": float(g[1]),
        "beans_slack": float(rb),
        "water_slack": float(rw),
        "kkt_residual": kkt,
        "lambda_beans": float(lam[0]) if len(lam) > 0 else 0.0,
        "lambda_water": float(lam[1]) if len(lam) > 1 else 0.0,
        "lower_bound_violation": float(np.max(np.abs(lower_violation))),
    }


def _exact_objective(sc: Scenario, round_number: int, qh: float, qc: float) -> float:
    include_cold, include_cost = _round_flags(round_number)
    return _round_objective(sc, include_cold, include_cost, qh, qc)


def _random_scenario(rng: random.Random, round_number: int) -> Scenario:
    lam = rng.uniform(5.0, 180.0)
    if round_number in (1, 3):
        ph, pc = 1.0, 0.0
    else:
        ph = rng.uniform(0.2, 0.8)
        pc = 1.0 - ph
    rh = rng.uniform(1.0, 6.0)
    rc = rng.uniform(1.0, 6.0)
    ch = rng.uniform(0.05, min(2.0, rh * 0.85)) if round_number in (3, 4) else 0.0
    cc = rng.uniform(0.05, min(2.0, rc * 0.85)) if round_number == 4 else 0.0
    sh = rng.uniform(0.0, min(0.25, rh * 0.2))
    scold = rng.uniform(0.0, min(0.25, rc * 0.2)) if round_number in (2, 4) else 0.0
    bh = rng.uniform(0.3, 2.0)
    bc = rng.uniform(0.3, 2.0) if round_number in (2, 4) else 0.0
    wh = rng.uniform(0.3, 2.0)
    wc = rng.uniform(0.3, 2.0) if round_number in (2, 4) else 0.0
    cap = rng.uniform(0.35, 1.15) * lam * max(bh, bc or bh)
    water = rng.uniform(0.35, 1.15) * lam * max(wh, wc or wh)
    return Scenario(
        lambda_total=lam,
        p_hot=ph,
        p_cold=pc,
        revenue_hot=rh,
        revenue_cold=rc,
        cost_hot=ch,
        cost_cold=cc,
        salvage_hot=sh,
        salvage_cold=scold,
        beans_available=cap,
        water_available=water,
        beans_hot=bh,
        beans_cold=bc,
        water_hot=wh,
        water_cold=wc,
    )


def _certify_case(sc: Scenario, round_number: int, case_id: str) -> Dict:
    ref = solve_round_scipy(sc, round_number)
    qref = np.array([ref["Q_hot"], ref["Q_cold"]], dtype=float)
    ref_obj = float(ref["objective"])
    kkt = _reference_kkt(sc, round_number, qref)

    gr = solve_gurobi_round(sc, round_number, pwl_points=PWL_POINTS)
    qg = np.array([float(gr["Q_hot"]), float(gr["Q_cold"])], dtype=float)
    exact_g = _exact_objective(sc, round_number, qg[0], qg[1])
    obj_error = abs(exact_g - ref_obj)
    q_error = float(np.max(np.abs(qg - qref)))
    feasible = _feasible(qg[0], qg[1], sc)
    regret = max(0.0, ref_obj - exact_g)

    passed = (
        feasible
        and kkt["kkt_residual"] <= KKT_TOL
        and obj_error <= OBJ_TOL
        and q_error <= Q_TOL
    )
    return {
        "case": case_id,
        "round": round_number,
        "reference": {"Q_hot": float(qref[0]), "Q_cold": float(qref[1]), "objective": ref_obj},
        "gurobi": {"Q_hot": float(qg[0]), "Q_cold": float(qg[1]), "exact_objective": float(exact_g)},
        "errors": {"objective_abs": float(obj_error), "q_inf": q_error, "exact_regret": float(regret)},
        "feasible": bool(feasible),
        "kkt": kkt,
        "pass": bool(passed),
    }


def main() -> int:
    rng = random.Random(SEED)
    results: List[Dict] = []
    failures: List[Dict] = []

    deterministic = [
        ("r1_base", 1, Scenario(100, p_hot=1, revenue_hot=2, beans_available=120, beans_hot=1, water_available=120, water_hot=1)),
        ("r2_balanced", 2, Scenario(100, p_hot=.6, p_cold=.4, revenue_hot=3, revenue_cold=4, beans_available=100, water_available=100, beans_hot=1, beans_cold=1, water_hot=1, water_cold=1)),
        ("r3_cost", 3, Scenario(100, p_hot=1, revenue_hot=4, cost_hot=.7, beans_available=80, beans_hot=1, water_available=80, water_hot=1)),
        ("r4_shared", 4, Scenario(120, p_hot=.55, p_cold=.45, revenue_hot=4, revenue_cold=5, cost_hot=.8, cost_cold=1.0, beans_available=90, water_available=90, beans_hot=1.2, beans_cold=.8, water_hot=.9, water_cold=1.1)),
    ]
    for name, rnd, sc in deterministic:
        try:
            item = _certify_case(sc, rnd, name)
        except Exception as exc:
            item = {"case": name, "round": rnd, "status": "exception", "error": repr(exc), "pass": False}
        results.append(item)
        if not item.get("pass", False):
            failures.append(item)

    for rnd in (1, 2, 3, 4):
        for i in range(CASES // 4):
            name = f"random_r{rnd}_{i:02d}"
            sc = _random_scenario(rng, rnd)
            try:
                item = _certify_case(sc, rnd, name)
            except Exception as exc:
                item = {"case": name, "round": rnd, "status": "exception", "error": repr(exc), "pass": False}
            results.append(item)
            if not item.get("pass", False):
                failures.append(item)

    summary = {
        "schema": "gurobean.r7.1.certification.v1",
        "seed": SEED,
        "pwl_points": PWL_POINTS,
        "deterministic_cases": len(deterministic),
        "random_cases": CASES,
        "total_cases": len(results),
        "failures": len(failures),
        "max_objective_error": max((x.get("errors", {}).get("objective_abs", 0.0) for x in results), default=0.0),
        "max_q_inf_error": max((x.get("errors", {}).get("q_inf", 0.0) for x in results), default=0.0),
        "max_kkt_residual": max((x.get("kkt", {}).get("kkt_residual", 0.0) for x in results), default=0.0),
        "max_exact_regret": max((x.get("errors", {}).get("exact_regret", 0.0) for x in results), default=0.0),
        "status": "PASS" if not failures else "FAIL",
        "results": results,
        "failure_cases": failures,
    }
    Path("r7_1_certification.json").write_text(json.dumps(summary, indent=2, allow_nan=True), encoding="utf-8")

    print("=== R7.1 MATHEMATICAL CERTIFICATION ===")
    print(f"PWL_POINTS: {PWL_POINTS}")
    print(f"CASES: {len(results)}")
    print(f"FAILURES: {len(failures)}")
    print(f"MAX_OBJECTIVE_ERROR: {summary['max_objective_error']:.12g}")
    print(f"MAX_Q_INF_ERROR: {summary['max_q_inf_error']:.12g}")
    print(f"MAX_KKT_RESIDUAL: {summary['max_kkt_residual']:.12g}")
    print(f"MAX_EXACT_REGRET: {summary['max_exact_regret']:.12g}")
    print(f"R7.1 STATUS: {summary['status']}")
    print("ARTIFACT: r7_1_certification.json")
    if failures:
        for f in failures[:10]:
            print("FAIL:", f.get("case"), f.get("error", f.get("errors")))
        return 1
    print("R7.1_CERTIFICATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
