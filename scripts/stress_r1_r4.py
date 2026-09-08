from __future__ import annotations

import json
import warnings
from pathlib import Path

from gurobean.model import Scenario
from gurobean.parity import ParityCase, default_parity_cases, run_parity_suite

warnings.filterwarnings(
    "ignore",
    message="Values in x were outside bounds*",
)

BATCHES = 8
CASES_PER_BATCH = 30
PWL_POINTS = 20001

all_results = []
batch_summaries = []

for batch in range(BATCHES):
    seed = 20260907 + batch * 1000
    cases = default_parity_cases(
        seed=seed,
        count=CASES_PER_BATCH,
    )

    results = run_parity_suite(
        cases,
        pwl_points=PWL_POINTS,
        objective_tolerance=2e-3,
        quantity_tolerance=2e-2,
    )

    all_results.extend(results)

    passed = sum(r.passed for r in results)
    failed = sum(not r.passed for r in results)

    batch_summaries.append({
        "batch": batch + 1,
        "seed": seed,
        "cases": len(results),
        "passed": passed,
        "failed": failed,
        "max_objective_error": max(
            (r.objective_abs_error or 0.0) for r in results
        ),
    })

print("=== STRESS RANDOM R1-R4 ===")

total = len(all_results)
passed = sum(r.passed for r in all_results)
failed = total - passed

print("CASES:", total)
print("PASSED:", passed)
print("FAILED:", failed)
print(
    "MAX_OBJECTIVE_ERROR:",
    max((r.objective_abs_error or 0.0) for r in all_results),
)
print(
    "MAX_QHOT_ERROR:",
    max((r.q_hot_abs_error or 0.0) for r in all_results),
)
print(
    "MAX_QCOLD_ERROR:",
    max((r.q_cold_abs_error or 0.0) for r in all_results),
)

print("\nBATCHES:")
for item in batch_summaries:
    print(item)

extreme_cases = [
    ParityCase(
        1,
        Scenario(
            lambda_total=0.0,
            p_hot=1.0,
            revenue_hot=3.0,
            beans_available=1.0,
            water_available=1.0,
            beans_hot=1.0,
            water_hot=1.0,
        ),
        "extreme_r1_zero_demand",
    ),
    ParityCase(
        1,
        Scenario(
            lambda_total=80.0,
            p_hot=1.0,
            revenue_hot=6.0,
            beans_available=5.0,
            water_available=200.0,
            beans_hot=1.0,
            water_hot=1.0,
        ),
        "extreme_r1_bean_bottleneck",
    ),
    ParityCase(
        2,
        Scenario(
            lambda_total=60.0,
            p_hot=0.99,
            p_cold=0.01,
            revenue_hot=5.0,
            revenue_cold=5.0,
            beans_available=40.0,
            water_available=40.0,
            beans_hot=1.0,
            beans_cold=1.0,
            water_hot=1.0,
            water_cold=1.0,
        ),
        "extreme_r2_almost_all_hot",
    ),
    ParityCase(
        2,
        Scenario(
            lambda_total=30.0,
            p_hot=0.50,
            p_cold=0.50,
            revenue_hot=4.0,
            revenue_cold=5.0,
            beans_available=12.0,
            water_available=100.0,
            beans_hot=1.0,
            beans_cold=2.0,
            water_hot=1.0,
            water_cold=1.0,
        ),
        "extreme_r2_shared_bean_bottleneck",
    ),
    ParityCase(
        3,
        Scenario(
            lambda_total=50.0,
            p_hot=1.0,
            revenue_hot=3.0,
            cost_hot=2.999,
            beans_available=100.0,
            water_available=100.0,
            beans_hot=1.0,
            water_hot=1.0,
        ),
        "extreme_r3_margin_near_zero",
    ),
    ParityCase(
        4,
        Scenario(
            lambda_total=50.0,
            p_hot=0.50,
            p_cold=0.50,
            revenue_hot=6.0,
            revenue_cold=5.0,
            cost_hot=1.0,
            cost_cold=1.5,
            beans_available=20.0,
            water_available=15.0,
            beans_hot=1.0,
            beans_cold=2.0,
            water_hot=2.0,
            water_cold=1.0,
        ),
        "extreme_r4_dual_resource_bottleneck",
    ),
]

print("\n=== EXTREME CASES ===")

extreme_results = run_parity_suite(
    extreme_cases,
    pwl_points=PWL_POINTS,
    objective_tolerance=2e-3,
    quantity_tolerance=2e-2,
)

for r in extreme_results:
    print(
        r.label,
        "|",
        r.status,
        "| objective_error=",
        r.objective_abs_error,
        "| q_hot_error=",
        r.q_hot_abs_error,
        "| q_cold_error=",
        r.q_cold_abs_error,
    )

extreme_failed = sum(not r.passed for r in extreme_results)

print("\n=== FINAL STRESS RESULT ===")
print("RANDOM_CASES:", total)
print("RANDOM_PASSED:", passed)
print("RANDOM_FAILED:", failed)
print("EXTREME_CASES:", len(extreme_results))
print("EXTREME_FAILED:", extreme_failed)

summary = {
    "random_cases": total,
    "random_passed": passed,
    "random_failed": failed,
    "extreme_cases": len(extreme_results),
    "extreme_failed": extreme_failed,
    "pwl_points": PWL_POINTS,
    "batch_summaries": batch_summaries,
}

Path("stress_r1_r4_summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8",
)

if failed or extreme_failed:
    raise SystemExit(1)

print("\nSTRESS_TEST_OK")
