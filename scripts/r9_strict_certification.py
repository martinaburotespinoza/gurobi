"""Unified strict R9 certification gate for R1-R4 with real Gurobi.

This is the authoritative end-to-end gate. It deliberately uses the same
2e-6 exact-objective regret and 1e-8 feasibility tolerances as the strict
release gate, and the production-quality 20,001-point PWL mesh.
"""
from __future__ import annotations

import math
import random

import scripts.r9_end_to_end as r9
from gurobean.model import _round_bounds, _round_objective, solve_gurobi_round

STRICT_REGRET_TOL = 2e-6
FEAS_TOL = 1e-8
PWL_POINTS = 20001


def _check_gurobi_available() -> None:
    try:
        import gurobipy  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Strict R9 certification requires gurobipy") from exc


def main() -> int:
    _check_gurobi_available()
    rng = random.Random(r9.SEED)
    worst_regret = 0.0
    worst_case: tuple[int, int] | None = None
    failures: list[tuple[int, int, str]] = []
    checked = 0

    for case in range(r9.CASES):
        sc = r9._scenario(rng, case % 4)
        for round_number in r9.ROUNDS:
            checked += 1
            try:
                ref = r9._robust_reference(sc, round_number)
                rq_h = float(ref["Q_hot"])
                rq_c = float(ref["Q_cold"])
                ref_obj = float(ref["objective"])
                exact_ref_obj = _round_objective(sc, round_number in (2, 4), round_number in (3, 4), rq_h, rq_c)
                ref_error = abs(ref_obj - exact_ref_obj)
                if not math.isfinite(ref_error) or ref_error > 2e-7:
                    failures.append((case, round_number, f"reference_objective_error={ref_error:.12g}"))
                    continue

                g = solve_gurobi_round(sc, round_number, pwl_points=PWL_POINTS)
                qh = float(g["Q_hot"])
                qc = float(g["Q_cold"])
                exact_obj = _round_objective(sc, round_number in (2, 4), round_number in (3, 4), qh, qc)
                regret = abs(exact_obj - ref_obj)
                worst_regret = max(worst_regret, regret)
                if regret == worst_regret:
                    worst_case = (case, round_number)

                hot_hi, cold_hi = _round_bounds(sc, round_number in (2, 4), round_number in (3, 4))
                beans_usage = sc.beans_hot * qh + sc.beans_cold * qc
                water_usage = sc.water_hot * qh + sc.water_cold * qc
                feasible = (
                    math.isfinite(qh) and math.isfinite(qc) and math.isfinite(exact_obj)
                    and qh >= -FEAS_TOL and qc >= -FEAS_TOL
                    and qh <= hot_hi + FEAS_TOL and qc <= cold_hi + FEAS_TOL
                    and beans_usage <= sc.beans_available + FEAS_TOL
                    and water_usage <= sc.water_available + FEAS_TOL
                )
                if not feasible:
                    failures.append((case, round_number, "solver_output_infeasible"))
                if regret > STRICT_REGRET_TOL:
                    failures.append((case, round_number, f"exact_regret={regret:.12g}"))
            except Exception as exc:
                failures.append((case, round_number, repr(exc)))

    print("=== GUROBEAN UNIFIED STRICT R9 CERTIFICATION ===")
    print("Gurobi backend: REQUIRED")
    print(f"CASES_CHECKED: {checked}")
    print(f"PWL_POINTS: {PWL_POINTS}")
    print(f"EXACT_REGRET_TOL: {STRICT_REGRET_TOL}")
    print(f"FEAS_TOL: {FEAS_TOL}")
    print(f"WORST_REGRET: {worst_regret:.15g}")
    if worst_case:
        print(f"WORST_CASE: {worst_case[0]} ROUND={worst_case[1]}")
    print(f"FAILURES: {len(failures)}")
    if failures:
        for item in failures[:20]:
            print(" ", item)
        print("STRICT_R9_CERTIFICATION: FAIL")
        return 1
    print("STRICT_R9_CERTIFICATION: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
