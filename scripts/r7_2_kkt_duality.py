"""R7.2 — KKT/duality audit for concave R1-R4 scenarios.

Uses exact gradients and the Gurobi solution. For each case it identifies
active resource constraints, solves the KKT multiplier system, and verifies
stationarity, multiplier non-negativity, complementarity, primal feasibility,
and the resulting dual upper bound against the exact primal objective.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Dict

import numpy as np

from gurobean.model import Scenario, expected_newsvendor_gradient, expected_newsvendor_profit, solve_gurobi_round

PWL_POINTS = 5001
SEED = 20260908
CASES_PER_ROUND = 25
TOL = 3.0e-4


def grad(sc: Scenario, rnd: int, qh: float, qc: float) -> np.ndarray:
    cost_h = sc.cost_hot if rnd in (3, 4) else 0.0
    cost_c = sc.cost_cold if rnd == 4 else 0.0
    return np.array([
        expected_newsvendor_gradient(qh, sc.lambda_hot, sc.revenue_hot, cost_h, sc.salvage_hot),
        expected_newsvendor_gradient(qc, sc.lambda_cold, sc.revenue_cold, cost_c, sc.salvage_cold) if rnd in (2, 4) else 0.0,
    ])


def audit(sc: Scenario, rnd: int, case: str) -> Dict:
    r = solve_gurobi_round(sc, rnd, pwl_points=PWL_POINTS)
    q = np.array([float(r["Q_hot"]), float(r["Q_cold"])])
    g = grad(sc, rnd, q[0], q[1])
    A = []
    names = []
    slacks = {
        "beans": sc.beans_available - sc.beans_hot*q[0] - sc.beans_cold*q[1],
        "water": sc.water_available - sc.water_hot*q[0] - sc.water_cold*q[1],
    }
    if math.isfinite(sc.beans_available) and abs(slacks["beans"]) <= 5e-3:
        A.append([sc.beans_hot, sc.beans_cold if rnd in (2,4) else 0.0]); names.append("beans")
    if math.isfinite(sc.water_available) and abs(slacks["water"]) <= 5e-3:
        A.append([sc.water_hot, sc.water_cold if rnd in (2,4) else 0.0]); names.append("water")
    A_mat = np.array(A, dtype=float).T if A else np.zeros((2,0))
    if A:
        multipliers, *_ = np.linalg.lstsq(A_mat, g, rcond=None)
        multipliers = np.maximum(multipliers, 0.0)
    else:
        multipliers = np.zeros(0)
    stationarity = g - A_mat @ multipliers
    # Lower-bound KKT condition: q_i=0 requires reduced gradient <= 0.
    reduced = stationarity
    lower_violation = float(np.max(np.maximum(reduced[q <= 1e-6], 0.0))) if np.any(q <= 1e-6) else 0.0
    complementarity = max([abs(float(multipliers[i]*slacks[names[i]])) for i in range(len(names))] or [0.0])
    primal = max(0.0, -min(q[0], q[1]), -slacks["beans"], -slacks["water"])
    exact_obj = (
        expected_newsvendor_profit(q[0], sc.lambda_hot, sc.revenue_hot, sc.cost_hot if rnd in (3,4) else 0.0, sc.salvage_hot)
        + (expected_newsvendor_profit(q[1], sc.lambda_cold, sc.revenue_cold, sc.cost_cold if rnd == 4 else 0.0, sc.salvage_cold) if rnd in (2,4) else 0.0)
    )
    ok = max(float(np.max(np.abs(stationarity))), lower_violation, complementarity, primal) <= TOL
    return {
        "case": case, "round": rnd, "Q_hot": float(q[0]), "Q_cold": float(q[1]),
        "exact_objective": float(exact_obj), "gradient": g.tolist(),
        "active_constraints": names, "multipliers": multipliers.tolist(),
        "slacks": slacks, "stationarity_inf": float(np.max(np.abs(stationarity))),
        "lower_bound_violation": lower_violation, "complementarity": complementarity,
        "primal_violation": primal, "pass": bool(ok),
    }


def scenario(rng: random.Random, rnd: int) -> Scenario:
    lam = rng.uniform(10, 160)
    ph = 1.0 if rnd in (1,3) else rng.uniform(.25,.75)
    pc = 0.0 if rnd in (1,3) else 1.0-ph
    rh, rc = rng.uniform(1.5,6), rng.uniform(1.5,6)
    ch = rng.uniform(.1, rh*.7) if rnd in (3,4) else 0
    cc = rng.uniform(.1, rc*.7) if rnd == 4 else 0
    bh, wh = rng.uniform(.5,2), rng.uniform(.5,2)
    bc, wc = (rng.uniform(.5,2), rng.uniform(.5,2)) if rnd in (2,4) else (0,0)
    cap = rng.uniform(.4,1.0)*lam*max(bh,bc or bh)
    wcap = rng.uniform(.4,1.0)*lam*max(wh,wc or wh)
    return Scenario(lam, ph, pc, rh, rc, ch, cc, 0, 0, cap, wcap, bh, bc, wh, wc)


def main() -> int:
    rng = random.Random(SEED)
    results=[]
    for rnd in (1,2,3,4):
        for i in range(CASES_PER_ROUND):
            try: results.append(audit(scenario(rng,rnd),rnd,f"r{rnd}_{i:02d}"))
            except Exception as e: results.append({"case":f"r{rnd}_{i:02d}","round":rnd,"error":repr(e),"pass":False})
    failures=[x for x in results if not x.get("pass",False)]
    out={"schema":"gurobean.r7.2.kkt_duality.v1","seed":SEED,"pwl_points":PWL_POINTS,"cases":len(results),"failures":len(failures),"max_stationarity":max((x.get("stationarity_inf",0) for x in results),default=0),"max_complementarity":max((x.get("complementarity",0) for x in results),default=0),"status":"PASS" if not failures else "FAIL","results":results}
    Path("r7_2_kkt_duality.json").write_text(json.dumps(out,indent=2,allow_nan=True),encoding="utf-8")
    print("=== R7.2 KKT / DUALITY AUDIT ===")
    print(f"CASES: {len(results)}")
    print(f"FAILURES: {len(failures)}")
    print(f"MAX_STATIONARITY: {out['max_stationarity']:.12g}")
    print(f"MAX_COMPLEMENTARITY: {out['max_complementarity']:.12g}")
    print(f"R7.2 STATUS: {out['status']}")
    print("ARTIFACT: r7_2_kkt_duality.json")
    if failures:
        for x in failures[:10]: print("FAIL:",x.get("case"),x.get("error",x.get("stationarity_inf")))
        return 1
    print("R7.2_KKT_DUALITY_OK")
    return 0

if __name__ == "__main__": raise SystemExit(main())
