"""R9 end-to-end certification for the R1-R4 Gurobean optimization pipeline.

R9 is intentionally a certification harness. It exercises the complete public
solve path for R1-R4, validates feasibility and objective consistency against
the exact analytic objective, checks deterministic reference behavior, and
optionally cross-checks the real Gurobi/PWL backend when gurobipy is installed
and licensed. CI without Gurobi still certifies the mathematical/reference
path; the local Gurobi gate is mandatory for release certification.
"""
from __future__ import annotations

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
    solve_round,
)

SEED = 902026
CASES = 100
ROUNDS = (1, 2, 3, 4)
PWL_POINTS = 20001
OBJ_TOL = 2e-7
Q_TOL = 2e-4
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
        lam = 0.05
        p_hot, p_cold = 1.0, 0.0
    elif edge == 1:
        lam = 80.0
        p_hot, p_cold = 0.35, 0.65
    elif edge == 2:
        lam = 1e-4
        p_hot, p_cold = 0.55, 0.45
    else:
        lam = rng.uniform(0.05, 80.0)
        p_hot = rng.uniform(0.05, 0.95)
        p_cold = rng.uniform(0.0, 1.0 - p_hot)

    rh, rc = rng.uniform(1.0, 8.0), rng.uniform(1.0, 8.0)
    ch = rng.uniform(0.0, 0.8 * rh)
    cc = rng.uniform(0.0, 0.8 * rc)
    sh = rng.uniform(0.0, ch)
    sc = rng.uniform(0.0, cc)

    bh, bc = rng.uniform(0.05, 2.0), rng.uniform(0.05, 2.0)
    wh, wc = rng.uniform(0.1, 3.0), rng.uniform(0.1, 3.0)
    if edge == 1:
        scale = lam * 0.55
    elif edge == 2:
        scale = 0.002
    else:
        scale = lam * rng.uniform(0.8, 2.0)
    beans = scale * rng.uniform(0.55, 1.25) * max(bh, bc)
    water = scale * rng.uniform(0.55, 1.25) * max(wh, wc)

    return Scenario(
        lambda_total=lam,
        p_hot=p_hot,
        p_cold=p_cold,
        revenue_hot=rh,
        revenue_cold=rc,
        cost_hot=ch,
        cost_cold=cc,
        salvage_hot=sh,
        salvage_cold=sc,
        beans_available=beans,
        water_available=water,
        beans_hot=bh,
        beans_cold=bc,
        water_hot=wh,
        water_cold=wc,
    )


def _reference(sc: Scenario, round_number: int) -> dict:
    return solve_round(round_number, sc, backend="scipy")


def _objective(sc: Scenario, round_number: int, qh: float, qc: float) -> float:
    return _round_objective(
        sc,
        include_cold=round_number in (2, 4),
        include_brew_cost=round_number in (3, 4),
        qh=qh,
        qc=qc,
    )


def certify_case(index: int, round_number: int, sc: Scenario) -> CaseResult:
    try:
        ref = _reference(sc, round_number)
        qh, qc = float(ref["Q_hot"]), float(ref["Q_cold"])
        expected_obj = _objective(sc, round_number, qh, qc)
        objective_error = abs(float(ref["objective"]) - expected_obj)
        feasible = _feasible(qh, qc, sc)

        ref2 = _reference(sc, round_number)
        deterministic = (
            abs(qh - float(ref2["Q_hot"])) <= 1e-12
            and abs(qc - float(ref2["Q_cold"])) <= 1e-12
            and abs(float(ref["objective"]) - float(ref2["objective"])) <= 1e-12
        )

        hot_hi, cold_hi = _round_bounds(sc, round_number in (2, 4), round_number in (3, 4))
        within_box = (
            -FEAS_TOL <= qh <= hot_hi + FEAS_TOL
            and -FEAS_TOL <= qc <= cold_hi + FEAS_TOL
        )
        finite = all(math.isfinite(v) for v in (qh, qc, expected_obj))
        reference_ok = bool(
            finite and feasible and within_box and deterministic
            and objective_error <= OBJ_TOL
        )

        gurobi_checked = False
        gurobi_ok = True
        q_error = 0.0
        try:
            import gurobipy
        except ImportError:
            gurobipy = None

        if gurobipy is not None:
            gurobi_checked = True
            gurobi = solve_round(round_number, sc, backend="gurobi")
            gqh, gqc = float(gurobi["Q_hot"]), float(gurobi["Q_cold"])
            gobj_exact = _objective(sc, round_number, gqh, gqc)
            q_error = max(abs(gqh - qh), abs(gqc - qc))
            gobj_error = abs(gobj_exact - expected_obj)
            gurobi_ok = bool(
                _feasible(gqh, gqc, sc)
                and math.isfinite(gobj_exact)
                and q_error <= Q_TOL
                and gobj_error <= OBJ_TOL
            )

        return CaseResult(
            index, round_number, reference_ok, gurobi_checked, gurobi_ok,
            qh, qc, float(ref["objective"]), objective_error, q_error,
            feasible, deterministic,
        )
    except Exception as exc:
        return CaseResult(
            index, round_number, False, False, False,
            math.nan, math.nan, math.nan, math.inf, math.inf,
            False, False, repr(exc),
        )


def main() -> int:
    rng = random.Random(SEED)
    results: list[CaseResult] = []
    for i in range(CASES):
        sc = _scenario(rng, i % 4)
        for round_number in ROUNDS:
            results.append(certify_case(i, round_number, sc))

    reference_failures = [r for r in results if not r.reference_ok]
    gurobi_checked = [r for r in results if r.gurobi_checked]
    gurobi_failures = [r for r in gurobi_checked if not r.gurobi_ok]
    max_obj_error = max((r.objective_error for r in results), default=0.0)
    max_q_error = max((r.q_error for r in gurobi_checked), default=0.0)

    status = "PASS" if not reference_failures and not gurobi_failures else "FAIL"
    out = {
        "schema": "gurobean.r9.end_to_end.v1",
        "seed": SEED,
        "cases": CASES,
        "rounds": list(ROUNDS),
        "total_cases": len(results),
        "reference_failures": len(reference_failures),
        "gurobi_cases_checked": len(gurobi_checked),
        "gurobi_failures": len(gurobi_failures),
        "max_reference_objective_error": max_obj_error,
        "max_gurobi_q_error": max_q_error,
        "gurobi_gate": "CHECKED" if gurobi_checked else "NOT_AVAILABLE_IN_ENVIRONMENT",
        "status": status,
        "results": [asdict(r) for r in results],
    }
    Path("r9_end_to_end.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("=== R9 END-TO-END CERTIFICATION ===")
    print(f"CASES: {CASES} x ROUNDS: {len(ROUNDS)} = {len(results)}")
    print(f"REFERENCE_FAILURES: {len(reference_failures)}")
    print(f"GUROBI_CASES_CHECKED: {len(gurobi_checked)}")
    print(f"GUROBI_FAILURES: {len(gurobi_failures)}")
    print(f"MAX_REFERENCE_OBJECTIVE_ERROR: {max_obj_error:.12g}")
    print(f"MAX_GUROBI_Q_ERROR: {max_q_error:.12g}")
    print(f"GUROBI_GATE: {out['gurobi_gate']}")
    print(f"R9 STATUS: {status}")
    print("ARTIFACT: r9_end_to_end.json")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
