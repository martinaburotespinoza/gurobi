import json
import math
from pathlib import Path

from gurobean.model import Scenario, solve_gurobi_round


EXPECTED_UNBOUNDED = {
    "zero_cost",
    "extreme_revenue",
}

CASES = [
    (
        "zero_lambda",
        Scenario(lambda_total=0.0),
    ),
    (
        "tiny_lambda",
        Scenario(
            lambda_total=1e-6,
            p_hot=0.5,
            p_cold=0.5,
            revenue_hot=3.0,
            revenue_cold=2.0,
            cost_hot=0.5,
            cost_cold=0.25,
        ),
    ),
    (
        "huge_lambda",
        Scenario(
            lambda_total=1e6,
            p_hot=0.6,
            p_cold=0.4,
            revenue_hot=3.0,
            revenue_cold=2.5,
            cost_hot=0.8,
            cost_cold=0.6,
            salvage_hot=0.1,
            salvage_cold=0.1,
        ),
    ),
    (
        "zero_revenue",
        Scenario(
            lambda_total=100.0,
            p_hot=0.5,
            p_cold=0.5,
            revenue_hot=0.0,
            revenue_cold=0.0,
            cost_hot=1.0,
            cost_cold=1.0,
        ),
    ),
    (
        "zero_cost",
        Scenario(
            lambda_total=100.0,
            p_hot=0.5,
            p_cold=0.5,
            revenue_hot=3.0,
            revenue_cold=2.0,
            cost_hot=0.0,
            cost_cold=0.0,
        ),
    ),
    (
        "zero_salvage",
        Scenario(
            lambda_total=100.0,
            p_hot=0.7,
            p_cold=0.3,
            revenue_hot=3.0,
            revenue_cold=2.0,
            cost_hot=0.5,
            cost_cold=0.4,
            salvage_hot=0.0,
            salvage_cold=0.0,
        ),
    ),
    (
        "salvage_equals_revenue",
        Scenario(
            lambda_total=100.0,
            p_hot=0.5,
            p_cold=0.5,
            revenue_hot=2.0,
            revenue_cold=2.0,
            cost_hot=1.0,
            cost_cold=1.0,
            salvage_hot=2.0,
            salvage_cold=2.0,
        ),
    ),
    (
        "extreme_cost",
        Scenario(
            lambda_total=100.0,
            p_hot=0.5,
            p_cold=0.5,
            revenue_hot=3.0,
            revenue_cold=3.0,
            cost_hot=1e6,
            cost_cold=1e6,
        ),
    ),
    (
        "extreme_revenue",
        Scenario(
            lambda_total=100.0,
            p_hot=0.5,
            p_cold=0.5,
            revenue_hot=1e6,
            revenue_cold=1e6,
            cost_hot=0.0,
            cost_cold=0.0,
        ),
    ),
    (
        "tight_resources",
        Scenario(
            lambda_total=100.0,
            p_hot=0.5,
            p_cold=0.5,
            revenue_hot=3.0,
            revenue_cold=2.5,
            cost_hot=0.5,
            cost_cold=0.4,
            beans_available=1.0,
            water_available=1.0,
            beans_hot=1.0,
            beans_cold=1.0,
            water_hot=1.0,
            water_cold=1.0,
        ),
    ),
    (
        "huge_resources",
        Scenario(
            lambda_total=100.0,
            p_hot=0.5,
            p_cold=0.5,
            revenue_hot=3.0,
            revenue_cold=2.5,
            cost_hot=0.5,
            cost_cold=0.4,
            beans_available=1e9,
            water_available=1e9,
            beans_hot=1.0,
            beans_cold=1.0,
            water_hot=1.0,
            water_cold=1.0,
        ),
    ),
    (
        "highly_asymmetric",
        Scenario(
            lambda_total=1000.0,
            p_hot=0.999999,
            p_cold=0.000001,
            revenue_hot=100.0,
            revenue_cold=0.01,
            cost_hot=0.001,
            cost_cold=100.0,
            salvage_hot=0.0,
            salvage_cold=0.0,
        ),
    ),
]


def finite(x):
    return math.isfinite(float(x))


results = []
failures = []

for name, sc in CASES:
    row = {"name": name}

    try:
        sol = solve_gurobi_round(sc, 4, pwl_points=5001)

        qh = float(sol["Q_hot"])
        qc = float(sol["Q_cold"])
        obj = float(sol["objective"])

        row.update({
            "status": "ok",
            "Q_hot": qh,
            "Q_cold": qc,
            "objective": obj,
            "finite": finite(qh) and finite(qc) and finite(obj),
            "nonnegative": qh >= -1e-7 and qc >= -1e-7,
        })

        ok = row["finite"] and row["nonnegative"]

        if not ok:
            failures.append({
                "name": name,
                "reason": "nonfinite_or_negative",
                "row": row,
            })

    except Exception as exc:
        error_text = str(exc)

        if (
            name in EXPECTED_UNBOUNDED
            and "unbounded" in error_text.lower()
        ):
            row.update({
                "status": "expected_unbounded",
                "error": repr(exc),
                "expected": True,
            })
        else:
            row.update({
                "status": "exception",
                "error": repr(exc),
                "expected": False,
            })
            failures.append({
                "name": name,
                "reason": "unexpected_exception",
                "error": repr(exc),
            })

    results.append(row)

print()
for r in results:
    print(
        f'{r["name"]:24s} '
        f'status={r["status"]:10s} '
        f'Qh={r.get("Q_hot", float("nan")):14.6f} '
        f'Qc={r.get("Q_cold", float("nan")):14.6f} '
        f'obj={r.get("objective", float("nan")):16.8f}'
    )

artifact = {
    "round": "R6.4",
    "cases": results,
    "failures": failures,
    "case_count": len(CASES),
    "failure_count": len(failures),
}

Path("r6_4_pathological.json").write_text(
    json.dumps(artifact, indent=2),
    encoding="utf-8",
)

print()
print("=" * 40)
print(f"R6.4 STATUS: {'PASS' if not failures else 'FAIL'}")
print(f"CASES: {len(CASES)}")
print(f"FAILURES: {len(failures)}")
print("ARTIFACT: r6_4_pathological.json")
print("=" * 40)

if failures:
    raise SystemExit(1)

print("R6.4_PATHOLOGICAL_OK")
