from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

import gurobean.model as gm
from gurobean.parity import default_parity_cases

SEED = 20260908
CASE_COUNT = 32
POINTS = [1001, 5001, 10001, 20001]
TARGETS = {"random_005_r2", "random_001_r2", "random_011_r4"}
OUT = Path("r5_adaptive_pwl_experiment.json")

print("=" * 78)
print("R5.5 — EXPERIMENTO DE MALLA PWL ADAPTATIVA")
print("=" * 78)
print(f"seed  : {SEED}")
print(f"cases : {CASE_COUNT}")
print(f"points: {POINTS}")
print()

cases = default_parity_cases(seed=SEED, count=CASE_COUNT)
selected = {case.label: case for case in cases if case.label in TARGETS}
if len(selected) != len(TARGETS):
    raise RuntimeError(f"No se encontraron todos los casos: {sorted(selected)}")

def adaptive_grid(start: float, stop: float, num: int, lam: float):
    start = float(start); stop = float(stop); num = max(2, int(num)); lam = float(lam)
    if stop <= start or not (start <= lam <= stop):
        return np.linspace(start, stop, num)
    frac = (lam - start) / (stop - start)
    left_n = max(2, int(round((num - 1) * frac)) + 1)
    right_n = max(2, num - left_n + 1)
    u_left = np.linspace(0.0, 1.0, left_n)
    u_right = np.linspace(0.0, 1.0, right_n)
    left = start + (lam - start) * (1.0 - (1.0 - u_left) ** 3)
    right = lam + (stop - lam) * (u_right ** 3)
    raw = np.sort(np.concatenate((left, right, np.asarray([start, lam, stop]))))
    scale = max(1.0, abs(stop - start), abs(lam))
    min_dx = max(1e-9 * scale, 1e-7)
    kept = [float(raw[0])]
    for x in raw[1:]:
        x = float(x)
        if x - kept[-1] >= min_dx:
            kept.append(x)
    if kept[-1] < stop:
        kept.append(float(stop))
    return np.asarray(kept, dtype=float)

def run_strategy(strategy: str):
    original_linspace = gm.np.linspace
    active_lambdas = []
    lambda_index = 0
    def patched_linspace(start, stop, num, *args, **kwargs):
        nonlocal lambda_index
        if strategy == "adaptive" and float(start) == 0.0 and float(stop) > 1e-5 and int(num) >= 100 and lambda_index < len(active_lambdas):
            lam = active_lambdas[lambda_index]
            lambda_index += 1
            return adaptive_grid(start, stop, num, lam)
        return original_linspace(start, stop, num, *args, **kwargs)
    gm.np.linspace = patched_linspace
    output = {}
    try:
        for label in sorted(selected):
            case = selected[label]
            reference = gm.solve_round_scipy(case.scenario, case.round_number)
            print(); print("-" * 78); print(f"{label} — R{case.round_number}")
            print(f"SCIPY obj={reference['objective']:.15f} qh={reference['Q_hot']:.15f} qc={reference['Q_cold']:.15f}"); print("-" * 78)
            rows = []
            for points in POINTS:
                active_lambdas.clear(); active_lambdas.append(float(case.scenario.lambda_hot))
                if case.round_number in (2, 4): active_lambdas.append(float(case.scenario.lambda_cold))
                lambda_index = 0
                t0 = time.perf_counter()
                sol = gm.solve_gurobi_round(case.scenario, case.round_number, pwl_points=points)
                elapsed = time.perf_counter() - t0
                row = {"points": points, "objective": float(sol["objective"]), "Q_hot": float(sol["Q_hot"]), "Q_cold": float(sol["Q_cold"]), "objective_error": abs(float(sol["objective"]) - float(reference["objective"])), "Q_hot_error": abs(float(sol["Q_hot"]) - float(reference["Q_hot"])), "Q_cold_error": abs(float(sol["Q_cold"]) - float(reference["Q_cold"])), "seconds": elapsed}
                rows.append(row)
                print(f"PWL={points:5d} objerr={row['objective_error']:.12g} qherr={row['Q_hot_error']:.12g} qcerr={row['Q_cold_error']:.12g} time={elapsed:.3f}s")
            output[label] = {"round": case.round_number, "reference": {"objective": float(reference["objective"]), "Q_hot": float(reference["Q_hot"]), "Q_cold": float(reference["Q_cold"])}, "results": rows}
    finally:
        gm.np.linspace = original_linspace
    return output

all_results = {}
for strategy in ("uniform", "adaptive"):
    print(); print("=" * 78); print(f"STRATEGY: {strategy.upper()}"); print("=" * 78)
    all_results[strategy] = run_strategy(strategy)

payload = {"schema": "gurobean.r5.adaptive_pwl_experiment.v2", "seed": SEED, "case_count": CASE_COUNT, "targets": sorted(TARGETS), "points": POINTS, "results": all_results}
OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print(); print("=" * 78); print("R5.5 COMPLETE"); print("=" * 78); print(f"Artifact: {OUT}"); print("=" * 78)
