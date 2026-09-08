from __future__ import annotations

import json
import math
from pathlib import Path

from gurobean.model import Scenario, solve_gurobi_round

PWL_POINTS = 5001
TOL = 2.0e-3
FEAS_TOL = 1.0e-6

cases = [
    (
        "r1_zero_demand",
        1,
        Scenario(
            lambda_total=0.0,
            p_hot=1.0,
            p_cold=0.0,
            revenue_hot=2.0,
            cost_hot=0.0,
            beans_available=100.0,
            beans_hot=1.0,
        ),
    ),
    (
        "r1_bean_bottleneck",
        1,
        Scenario(
            lambda_total=100.0,
            p_hot=1.0,
            p_cold=0.0,
            revenue_hot=2.0,
            cost_hot=0.2,
            beans_available=25.0,
            beans_hot=1.0,
        ),
    ),
    (
        "r2_hot_only",
        2,
        Scenario(
            lambda_total=100.0,
            p_hot=1.0,
            p_cold=0.0,
            revenue_hot=2.5,
            revenue_cold=2.5,
            cost_hot=0.2,
            cost_cold=0.2,
            beans_available=40.0,
            beans_hot=1.0,
            beans_cold=1.0,
            water_available=40.0,
            water_hot=1.0,
            water_cold=1.0,
        ),
    ),
    (
        "r2_symmetric",
        2,
        Scenario(
            lambda_total=80.0,
            p_hot=0.5,
            p_cold=0.5,
            revenue_hot=2.0,
            revenue_cold=2.0,
            cost_hot=0.2,
            cost_cold=0.2,
            salvage_hot=0.0,
            salvage_cold=0.0,
            beans_available=50.0,
            beans_hot=1.0,
            beans_cold=1.0,
            water_available=50.0,
            water_hot=1.0,
            water_cold=1.0,
        ),
    ),
    (
        "r4_dual_bottleneck",
        4,
        Scenario(
            lambda_total=120.0,
            p_hot=0.5,
            p_cold=0.5,
            revenue_hot=3.0,
            revenue_cold=3.0,
            cost_hot=0.4,
            cost_cold=0.4,
            beans_available=60.0,
            beans_hot=1.0,
            beans_cold=1.0,
            water_available=60.0,
            water_hot=1.0,
            water_cold=1.0,
        ),
    ),
]

out = {
    "schema": "gurobean.r6.2.degeneracy.v1",
    "pwl_points": PWL_POINTS,
    "cases": {},
    "failures": [],
}

def record_failure(test, detail):
    out["failures"].append({
        "test": test,
        "detail": detail,
    })

print("=== R6.2 DEGENERACY / ALTERNATIVE OPTIMA ===")

for name, rnd, sc in cases:
    sol = solve_gurobi_round(sc, rnd, pwl_points=PWL_POINTS)

    qh = float(sol["Q_hot"])
    qc = float(sol["Q_cold"])
    obj = float(sol["objective"])

    beans_used = sc.beans_hot * qh + sc.beans_cold * qc
    water_used = sc.water_hot * qh + sc.water_cold * qc

    beans_slack = sc.beans_available - beans_used
    water_slack = sc.water_available - water_used

    feasible = (
        qh >= -FEAS_TOL
        and qc >= -FEAS_TOL
        and beans_slack >= -FEAS_TOL
        and water_slack >= -FEAS_TOL
    )

    finite = all(math.isfinite(x) for x in [
        qh, qc, obj, beans_used, water_used
    ])

    if not feasible:
        record_failure(
            f"feasibility_{name}",
            {
                "Q_hot": qh,
                "Q_cold": qc,
                "beans_slack": beans_slack,
                "water_slack": water_slack,
            },
        )

    if not finite:
        record_failure(
            f"finite_{name}",
            sol,
        )

    active = {
        "hot_nonnegative": qh <= FEAS_TOL,
        "cold_nonnegative": qc <= FEAS_TOL,
        "beans": abs(beans_slack) <= FEAS_TOL,
        "water": abs(water_slack) <= FEAS_TOL,
    }

    out["cases"][name] = {
        "round": rnd,
        "Q_hot": qh,
        "Q_cold": qc,
        "objective": obj,
        "beans_used": beans_used,
        "beans_slack": beans_slack,
        "water_used": water_used,
        "water_slack": water_slack,
        "active_constraints": active,
        "feasible": feasible,
        "status": sol.get("status"),
    }

    print(
        f"{name:22s} "
        f"Qh={qh:12.6f} "
        f"Qc={qc:12.6f} "
        f"obj={obj:14.8f} "
        f"bean_slack={beans_slack:10.6g} "
        f"water_slack={water_slack:10.6g}"
    )

# ----------------------------------------------------------------------
# SYMMETRY TEST
# ----------------------------------------------------------------------

print("\n=== SYMMETRY ===")

sym = out["cases"]["r2_symmetric"]

symmetry_ok = abs(sym["Q_hot"] - sym["Q_cold"]) <= 1.0e-3

if not symmetry_ok:
    record_failure(
        "symmetric_allocation",
        {
            "Q_hot": sym["Q_hot"],
            "Q_cold": sym["Q_cold"],
        },
    )

print(
    f"Q_hot={sym['Q_hot']:.10f} "
    f"Q_cold={sym['Q_cold']:.10f} "
    f"PASS={symmetry_ok}"
)

# ----------------------------------------------------------------------
# ZERO-DEMAND INVARIANT
# ----------------------------------------------------------------------

print("\n=== ZERO DEMAND ===")

zero = out["cases"]["r1_zero_demand"]

zero_ok = (
    abs(zero["Q_hot"]) <= TOL
    and abs(zero["objective"]) <= TOL
)

if not zero_ok:
    record_failure(
        "zero_demand",
        zero,
    )

print(
    f"Q_hot={zero['Q_hot']:.10f} "
    f"objective={zero['objective']:.10f} "
    f"PASS={zero_ok}"
)

# ----------------------------------------------------------------------
# BOTTLENECK INVARIANT
# ----------------------------------------------------------------------

print("\n=== RESOURCE BOTTLENECK ===")

bottle = out["cases"]["r1_bean_bottleneck"]

bottle_ok = (
    abs(bottle["beans_slack"]) <= TOL
    and bottle["Q_hot"] <= 25.0 + TOL
)

if not bottle_ok:
    record_failure(
        "bean_bottleneck",
        bottle,
    )

print(
    f"Q_hot={bottle['Q_hot']:.10f} "
    f"beans_slack={bottle['beans_slack']:.10f} "
    f"PASS={bottle_ok}"
)

# ----------------------------------------------------------------------
# DUAL RESOURCE BOTTLENECK
# ----------------------------------------------------------------------

print("\n=== DUAL BOTTLENECK ===")

dual = out["cases"]["r4_dual_bottleneck"]

dual_ok = (
    abs(dual["beans_slack"]) <= TOL
    and abs(dual["water_slack"]) <= TOL
)

if not dual_ok:
    record_failure(
        "dual_resource_bottleneck",
        dual,
    )

print(
    f"beans_slack={dual['beans_slack']:.10f} "
    f"water_slack={dual['water_slack']:.10f} "
    f"PASS={dual_ok}"
)

# ----------------------------------------------------------------------
# FINAL
# ----------------------------------------------------------------------

out["summary"] = {
    "cases": len(cases),
    "failures": len(out["failures"]),
    "status": "PASS" if not out["failures"] else "FAIL",
}

Path("r6_2_degeneracy.json").write_text(
    json.dumps(out, indent=2),
    encoding="utf-8",
)

print("\n========================================")
print("R6.2 STATUS:", out["summary"]["status"])
print("FAILURES:", len(out["failures"]))
print("ARTIFACT: r6_2_degeneracy.json")
print("========================================")

if out["failures"]:
    print(json.dumps(out["failures"], indent=2))
    raise SystemExit(1)

print("R6.2_DEGENERACY_OK")
