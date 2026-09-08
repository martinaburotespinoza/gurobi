from __future__ import annotations

import json
import math
import random
from pathlib import Path

from gurobean.model import Scenario, solve_gurobi_round

PWL_POINTS = 5001
TOL = 3.0e-3
OBJ_TOL = 1.0e-2
Q_TOL = 5.0e-1

rng = random.Random(20260908)

out = {
    "schema": "gurobean.r6.3.metamorphic.v1",
    "seed": 20260908,
    "pwl_points": PWL_POINTS,
    "cases": [],
    "failures": [],
}

def run(sc, rnd):
    sol = solve_gurobi_round(sc, rnd, pwl_points=PWL_POINTS)
    return {
        "Q_hot": float(sol["Q_hot"]),
        "Q_cold": float(sol["Q_cold"]),
        "objective": float(sol["objective"]),
        "status": sol.get("status"),
    }

def check(test, condition, detail):
    if not condition:
        out["failures"].append({
            "test": test,
            "detail": detail,
        })

print("=== R6.3 METAMORPHIC VALIDATION ===")

# ----------------------------------------------------------------------
# Generate deterministic economically valid R4 scenarios.
# ----------------------------------------------------------------------

scenarios = []

for i in range(12):
    lam = rng.uniform(30.0, 120.0)
    p_hot = rng.uniform(0.25, 0.75)
    p_cold = 1.0 - p_hot

    scenarios.append(
        Scenario(
            lambda_total=lam,
            p_hot=p_hot,
            p_cold=p_cold,
            revenue_hot=rng.uniform(2.0, 4.0),
            revenue_cold=rng.uniform(1.5, 3.5),
            cost_hot=rng.uniform(0.1, 0.8),
            cost_cold=rng.uniform(0.1, 0.8),
            salvage_hot=rng.uniform(0.0, 0.15),
            salvage_cold=rng.uniform(0.0, 0.15),
            beans_available=rng.uniform(35.0, 120.0),
            beans_hot=rng.uniform(0.5, 1.5),
            beans_cold=rng.uniform(0.5, 1.5),
            water_available=rng.uniform(35.0, 120.0),
            water_hot=rng.uniform(0.5, 1.5),
            water_cold=rng.uniform(0.5, 1.5),
        )
    )

# ----------------------------------------------------------------------
# 1. Resource relaxation
# ----------------------------------------------------------------------

print("\n[1] RESOURCE RELAXATION")

for i, sc in enumerate(scenarios):
    base = run(sc, 4)

    relaxed = Scenario(
        lambda_total=sc.lambda_total,
        p_hot=sc.p_hot,
        p_cold=sc.p_cold,
        revenue_hot=sc.revenue_hot,
        revenue_cold=sc.revenue_cold,
        cost_hot=sc.cost_hot,
        cost_cold=sc.cost_cold,
        salvage_hot=sc.salvage_hot,
        salvage_cold=sc.salvage_cold,
        beans_available=sc.beans_available * 1.5,
        water_available=sc.water_available * 1.5,
        beans_hot=sc.beans_hot,
        beans_cold=sc.beans_cold,
        water_hot=sc.water_hot,
        water_cold=sc.water_cold,
    )

    rr = run(relaxed, 4)

    ok = rr["objective"] + TOL >= base["objective"]

    check(
        "resource_relaxation",
        ok,
        {
            "case": i,
            "base": base,
            "relaxed": rr,
        },
    )

    out["cases"].append({
        "type": "resource_relaxation",
        "case": i,
        "base": base,
        "relaxed": rr,
        "pass": ok,
    })

print("resource relaxation:", "PASS" if not any(
    x["test"] == "resource_relaxation"
    for x in out["failures"]
) else "FAIL")

# ----------------------------------------------------------------------
# 2. Cost increase
# ----------------------------------------------------------------------

print("\n[2] COST INCREASE")

for i, sc in enumerate(scenarios):
    base = run(sc, 4)

    expensive = Scenario(
        lambda_total=sc.lambda_total,
        p_hot=sc.p_hot,
        p_cold=sc.p_cold,
        revenue_hot=sc.revenue_hot,
        revenue_cold=sc.revenue_cold,
        cost_hot=sc.cost_hot + 0.5,
        cost_cold=sc.cost_cold + 0.5,
        salvage_hot=sc.salvage_hot,
        salvage_cold=sc.salvage_cold,
        beans_available=sc.beans_available,
        beans_hot=sc.beans_hot,
        beans_cold=sc.beans_cold,
        water_available=sc.water_available,
        water_hot=sc.water_hot,
        water_cold=sc.water_cold,
    )

    ee = run(expensive, 4)

    ok = ee["objective"] <= base["objective"] + TOL

    check(
        "cost_increase",
        ok,
        {
            "case": i,
            "base": base,
            "expensive": ee,
        },
    )

    out["cases"].append({
        "type": "cost_increase",
        "case": i,
        "base": base,
        "expensive": ee,
        "pass": ok,
    })

print("cost increase:", "PASS" if not any(
    x["test"] == "cost_increase"
    for x in out["failures"]
) else "FAIL")

# ----------------------------------------------------------------------
# 3. Revenue increase
# ----------------------------------------------------------------------

print("\n[3] REVENUE INCREASE")

for i, sc in enumerate(scenarios):
    base = run(sc, 4)

    better = Scenario(
        lambda_total=sc.lambda_total,
        p_hot=sc.p_hot,
        p_cold=sc.p_cold,
        revenue_hot=sc.revenue_hot + 0.5,
        revenue_cold=sc.revenue_cold + 0.5,
        cost_hot=sc.cost_hot,
        cost_cold=sc.cost_cold,
        salvage_hot=sc.salvage_hot,
        salvage_cold=sc.salvage_cold,
        beans_available=sc.beans_available,
        beans_hot=sc.beans_hot,
        beans_cold=sc.beans_cold,
        water_available=sc.water_available,
        water_hot=sc.water_hot,
        water_cold=sc.water_cold,
    )

    bb = run(better, 4)

    ok = bb["objective"] + TOL >= base["objective"]

    check(
        "revenue_increase",
        ok,
        {
            "case": i,
            "base": base,
            "better": bb,
        },
    )

    out["cases"].append({
        "type": "revenue_increase",
        "case": i,
        "base": base,
        "better": bb,
        "pass": ok,
    })

print("revenue increase:", "PASS" if not any(
    x["test"] == "revenue_increase"
    for x in out["failures"]
) else "FAIL")

# ----------------------------------------------------------------------
# 4. Uniform scaling of all resource coefficients and capacities.
#
# Multiplying both coefficients and capacity by the same positive factor
# leaves the feasible set unchanged.
# ----------------------------------------------------------------------

print("\n[4] RESOURCE SCALE INVARIANCE")

for i, sc in enumerate(scenarios):
    base = run(sc, 4)
    k = 3.0

    scaled = Scenario(
        lambda_total=sc.lambda_total,
        p_hot=sc.p_hot,
        p_cold=sc.p_cold,
        revenue_hot=sc.revenue_hot,
        revenue_cold=sc.revenue_cold,
        cost_hot=sc.cost_hot,
        cost_cold=sc.cost_cold,
        salvage_hot=sc.salvage_hot,
        salvage_cold=sc.salvage_cold,
        beans_available=sc.beans_available * k,
        beans_hot=sc.beans_hot * k,
        beans_cold=sc.beans_cold * k,
        water_available=sc.water_available * k,
        water_hot=sc.water_hot * k,
        water_cold=sc.water_cold * k,
    )

    ss = run(scaled, 4)

    ok_obj = abs(ss["objective"] - base["objective"]) <= OBJ_TOL
    ok_qh = abs(ss["Q_hot"] - base["Q_hot"]) <= Q_TOL
    ok_qc = abs(ss["Q_cold"] - base["Q_cold"]) <= Q_TOL
    ok = ok_obj and ok_qh and ok_qc

    check(
        "resource_scale_invariance",
        ok,
        {
            "case": i,
            "base": base,
            "scaled": ss,
            "differences": {
                "objective": ss["objective"] - base["objective"],
                "Q_hot": ss["Q_hot"] - base["Q_hot"],
                "Q_cold": ss["Q_cold"] - base["Q_cold"],
            },
        },
    )

    out["cases"].append({
        "type": "resource_scale_invariance",
        "case": i,
        "base": base,
        "scaled": ss,
        "pass": ok,
    })

print("resource scale invariance:", "PASS" if not any(
    x["test"] == "resource_scale_invariance"
    for x in out["failures"]
) else "FAIL")

# ----------------------------------------------------------------------
# 5. Hot/cold label symmetry.
#
# Swap all hot/cold parameters. Objective must remain equal and the
# quantities must swap.
# ----------------------------------------------------------------------

print("\n[5] HOT/COLD LABEL SYMMETRY")

for i, sc in enumerate(scenarios):
    base = run(sc, 4)

    swapped = Scenario(
        lambda_total=sc.lambda_total,
        p_hot=sc.p_cold,
        p_cold=sc.p_hot,
        revenue_hot=sc.revenue_cold,
        revenue_cold=sc.revenue_hot,
        cost_hot=sc.cost_cold,
        cost_cold=sc.cost_hot,
        salvage_hot=sc.salvage_cold,
        salvage_cold=sc.salvage_hot,
        beans_available=sc.beans_available,
        beans_hot=sc.beans_cold,
        beans_cold=sc.beans_hot,
        water_available=sc.water_available,
        water_hot=sc.water_cold,
        water_cold=sc.water_hot,
    )

    sw = run(swapped, 4)

    ok_obj = abs(sw["objective"] - base["objective"]) <= OBJ_TOL
    ok_qh = abs(sw["Q_hot"] - base["Q_cold"]) <= Q_TOL
    ok_qc = abs(sw["Q_cold"] - base["Q_hot"]) <= Q_TOL
    ok = ok_obj and ok_qh and ok_qc

    check(
        "hot_cold_symmetry",
        ok,
        {
            "case": i,
            "base": base,
            "swapped": sw,
        },
    )

    out["cases"].append({
        "type": "hot_cold_symmetry",
        "case": i,
        "base": base,
        "swapped": sw,
        "pass": ok,
    })

print("hot/cold symmetry:", "PASS" if not any(
    x["test"] == "hot_cold_symmetry"
    for x in out["failures"]
) else "FAIL")

# ----------------------------------------------------------------------
# FINAL
# ----------------------------------------------------------------------

out["summary"] = {
    "scenarios": len(scenarios),
    "metamorphic_tests": 5,
    "total_checks": len(scenarios) * 5,
    "failures": len(out["failures"]),
    "status": "PASS" if not out["failures"] else "FAIL",
}

Path("r6_3_metamorphic.json").write_text(
    json.dumps(out, indent=2),
    encoding="utf-8",
)

print("\n========================================")
print("R6.3 STATUS:", out["summary"]["status"])
print("SCENARIOS:", len(scenarios))
print("CHECKS:", out["summary"]["total_checks"])
print("FAILURES:", len(out["failures"]))
print("ARTIFACT: r6_3_metamorphic.json")
print("========================================")

if out["failures"]:
    print(json.dumps(out["failures"], indent=2))
    raise SystemExit(1)

print("R6.3_METAMORPHIC_OK")
