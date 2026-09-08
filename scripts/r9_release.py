"""R9 release gate for licensed production Gurobi certification.

This gate is intentionally stricter than the ordinary R9 harness:
- the real Gurobi binding must be importable;
- the model must return OPTIMAL;
- the returned point must be feasible against the explicit resource model;
- the exact analytical objective at the returned point must be within the
  release regret tolerance of the independent concave reference;
- Gurobi's reported PWL objective must also agree with the exact objective;
- every result is written to a deterministic JSON artifact.

R5-R8 game dynamics are not enabled here because their empirical equations
remain calibration-gated. This file certifies the mathematically closed R1-R4
production core only.
"""
from __future__ import annotations

import json
import math
import random
import sys
from dataclasses import asdict, dataclass
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
ARTIFACT = ROOT / "r9_release_certification.json"


@dataclass(frozen=True)
class CheckResult:
    case: int
    round_number: int
    pwl_points: int
    reference_ok: bool
    gurobi_status: int
    feasible: bool
    exact_objective: float
    reference_objective: float
    exact_regret: float
    solver_objective: float
    solver_objective_error: float
    q_hot: float
    q_cold: float
    reference_q_hot: float
    reference_q_cold: float
    q_error: float
    passed: bool
    error: str | None = None


def check(sc, round_number: int, points: int) -> CheckResult:
    ref = r9._robust_reference(sc, round_number)
    rq_h = float(ref["Q_hot"])
    rq_c = float(ref["Q_cold"])
    ref_obj = float(ref["objective"])
    exact_ref = float(r9._objective(sc, round_number, rq_h, rq_c))
    reference_ok = bool(
        r9._feasible(rq_h, rq_c, sc)
        and math.isfinite(exact_ref)
        and abs(ref_obj - exact_ref) <= REF_TOL
    )
    if not reference_ok:
        return CheckResult(
            case=-1,
            round_number=round_number,
            pwl_points=points,
            reference_ok=False,
            gurobi_status=-1,
            feasible=False,
            exact_objective=math.nan,
            reference_objective=exact_ref,
            exact_regret=math.inf,
            solver_objective=math.nan,
            solver_objective_error=math.inf,
            q_hot=math.nan,
            q_cold=math.nan,
            reference_q_hot=rq_h,
            reference_q_cold=rq_c,
            q_error=math.inf,
            passed=False,
            error="independent reference failed",
        )

    g = model.solve_gurobi_round(sc, round_number, pwl_points=points)
    qh = float(g["Q_hot"])
    qc = float(g["Q_cold"])
    exact_obj = float(r9._objective(sc, round_number, qh, qc))
    solver_obj = float(g["objective"])
    exact_regret = abs(exact_obj - exact_ref)
    solver_obj_error = abs(solver_obj - exact_obj)
    feasible = r9._gurobi_feasible(qh, qc, sc)
    status = int(g["status"])
    q_error = max(abs(qh - rq_h), abs(qc - rq_c))
    passed = bool(
        status == 2
        and feasible
        and math.isfinite(exact_obj)
        and math.isfinite(solver_obj)
        and exact_regret <= OBJ_TOL
        and solver_obj_error <= OBJ_TOL
    )
    return CheckResult(
        case=-1,
        round_number=round_number,
        pwl_points=points,
        reference_ok=True,
        gurobi_status=status,
        feasible=feasible,
        exact_objective=exact_obj,
        reference_objective=exact_ref,
        exact_regret=exact_regret,
        solver_objective=solver_obj,
        solver_objective_error=solver_obj_error,
        q_hot=qh,
        q_cold=qc,
        reference_q_hot=rq_h,
        reference_q_cold=rq_c,
        q_error=q_error,
        passed=passed,
    )


def main() -> int:
    # Import and license failures are deliberately fatal: this is a release
    # gate, not a reference-only smoke test.
    try:
        import gurobipy as gp
        version = tuple(int(x) for x in gp.gurobi.version())
        env = gp.Env(empty=True)
        env.setParam("OutputFlag", 0)
        env.start()
        env.dispose()
    except Exception as exc:
        print("=== R9 RELEASE CERTIFICATION ===")
        print("STATUS: FAIL")
        print(f"GUROBI_GATE: FAIL ({exc!r})")
        return 1

    rng = random.Random(r9.SEED)
    records: list[CheckResult] = []
    failures: list[dict] = []
    refined = 0

    for i in range(r9.CASES):
        sc = r9._scenario(rng, i % 4)
        for rn in r9.ROUNDS:
            result = check(sc, rn, BASE_POINTS)
            result = CheckResult(i, result.round_number, result.pwl_points, result.reference_ok,
                                 result.gurobi_status, result.feasible, result.exact_objective,
                                 result.reference_objective, result.exact_regret,
                                 result.solver_objective, result.solver_objective_error,
                                 result.q_hot, result.q_cold, result.reference_q_hot,
                                 result.reference_q_cold, result.q_error, result.passed, result.error)
            if not result.passed and result.reference_ok:
                resolved = False
                for points in REFINE_POINTS:
                    refined += 1
                    retry = check(sc, rn, points)
                    retry = CheckResult(i, retry.round_number, retry.pwl_points, retry.reference_ok,
                                        retry.gurobi_status, retry.feasible, retry.exact_objective,
                                        retry.reference_objective, retry.exact_regret,
                                        retry.solver_objective, retry.solver_objective_error,
                                        retry.q_hot, retry.q_cold, retry.reference_q_hot,
                                        retry.reference_q_cold, retry.q_error, retry.passed, retry.error)
                    if retry.passed:
                        result = retry
                        resolved = True
                        break
                if not resolved:
                    failures.append(asdict(result))
            elif not result.passed:
                failures.append(asdict(result))
            records.append(result)

    max_regret = max((r.exact_regret for r in records if math.isfinite(r.exact_regret)), default=0.0)
    max_solver_error = max((r.solver_objective_error for r in records if math.isfinite(r.solver_objective_error)), default=0.0)
    max_q_error = max((r.q_error for r in records if math.isfinite(r.q_error)), default=0.0)
    status = "PASS" if not failures else "FAIL"
    artifact = {
        "schema": "gurobean.r9.release-certification.v1",
        "seed": r9.SEED,
        "cases": r9.CASES,
        "rounds": list(r9.ROUNDS),
        "total_checks": len(records),
        "gurobi_version": version,
        "base_pwl_points": BASE_POINTS,
        "refinement_points": list(REFINE_POINTS),
        "refined_solves": refined,
        "failures": len(failures),
        "max_exact_objective_regret": max_regret,
        "max_solver_objective_error": max_solver_error,
        "max_q_error_diagnostic": max_q_error,
        "gurobi_gate": "CHECKED",
        "status": status,
        "records": [asdict(r) for r in records],
        "failure_records": failures,
    }
    ARTIFACT.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")

    print("=== R9 RELEASE CERTIFICATION ===")
    print(f"GUROBI_VERSION: {version}")
    print(f"CASES: {r9.CASES} x ROUNDS: {len(r9.ROUNDS)} = {len(records)}")
    print(f"BASE_PWL_POINTS: {BASE_POINTS}")
    print(f"REFINED_SOLVES: {refined}")
    print(f"FAILURES: {len(failures)}")
    print(f"MAX_EXACT_OBJECTIVE_REGRET: {max_regret:.12g}")
    print(f"MAX_SOLVER_OBJECTIVE_ERROR: {max_solver_error:.12g}")
    print(f"MAX_Q_ERROR: {max_q_error:.12g} (diagnostic)")
    print(f"GUROBI_GATE: CHECKED")
    print(f"R9 STATUS: {status}")
    print(f"ARTIFACT: {ARTIFACT.name}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
