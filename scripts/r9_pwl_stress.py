"""R9 stress audit for the nine previously failing R2/R4 scenarios."""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.r9_end_to_end as r9
from gurobean.model import expected_newsvendor_gradient, _round_bounds

FAIL_CASES = {(37, 2), (37, 4), (73, 2), (73, 4), (77, 2), (81, 2), (81, 4), (85, 4), (93, 2)}
MESHES = (2001, 5001, 10001, 20001)


def exact_gradient(sc, round_number, qh, qc):
    include_cost = round_number in (3, 4)
    return (
        expected_newsvendor_gradient(qh, sc.lambda_hot, sc.revenue_hot, sc.cost_hot if include_cost else 0.0, sc.salvage_hot),
        expected_newsvendor_gradient(qc, sc.lambda_cold, sc.revenue_cold, sc.cost_cold if include_cost else 0.0, sc.salvage_cold),
    )


def main() -> int:
    rng = random.Random(r9.SEED)
    scenarios = {i: r9._scenario(rng, i % 4) for i in range(r9.CASES)}
    worst = 0.0
    failures = []
    print("R9 NATIVE PWL OBJECTIVE STRESS AUDIT")
    print("=" * 96)
    for case, rn in sorted(FAIL_CASES):
        sc = scenarios[case]
        ref_obj = float(r9._robust_reference(sc, rn)["objective"])
        print(f"CASE={case} ROUND={rn} REF={ref_obj:.15f}")
        previous = math.inf
        for mesh in MESHES:
            g = r9.solve_gurobi_round(sc, rn, pwl_points=mesh)
            qh, qc = float(g["Q_hot"]), float(g["Q_cold"])
            exact = r9._objective(sc, rn, qh, qc)
            regret = abs(exact - ref_obj)
            beans = sc.beans_hot * qh + sc.beans_cold * qc
            water = sc.water_hot * qh + sc.water_cold * qc
            gh, gc = exact_gradient(sc, rn, qh, qc)
            bh, bc = sc.beans_hot, sc.beans_cold
            bean_lambda_gap = abs(gh / bh - gc / bc) if bh > 0 and bc > 0 else math.nan
            hot_hi, cold_hi = _round_bounds(sc, rn in (2, 4), rn in (3, 4))
            feasible = (-1e-8 <= qh <= hot_hi + 1e-8 and -1e-8 <= qc <= cold_hi + 1e-8 and beans <= sc.beans_available + 1e-8 and water <= sc.water_available + 1e-8)
            print(f"  mesh={mesh:5d} q=({qh:.12f},{qc:.12f}) regret={regret:.12g} bean_gap={bean_lambda_gap:.12g} slack=({sc.beans_available-beans:.12g},{sc.water_available-water:.12g}) feasible={feasible}")
            worst = max(worst, regret)
            if not feasible:
                failures.append((case, rn, mesh, "infeasible"))
            if regret >= previous * 1.05 and mesh != MESHES[0]:
                failures.append((case, rn, mesh, "nonconvergent_regret"))
            previous = regret
        print()
    print(f"WORST_EXACT_REGRET={worst:.15g}")
    if failures:
        print("FAILURES:")
        for item in failures:
            print(" ", item)
        return 1
    print("STRESS_AUDIT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
