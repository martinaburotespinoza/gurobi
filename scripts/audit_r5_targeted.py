from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path

from gurobean.parity import default_parity_cases
from gurobean.model import solve_gurobi_round, solve_round_scipy

SEED = 20260908
CASES = 32
TARGETS = {
    "random_001_r2", "random_005_r2", "random_009_r2", "random_011_r4", "random_017_r2",
    "random_021_r2", "random_025_r2", "random_029_r2", "random_003_r4", "random_019_r4",
}
POINTS = [1001, 5001, 10001, 20001, 40001, 80001]
cases = default_parity_cases(seed=SEED, count=CASES)
selected = [c for c in cases if c.label in TARGETS]

print("=" * 78)
print("GUROBEAN R5.1 — TARGETED NUMERICAL AUDIT")
print("=" * 78)
print(f"selected cases: {len(selected)}")
print(f"points        : {POINTS}")
print()
if len(selected) != len(TARGETS):
    missing = sorted(TARGETS - {c.label for c in selected})
    raise RuntimeError(f"Missing deterministic cases: {missing}")

def dump_scenario(sc):
    data = {}
    for name in ("lambda_total", "p_hot", "p_cold", "revenue_hot", "revenue_cold", "cost_hot", "cost_cold", "salvage_hot", "salvage_cold", "beans_available", "water_available", "beans_hot", "beans_cold", "water_hot", "water_cold"):
        value = getattr(sc, name)
        if isinstance(value, float) and not math.isfinite(value):
            value = str(value)
        data[name] = value
    return data

audit = {"schema": "gurobean.r5.1.targeted_audit.v1", "seed": SEED, "cases": CASES, "points": POINTS, "targets": {}}

for case in selected:
    print("=" * 78)
    print(case.label, f"R{case.round_number}")
    print("-" * 78)
    scipy = solve_round_scipy(case.scenario, case.round_number)
    print(f"SCIPY  obj={scipy['objective']:.12f} qh={scipy['Q_hot']:.12f} qc={scipy['Q_cold']:.12f}")
    target = {"label": case.label, "round": case.round_number, "scenario": dump_scenario(case.scenario), "scipy": {"objective": float(scipy["objective"]), "Q_hot": float(scipy["Q_hot"]), "Q_cold": float(scipy["Q_cold"])}, "runs": []}
    for points in POINTS:
        t0 = time.perf_counter()
        try:
            sol = solve_gurobi_round(case.scenario, case.round_number, pwl_points=points)
            elapsed = time.perf_counter() - t0
            row = {"pwl_points": points, "objective": float(sol["objective"]), "Q_hot": float(sol["Q_hot"]), "Q_cold": float(sol["Q_cold"]), "objective_error": abs(float(sol["objective"]) - float(scipy["objective"])), "Q_hot_error": abs(float(sol["Q_hot"]) - float(scipy["Q_hot"])), "Q_cold_error": abs(float(sol["Q_cold"]) - float(scipy["Q_cold"])), "solve_seconds": elapsed}
            target["runs"].append(row)
            print(f"PWL={points:6d} obj={row['objective']:.12f} err={row['objective_error']:.9g} qh={row['Q_hot']:.9f} qc={row['Q_cold']:.9f} time={elapsed:.3f}s")
        except Exception as exc:
            target["runs"].append({"pwl_points": points, "error": repr(exc)})
            print(f"PWL={points:6d} ERROR {exc}")
    repeat_points = 40001
    repeats = []
    print()
    print(f"REPEAT TEST PWL={repeat_points}")
    for i in range(3):
        t0 = time.perf_counter()
        try:
            sol = solve_gurobi_round(case.scenario, case.round_number, pwl_points=repeat_points)
            elapsed = time.perf_counter() - t0
            repeats.append({"objective": float(sol["objective"]), "Q_hot": float(sol["Q_hot"]), "Q_cold": float(sol["Q_cold"]), "solve_seconds": elapsed})
            print(f"repeat {i + 1}: obj={sol['objective']:.12f} qh={sol['Q_hot']:.9f} qc={sol['Q_cold']:.9f} time={elapsed:.3f}s")
        except Exception as exc:
            repeats.append({"error": repr(exc)})
            print(f"repeat {i + 1}: ERROR {exc}")
    target["repeat_40001"] = repeats
    valid = [x for x in repeats if "error" not in x]
    if len(valid) >= 2:
        target["repeat_spread"] = {"objective": max(x["objective"] for x in valid) - min(x["objective"] for x in valid), "Q_hot": max(x["Q_hot"] for x in valid) - min(x["Q_hot"] for x in valid), "Q_cold": max(x["Q_cold"] for x in valid) - min(x["Q_cold"] for x in valid)}
        print(f"spread: obj={target['repeat_spread']['objective']:.12g} qh={target['repeat_spread']['Q_hot']:.12g} qc={target['repeat_spread']['Q_cold']:.12g}")
    audit["targets"][case.label] = target

Path("r5_targeted_audit.json").write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
print("\n" + "=" * 78)
print("R5.1 AUDIT COMPLETE")
print("=" * 78)
print("Artifact: r5_targeted_audit.json")
