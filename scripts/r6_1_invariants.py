from __future__ import annotations

import json
import math
import random
from pathlib import Path

from gurobean.model import (
    Scenario,
    expected_newsvendor_profit,
    expected_newsvendor_gradient,
    solve_gurobi_round,
)

TOL = 2.0e-3
FEAS_TOL = 1.0e-6
PWL_POINTS = 5001

results = {
    "schema": "gurobean.r6.1.invariants.v1",
    "pwl_points": PWL_POINTS,
    "analytic": {},
    "gurobi": {},
    "failures": [],
}

def fail(name, detail):
    results["failures"].append({
        "test": name,
        "detail": detail,
    })

def check(name, condition, detail):
    if not condition:
        fail(name, detail)
    return condition

print("=== R6.1 MATHEMATICAL INVARIANTS ===")

# ----------------------------------------------------------------------
# A. ANALYTIC OBJECTIVE INVARIANTS
# ----------------------------------------------------------------------

print("\n[A] ANALYTIC OBJECTIVE")

analytic_cases = [
    ("base", 40.0, 40.0, 1.0, 0.0, 0.0),
    ("low_q", 40.0, 10.0, 1.0, 0.0, 0.0),
    ("high_q", 40.0, 80.0, 1.0, 0.0, 0.0),
    ("cost", 40.0, 40.0, 2.0, 0.4, 0.0),
    ("salvage", 40.0, 40.0, 2.0, 0.4, 0.2),
]

for name, lam, q, revenue, cost, salvage in analytic_cases:
    value = expected_newsvendor_profit(
        q, lam, revenue, cost, salvage
    )
    grad = expected_newsvendor_gradient(
        q, lam, revenue, cost, salvage
    )

    results["analytic"][name] = {
        "objective": value,
        "gradient": grad,
    }

    check(
        f"analytic_finite_{name}",
        math.isfinite(value) and math.isfinite(grad),
        f"value={value}, gradient={grad}",
    )

    print(
        f"{name:12s} objective={value:.12f} "
        f"gradient={grad:.12f}"
    )

# ----------------------------------------------------------------------
# B. ANALYTIC CONCAVITY
# ----------------------------------------------------------------------

print("\n[B] ANALYTIC CONCAVITY")

for lam, revenue, cost, salvage in [
    (10.0, 2.0, 0.2, 0.0),
    (40.0, 3.0, 0.5, 0.1),
    (100.0, 5.0, 1.0, 0.2),
]:
    qs = [lam * x / 100.0 for x in range(0, 301)]
    vals = [
        expected_newsvendor_profit(
            q, lam, revenue, cost, salvage
        )
        for q in qs
    ]

    local_ok = True
    for i in range(1, len(qs) - 1):
        second_diff = vals[i + 1] - 2.0 * vals[i] + vals[i - 1]
        if second_diff > 1.0e-8:
            local_ok = False
            fail(
                "analytic_concavity",
                {
                    "lambda": lam,
                    "q": qs[i],
                    "second_difference": second_diff,
                },
            )
            break

    print(
        f"lambda={lam:6.1f} "
        f"concavity={'PASS' if local_ok else 'FAIL'}"
    )

# ----------------------------------------------------------------------
# C. ANALYTIC MONOTONICITY
# ----------------------------------------------------------------------

print("\n[C] ANALYTIC MONOTONICITY")

# Higher revenue cannot reduce expected profit at fixed Q.
for q in [0.0, 10.0, 40.0, 80.0]:
    a = expected_newsvendor_profit(q, 40.0, 1.0, 0.2, 0.0)
    b = expected_newsvendor_profit(q, 40.0, 1.5, 0.2, 0.0)

    check(
        "revenue_monotonicity",
        b + 1e-10 >= a,
        f"q={q}, low={a}, high={b}",
    )

# Higher cost cannot increase expected profit.
for q in [0.0, 10.0, 40.0, 80.0]:
    a = expected_newsvendor_profit(q, 40.0, 2.0, 0.2, 0.0)
    b = expected_newsvendor_profit(q, 40.0, 2.0, 0.8, 0.0)

    check(
        "cost_monotonicity",
        b <= a + 1e-10,
        f"q={q}, low_cost={a}, high_cost={b}",
    )

# More demand must not reduce the optimal value.
for lam_a, lam_b in [(10.0, 20.0), (20.0, 40.0), (40.0, 80.0)]:
    qs = [x / 10.0 for x in range(0, 1501)]

    va = max(
        expected_newsvendor_profit(q, lam_a, 2.0, 0.2, 0.0)
        for q in qs
    )
    vb = max(
        expected_newsvendor_profit(q, lam_b, 2.0, 0.2, 0.0)
        for q in qs
    )

    check(
        "demand_value_monotonicity",
        vb + 1e-6 >= va,
        f"lambda {lam_a}->{lam_b}: {va}->{vb}",
    )

print("Analytic monotonicity: checked")

# ----------------------------------------------------------------------
# D. GUROBI SCENARIOS
# ----------------------------------------------------------------------

print("\n[D] GUROBI FEASIBILITY + OBJECTIVE")

cases = [
    (
        "r1_base",
        1,
        Scenario(
            lambda_total=40,
            p_hot=1.0,
            p_cold=0.0,
            revenue_hot=2.0,
            cost_hot=0.0,
            beans_available=100,
            beans_hot=1.0,
        ),
    ),
    (
        "r2_balanced",
        2,
        Scenario(
            lambda_total=80,
            p_hot=0.60,
            p_cold=0.40,
            revenue_hot=2.4,
            revenue_cold=2.0,
            beans_available=100,
            beans_hot=1.0,
            beans_cold=1.0,
            water_available=100,
            water_hot=1.0,
            water_cold=1.0,
        ),
    ),
    (
        "r3_cost",
        3,
        Scenario(
            lambda_total=80,
            p_hot=0.60,
            p_cold=0.40,
            revenue_hot=2.8,
            revenue_cold=2.2,
            cost_hot=0.35,
            cost_cold=0.25,
            beans_available=100,
            beans_hot=1.0,
            beans_cold=1.0,
            water_available=100,
            water_hot=1.0,
            water_cold=1.0,
        ),
    ),
    (
        "r4_shared_bottleneck",
        4,
        Scenario(
            lambda_total=100,
            p_hot=0.55,
            p_cold=0.45,
            revenue_hot=3.0,
            revenue_cold=2.5,
            cost_hot=0.50,
            cost_cold=0.40,
            beans_available=65,
            beans_hot=1.0,
            beans_cold=1.0,
            water_available=65,
            water_hot=1.0,
            water_cold=1.0,
        ),
    ),
]

for name, rnd, sc in cases:
    sol = solve_gurobi_round(
        sc,
        rnd,
        pwl_points=PWL_POINTS,
    )

    qh = float(sol["Q_hot"])
    qc = float(sol["Q_cold"])
    obj = float(sol["objective"])

    beans_used = sc.beans_hot * qh + sc.beans_cold * qc
    water_used = sc.water_hot * qh + sc.water_cold * qc

    feasible = (
        qh >= -FEAS_TOL
        and qc >= -FEAS_TOL
        and beans_used <= sc.beans_available + FEAS_TOL
        and water_used <= sc.water_available + FEAS_TOL
    )

    results["gurobi"][name] = {
        "round": rnd,
        "Q_hot": qh,
        "Q_cold": qc,
        "objective": obj,
        "beans_used": beans_used,
        "water_used": water_used,
        "feasible": feasible,
        "status": sol.get("status"),
    }

    check(
        f"gurobi_feasibility_{name}",
        feasible,
        results["gurobi"][name],
    )

    check(
        f"gurobi_finite_{name}",
        all(math.isfinite(x) for x in [qh, qc, obj]),
        results["gurobi"][name],
    )

    print(
        f"{name:24s} "
        f"Qh={qh:12.6f} "
        f"Qc={qc:12.6f} "
        f"obj={obj:14.8f} "
        f"feasible={feasible}"
    )

# ----------------------------------------------------------------------
# E. RESOURCE RELAXATION MONOTONICITY
# ----------------------------------------------------------------------

print("\n[E] RESOURCE MONOTONICITY")

base = Scenario(
    lambda_total=80,
    p_hot=0.60,
    p_cold=0.40,
    revenue_hot=2.5,
    revenue_cold=2.2,
    cost_hot=0.30,
    cost_cold=0.25,
    beans_available=50,
    beans_hot=1.0,
    beans_cold=1.0,
    water_available=50,
    water_hot=1.0,
    water_cold=1.0,
)

relaxed = Scenario(
    lambda_total=80,
    p_hot=0.60,
    p_cold=0.40,
    revenue_hot=2.5,
    revenue_cold=2.2,
    cost_hot=0.30,
    cost_cold=0.25,
    beans_available=80,
    beans_hot=1.0,
    beans_cold=1.0,
    water_available=80,
    water_hot=1.0,
    water_cold=1.0,
)

tight_sol = solve_gurobi_round(base, 4, pwl_points=PWL_POINTS)
relaxed_sol = solve_gurobi_round(relaxed, 4, pwl_points=PWL_POINTS)

tight_obj = float(tight_sol["objective"])
relaxed_obj = float(relaxed_sol["objective"])

resource_ok = relaxed_obj + TOL >= tight_obj

check(
    "resource_relaxation_monotonicity",
    resource_ok,
    f"tight={tight_obj}, relaxed={relaxed_obj}",
)

print(
    f"tight={tight_obj:.10f} "
    f"relaxed={relaxed_obj:.10f} "
    f"PASS={resource_ok}"
)

# ----------------------------------------------------------------------
# F. COST MONOTONICITY OF OPTIMAL VALUE
# ----------------------------------------------------------------------

print("\n[F] OPTIMAL VALUE VS COST")

low_cost = Scenario(
    lambda_total=80,
    p_hot=0.60,
    p_cold=0.40,
    revenue_hot=2.5,
    revenue_cold=2.2,
    cost_hot=0.20,
    cost_cold=0.15,
    beans_available=80,
    beans_hot=1.0,
    beans_cold=1.0,
    water_available=80,
    water_hot=1.0,
    water_cold=1.0,
)

high_cost = Scenario(
    lambda_total=80,
    p_hot=0.60,
    p_cold=0.40,
    revenue_hot=2.5,
    revenue_cold=2.2,
    cost_hot=0.60,
    cost_cold=0.55,
    beans_available=80,
    beans_hot=1.0,
    beans_cold=1.0,
    water_available=80,
    water_hot=1.0,
    water_cold=1.0,
)

low_sol = solve_gurobi_round(low_cost, 4, pwl_points=PWL_POINTS)
high_sol = solve_gurobi_round(high_cost, 4, pwl_points=PWL_POINTS)

low_obj = float(low_sol["objective"])
high_obj = float(high_sol["objective"])

cost_ok = high_obj <= low_obj + TOL

check(
    "optimal_value_cost_monotonicity",
    cost_ok,
    f"low_cost={low_obj}, high_cost={high_obj}",
)

print(
    f"low_cost={low_obj:.10f} "
    f"high_cost={high_obj:.10f} "
    f"PASS={cost_ok}"
)

# ----------------------------------------------------------------------
# FINAL
# ----------------------------------------------------------------------

results["summary"] = {
    "tests_failed": len(results["failures"]),
    "status": "PASS" if not results["failures"] else "FAIL",
}

Path("r6_1_invariants.json").write_text(
    json.dumps(results, indent=2),
    encoding="utf-8",
)

print("\n========================================")
print("R6.1 STATUS:", results["summary"]["status"])
print("FAILURES:", len(results["failures"]))
print("ARTIFACT: r6_1_invariants.json")
print("========================================")

if results["failures"]:
    print(json.dumps(results["failures"], indent=2))
    raise SystemExit(1)

print("R6.1_INVARIANTS_OK")
