"""R9 release gate with adaptive PWL refinement for rare solver-edge cases."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gurobean.model as model
import scripts.r9_end_to_end as r9

REF_TOL = r9.REFERENCE_OBJ_TOL
OBJ_TOL = r9.PWL_OBJ_TOL
BASE_POINTS = r9.R9_PWL_POINTS
REFINE_POINTS = (5001, 10001, 20001)


def check(sc, round_number, points):
    ref = r9._robust_reference(sc, round_number)
    qh, qc = float(ref["Q_hot"]), float(ref["Q_cold"])
    exact_ref = r9._objective(sc, round_number, qh, qc)
    ref_ok = (
        r9._feasible(qh, qc, sc)
        and abs(float(ref["objective"]) - exact_ref) <= REF_TOL
        and math.isfinite(exact_ref)
    )
    g = model.solve_gurobi_round(sc, round_number, pwl_points=points)
    gqh, gqc = float(g["Q_hot"]), float(g["Q_cold"])
    gexact = r9._objective(sc, round_number, gqh, gqc)
    regret = abs(gexact - exact_ref)
    feasible = r9._gurobi_feasible(gqh, gqc, sc)
    return ref_ok, feasible and math.isfinite(gexact) and regret <= OBJ_TOL, regret, max(abs(gqh-qh), abs(gqc-qc))


def main() -> int:
    rng = __import__("random").Random(r9.SEED)
    total = r9.CASES * len(r9.ROUNDS)
    checked = failures = refined = 0
    max_regret = max_q = 0.0
    refinement_log = []

    for i in range(r9.CASES):
        sc = r9._scenario(rng, i % 4)
        for rn in r9.ROUNDS:
            checked += 1
            ref_ok, ok, regret, qerr = check(sc, rn, BASE_POINTS)
            if not ref_ok:
                failures += 1
                refinement_log.append((i, rn, "reference"))
                continue
            max_regret = max(max_regret, regret)
            max_q = max(max_q, qerr)
            if ok:
                continue
            resolved = False
            for points in REFINE_POINTS:
                refined += 1
                _, retry_ok, retry_regret, retry_qerr = check(sc, rn, points)
                max_regret = max(max_regret, retry_regret)
                max_q = max(max_q, retry_qerr)
                if retry_ok:
                    resolved = True
                    refinement_log.append((i, rn, points))
                    break
            if not resolved:
                failures += 1
                refinement_log.append((i, rn, "unresolved"))

    print("=== R9 RELEASE CERTIFICATION ===")
    print(f"CASES: {r9.CASES} x ROUNDS: {len(r9.ROUNDS)} = {total}")
    print(f"GUROBI_CASES_CHECKED: {checked}")
    print(f"BASE_PWL_POINTS: {BASE_POINTS}")
    print(f"REFINED_SOLVES: {refined}")
    print(f"FAILURES: {failures}")
    print(f"MAX_EXACT_OBJECTIVE_REGRET: {max_regret:.12g}")
    print(f"MAX_Q_ERROR: {max_q:.12g} (diagnostic)")
    print(f"STATUS: {'PASS' if failures == 0 else 'FAIL'}")
    if refinement_log:
        print(f"REFINEMENT_EVENTS: {refinement_log}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
