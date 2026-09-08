"""R7.3 — Bounded empirical certification of PWL approximation error.

The first harness attempted 800 Gurobi solves (40 cases x 4 rounds x 5
breakpoint counts). That is unnecessarily expensive because every solve
rebuilds a large PWL representation. R7.3 therefore uses a small, deterministic
coverage set and three representative breakpoint counts, while R7.5 provides
the large-scale default-PWL stress test.

This test never changes production defaults. It evaluates the exact analytic
objective at each PWL solution and compares it with an independent reference.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np

from gurobean.model import (
    Scenario,
    solve_gurobi_round,
    solve_round_scipy,
    _round_objective,
)

SEED = 20260908
POINTS = (1001, 5001, 20001)
CASES_PER_ROUND = 3
OBJ_TOL = 3e-2


def sc(rng, rnd):
    lam = rng.uniform(10, 180)
    ph = 1 if rnd in (1, 3) else rng.uniform(0.2, 0.8)
    pc = 0 if rnd in (1, 3) else 1 - ph
    rh, rc = rng.uniform(1, 6), rng.uniform(1, 6)
    ch = rng.uniform(0.05, 1.5) if rnd in (3, 4) else 0
    cc = rng.uniform(0.05, 1.5) if rnd == 4 else 0
    bh, wh = rng.uniform(0.4, 2), rng.uniform(0.4, 2)
    bc, wc = (
        (rng.uniform(0.4, 2), rng.uniform(0.4, 2))
        if rnd in (2, 4)
        else (0, 0)
    )
    b = rng.uniform(0.35, 1.0) * lam * max(bh, bc or bh)
    w = rng.uniform(0.35, 1.0) * lam * max(wh, wc or wh)
    return Scenario(lam, ph, pc, rh, rc, ch, cc, 0, 0, b, w, bh, bc, wh, wc)


def main():
    rng = random.Random(SEED)
    rows = []

    for rnd in (1, 2, 3, 4):
        for i in range(CASES_PER_ROUND):
            s = sc(rng, rnd)
            ref = solve_round_scipy(s, rnd)
            ro = float(ref["objective"])

            for pts in POINTS:
                g = solve_gurobi_round(s, rnd, pwl_points=pts)
                qh = float(g["Q_hot"])
                qc = float(g["Q_cold"])
                exact = float(
                    _round_objective(
                        s,
                        rnd in (2, 4),
                        rnd in (3, 4),
                        qh,
                        qc,
                    )
                )
                err = abs(exact - ro)
                rows.append(
                    {
                        "round": rnd,
                        "case": i,
                        "pwl_points": pts,
                        "Q_hot": qh,
                        "Q_cold": qc,
                        "exact_objective": exact,
                        "reference_objective": ro,
                        "objective_error": err,
                        "reference_regret": max(0.0, ro - exact),
                    }
                )

    maxerr = max(x["objective_error"] for x in rows)
    bypts = {
        str(p): {
            "max_objective_error": max(
                x["objective_error"] for x in rows if x["pwl_points"] == p
            ),
            "mean_objective_error": float(
                np.mean(
                    [x["objective_error"] for x in rows if x["pwl_points"] == p]
                )
            ),
        }
        for p in POINTS
    }

    out = {
        "schema": "gurobean.r7.3.pwl_error.v2",
        "seed": SEED,
        "points": POINTS,
        "cases_per_round": CASES_PER_ROUND,
        "total_runs": len(rows),
        "max_objective_error": maxerr,
        "by_points": bypts,
        "status": "PASS" if maxerr <= OBJ_TOL else "FAIL",
        "results": rows,
    }
    Path("r7_3_pwl_error.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )

    print("=== R7.3 PWL ERROR CERTIFICATION ===")
    print("TOTAL RUNS:", len(rows))
    print("MAX_OBJECTIVE_ERROR:", f"{maxerr:.12g}")
    print("R7.3 STATUS:", out["status"])
    print("ARTIFACT: r7_3_pwl_error.json")
    print(
        "R7.3_PWL_ERROR_OK"
        if out["status"] == "PASS"
        else "R7.3_PWL_ERROR_FAIL"
    )
    return 0 if out["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
