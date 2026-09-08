from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path

from gurobean.parity import default_parity_cases
from gurobean.model import solve_gurobi_round, solve_round_scipy


SEED = 20260908
CASE_COUNT = 32
POINTS = [1001, 5001, 10001, 20001, 40001]

OUT = Path("r5_pwl_calibration.json")


def finite(x):
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def err(a, b):
    if not finite(a) or not finite(b):
        return float("inf")
    return abs(float(a) - float(b))


print("=" * 78)
print("GUROBEAN ENGINE — R5 PWL CALIBRATION")
print("=" * 78)
print(f"seed       : {SEED}")
print(f"cases      : {CASE_COUNT}")
print(f"point sets : {POINTS}")
print()


cases = default_parity_cases(seed=SEED, count=CASE_COUNT)

print(f"Generated cases: {len(cases)}")

reference = {}
for i, case in enumerate(cases, 1):
    t0 = time.perf_counter()
    ref = solve_round_scipy(case.scenario, case.round_number)
    dt = time.perf_counter() - t0

    reference[case.label] = {
        "label": case.label,
        "round": case.round_number,
        "objective": float(ref["objective"]),
        "Q_hot": float(ref["Q_hot"]),
        "Q_cold": float(ref["Q_cold"]),
        "solve_seconds": dt,
    }

    print(
        f"[SCIPY {i:02d}/{len(cases)}] "
        f"{case.label:<28} R{case.round_number} "
        f"obj={ref['objective']:.10f}"
    )


results = []

for case_index, case in enumerate(cases, 1):
    ref = reference[case.label]

    print()
    print(f"CASE {case_index:02d}/{len(cases)} — {case.label} — R{case.round_number}")

    previous = None

    for points in POINTS:
        t0 = time.perf_counter()

        try:
            sol = solve_gurobi_round(
                case.scenario,
                case.round_number,
                pwl_points=points,
            )

            elapsed = time.perf_counter() - t0

            obj_error = err(sol["objective"], ref["objective"])
            qh_error = err(sol["Q_hot"], ref["Q_hot"])
            qc_error = err(sol["Q_cold"], ref["Q_cold"])

            if previous is None:
                delta_obj = None
                delta_qh = None
                delta_qc = None
            else:
                delta_obj = err(sol["objective"], previous["objective"])
                delta_qh = err(sol["Q_hot"], previous["Q_hot"])
                delta_qc = err(sol["Q_cold"], previous["Q_cold"])

            row = {
                "label": case.label,
                "round": case.round_number,
                "pwl_points": points,
                "objective": float(sol["objective"]),
                "Q_hot": float(sol["Q_hot"]),
                "Q_cold": float(sol["Q_cold"]),
                "objective_error_vs_scipy": obj_error,
                "Q_hot_error_vs_scipy": qh_error,
                "Q_cold_error_vs_scipy": qc_error,
                "delta_objective_vs_previous": delta_obj,
                "delta_Q_hot_vs_previous": delta_qh,
                "delta_Q_cold_vs_previous": delta_qc,
                "solve_seconds": elapsed,
            }

            results.append(row)

            print(
                f"  PWL={points:5d} "
                f"obj_err={obj_error:.9g} "
                f"qh_err={qh_error:.9g} "
                f"qc_err={qc_error:.9g} "
                f"time={elapsed:.3f}s"
            )

            previous = sol

        except Exception as exc:
            results.append({
                "label": case.label,
                "round": case.round_number,
                "pwl_points": points,
                "error": repr(exc),
            })
            print(f"  PWL={points:5d} ERROR: {exc}")


summary = {}

for points in POINTS:
    rows = [
        r for r in results
        if r.get("pwl_points") == points and "error" not in r
    ]

    if not rows:
        continue

    obj = [r["objective_error_vs_scipy"] for r in rows]
    qh = [r["Q_hot_error_vs_scipy"] for r in rows]
    qc = [r["Q_cold_error_vs_scipy"] for r in rows]

    summary[str(points)] = {
        "cases": len(rows),
        "max_objective_error": max(obj),
        "mean_objective_error": statistics.fmean(obj),
        "median_objective_error": statistics.median(obj),
        "max_Q_hot_error": max(qh),
        "mean_Q_hot_error": statistics.fmean(qh),
        "max_Q_cold_error": max(qc),
        "mean_Q_cold_error": statistics.fmean(qc),
        "max_solve_seconds": max(r["solve_seconds"] for r in rows),
        "mean_solve_seconds": statistics.fmean(
            r["solve_seconds"] for r in rows
        ),
    }


# Worst cases by objective error.
worst_objective = sorted(
    [r for r in results if "error" not in r],
    key=lambda r: r["objective_error_vs_scipy"],
    reverse=True,
)[:15]

# Explicit convergence diagnostics.
convergence = {}

for label in sorted({r["label"] for r in results}):
    rows = [
        r for r in results
        if r["label"] == label and "error" not in r
    ]
    rows.sort(key=lambda r: r["pwl_points"])

    convergence[label] = [
        {
            "pwl_points": r["pwl_points"],
            "objective_error": r["objective_error_vs_scipy"],
            "Q_hot_error": r["Q_hot_error_vs_scipy"],
            "Q_cold_error": r["Q_cold_error_vs_scipy"],
            "delta_objective": r["delta_objective_vs_previous"],
        }
        for r in rows
    ]


payload = {
    "schema": "gurobean.r5.pwl_calibration.v1",
    "seed": SEED,
    "case_count": CASE_COUNT,
    "points": POINTS,
    "summary": summary,
    "worst_objective_cases": worst_objective,
    "convergence": convergence,
    "reference": reference,
}

OUT.write_text(
    json.dumps(payload, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print()
print("=" * 78)
print("R5 CALIBRATION COMPLETE")
print("=" * 78)

for points in POINTS:
    s = summary.get(str(points))
    if not s:
        continue

    print(
        f"PWL {points:5d} | "
        f"max obj err={s['max_objective_error']:.9g} | "
        f"mean obj err={s['mean_objective_error']:.9g} | "
        f"max qh={s['max_Q_hot_error']:.9g} | "
        f"max qc={s['max_Q_cold_error']:.9g}"
    )

print()
print("TOP 15 OBJECTIVE ERRORS")
for r in worst_objective:
    print(
        f"{r['label']:<28} "
        f"R{r['round']} "
        f"PWL={r['pwl_points']:5d} "
        f"err={r['objective_error_vs_scipy']:.12g}"
    )

print()
print(f"Artifact: {OUT}")
