"""R9 release gate for the R1-R4 Gurobean optimization engine.

Release certification uses the same independent reference and Gurobi-native
PWL adapter as the end-to-end certification harness. It requires a real,
licensed Gurobi environment, checks all 400 deterministic case/round pairs,
and enforces the strict regret and feasibility gates.
"""
from __future__ import annotations

import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import r9_end_to_end as r9

PWL_POINTS = r9.R9_PWL_POINTS
# Backward-compatible public release-gate name retained for the policy test
# and for tooling that imports the release module. This is the strict exact
# objective regret gate, not the looser exploratory PWL comparison tolerance.
OBJ_TOL = r9.STRICT_REGRET_TOL
STRICT_REGRET_TOL = r9.STRICT_REGRET_TOL
FEAS_TOL = r9.FEAS_TOL
REF_TOL = r9.REFERENCE_OBJ_TOL
REFINE_POINTS = (5001, 10001, 20001)
ARTIFACT = ROOT / "r9_release_certification.json"


def _git_state() -> str:
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    ).strip()
    if dirty:
        raise RuntimeError(
            "working tree must be clean for certification; "
            f"unexpected changes:\n{dirty}"
        )
    return sha


def _check_gurobi_license() -> tuple[int, int, int]:
    import gurobipy as gp

    version = tuple(gp.gurobi.version())
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
    env.dispose()
    return version


def main() -> int:
    commit = _git_state()
    gurobi_version = _check_gurobi_license()

    rng = random.Random(r9.SEED)
    records = []
    for case in range(r9.CASES):
        scenario = r9._scenario(rng, case % 4)
        for round_number in r9.ROUNDS:
            records.append(
                r9.certify_case(
                    case,
                    round_number,
                    scenario,
                    require_gurobi=True,
                    has_gurobi=True,
                )
            )

    failures = [x for x in records if not x.reference_ok or not x.gurobi_ok]
    regrets = [x.regret for x in records if x.gurobi_checked]
    reference_errors = [
        x.objective_error
        for x in records
        if x.gurobi_checked and x.objective_error is not None
    ]

    artifact = {
        "schema": "gurobean.r9.release-certification.v6",
        "git_commit": commit,
        "gurobi_version": gurobi_version,
        "cases": r9.CASES,
        "rounds": list(r9.ROUNDS),
        "cases_checked": len(records),
        "pwl_points": PWL_POINTS,
        "refine_points": list(REFINE_POINTS),
        "reference_objective_tolerance": REF_TOL,
        "exact_objective_regret_tolerance": STRICT_REGRET_TOL,
        "solver_feasibility_tolerance": FEAS_TOL,
        "gurobi_gate": "CHECKED",
        "r5_r8_status": "CALIBRATION_GATED",
        "failures": len(failures),
        "max_exact_regret": max(regrets, default=0.0),
        "max_reference_objective_error": max(reference_errors, default=0.0),
        "records": [x.__dict__ for x in records],
        "status": "PASS" if len(records) == 400 and not failures else "FAIL",
    }
    ARTIFACT.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    print("=== GUROBEAN R9 RELEASE CERTIFICATION ===")
    print(f"GIT_COMMIT: {commit}")
    print(f"GUROBI_VERSION: {gurobi_version}")
    print(f"CASES_CHECKED: {len(records)}")
    print(f"PWL_POINTS: {PWL_POINTS}")
    print(f"REFINE_POINTS: {list(REFINE_POINTS)}")
    print(f"FAILURES: {len(failures)}")
    print(f"MAX_EXACT_REGRET: {max(regrets, default=0.0):.15g}")
    print(
        f"MAX_REFERENCE_OBJECTIVE_ERROR: "
        f"{max(reference_errors, default=0.0):.15g}"
    )
    print("GUROBI_GATE: CHECKED")
    print(f"R9 STATUS: {artifact['status']}")
    print(f"ARTIFACT: {ARTIFACT.name}")
    return 0 if artifact["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
