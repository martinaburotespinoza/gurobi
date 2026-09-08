"""Strict local release gate for R1-R4 with real Gurobi."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.r9_end_to_end as r9
from gurobean.model import solve_gurobi_round

EXACT_REGRET_TOL = 2e-6
FEAS_TOL = 1e-8
MESH = 20001


def main() -> int:
    try:
        import gurobipy as gp
        version = gp.gurobi.version()
    except Exception as exc:
        print(f"Gurobi environment unavailable: {exc!r}")
        return 2

    rng = random.Random(r9.SEED)
    worst = None
    failures = []
    checked = 0
    for i in range(r9.CASES):
        sc = r9._scenario(rng, i % 4)
        for rn in r9.ROUNDS:
            ref = r9._robust_reference(sc, rn)
            ref_obj = float(ref["objective"])
            g = solve_gurobi_round(sc, rn, pwl_points=MESH)
            qh, qc = float(g["Q_hot"]), float(g["Q_cold"])
            exact = r9._objective(sc, rn, qh, qc)
            regret = abs(exact - ref_obj)
            beans = sc.beans_hot * qh + sc.beans_cold * qc
            water = sc.water_hot * qh + sc.water_cold * qc
            feasible = (math.isfinite(qh) and math.isfinite(qc) and qh >= -FEAS_TOL and qc >= -FEAS_TOL and beans <= sc.beans_available + FEAS_TOL and water <= sc.water_available + FEAS_TOL)
            checked += 1
            record = (regret, i, rn, qh, qc, exact, ref_obj, beans, water)
            if worst is None or regret > worst[0]:
                worst = record
            if not feasible or regret > EXACT_REGRET_TOL:
                failures.append(record)

    print("=== GUROBEAN STRICT R1-R4 RELEASE GATE ===")
    print(f"GUROBI_VERSION: {version}")
    print(f"CASES_CHECKED: {checked}")
    print(f"MESH: {MESH}")
    print(f"EXACT_REGRET_TOL: {EXACT_REGRET_TOL}")
    print(f"FEAS_TOL: {FEAS_TOL}")
    if worst:
        print(f"WORST_REGRET: {worst[0]:.15g} CASE={worst[1]} ROUND={worst[2]}")
    print(f"FAILURES: {len(failures)}")
    for regret, i, rn, qh, qc, exact, ref_obj, beans, water in failures:
        print(f"FAIL CASE={i} R{rn} regret={regret:.15g} Q=({qh:.15g},{qc:.15g}) exact={exact:.15g} ref={ref_obj:.15g} beans_usage={beans:.15g} water_usage={water:.15g}")
    status = "PASS" if not failures else "FAIL"
    print(f"STRICT_GATE: {status}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
