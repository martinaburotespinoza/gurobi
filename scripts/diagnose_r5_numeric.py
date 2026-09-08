from __future__ import annotations

import json
import math
import time
from pathlib import Path

from gurobean.parity import default_parity_cases
from gurobean.model import solve_round_scipy, solve_gurobi_round


SEED = 20260908
CASES = default_parity_cases(seed=SEED, count=32)

TARGETS = [
    "random_005_r2",
    "random_001_r2",
    "random_011_r4",
]

POINTS = [5001, 10001, 20001, 40001, 80001]

# Diferentes configuraciones numéricas.
# Primero baseline; después iremos afinando según resultado.
CONFIGS = [
    ("baseline", {}),
    ("tight_feasibility", {
        "FeasibilityTol": 1e-8,
    }),
    ("tight_optimality", {
        "OptimalityTol": 1e-8,
    }),
    ("tight_both", {
        "FeasibilityTol": 1e-8,
        "OptimalityTol": 1e-8,
    }),
]


# La función pública actual no necesariamente expone parámetros
# de Gurobi. Detectamos primero su firma.
import inspect
print("=" * 78)
print("R5.2 — PWL / NUMERICAL TOLERANCE DIAGNOSTIC")
print("=" * 78)

print("\nsolve_gurobi_round signature:")
print(inspect.signature(solve_gurobi_round))


selected = {
    c.label: c
    for c in CASES
    if c.label in TARGETS
}

if len(selected) != len(TARGETS):
    raise RuntimeError(
        "No se encontraron todos los casos deterministas: "
        + repr(sorted(set(TARGETS) - set(selected)))
    )


# Inspección estática de la función para descubrir si ya acepta
# parámetros como FeasibilityTol, OptimalityTol, MIPGap, NumericFocus, etc.
source = inspect.getsource(solve_gurobi_round)

keywords = [
    "FeasibilityTol",
    "OptimalityTol",
    "MIPGap",
    "MIPGapAbs",
    "NumericFocus",
    "IntFeasTol",
    "ScaleFlag",
    "PWL",
    "addGenConstrPWL",
    "setPWLObj",
    "Model",
]

print("\nRelevant implementation markers:")
for key in keywords:
    print(f"  {key:20s}: {'YES' if key in source else 'NO'}")


# Guardamos evidencia de la implementación actual.
Path("r5_solve_gurobi_round_source.txt").write_text(
    source,
    encoding="utf-8",
)


results = {
    "schema": "gurobean.r5.2.numeric_diagnostic.v1",
    "seed": SEED,
    "targets": TARGETS,
    "points": POINTS,
    "configs": [name for name, _ in CONFIGS],
    "results": {},
}


for label in TARGETS:
    case = selected[label]

    scipy = solve_round_scipy(
        case.scenario,
        case.round_number,
    )

    print("\n" + "=" * 78)
    print(label, f"R{case.round_number}")
    print(
        f"SCIPY obj={scipy['objective']:.12f} "
        f"qh={scipy['Q_hot']:.12f} "
        f"qc={scipy['Q_cold']:.12f}"
    )
    print("-" * 78)

    case_result = {
        "round": case.round_number,
        "scipy": {
            "objective": float(scipy["objective"]),
            "Q_hot": float(scipy["Q_hot"]),
            "Q_cold": float(scipy["Q_cold"]),
        },
        "runs": [],
    }

    for points in POINTS:
        t0 = time.perf_counter()

        try:
            sol = solve_gurobi_round(
                case.scenario,
                case.round_number,
                pwl_points=points,
            )

            elapsed = time.perf_counter() - t0

            row = {
                "config": "baseline",
                "pwl_points": points,
                "objective": float(sol["objective"]),
                "Q_hot": float(sol["Q_hot"]),
                "Q_cold": float(sol["Q_cold"]),
                "objective_error": abs(
                    float(sol["objective"]) -
                    float(scipy["objective"])
                ),
                "Q_hot_error": abs(
                    float(sol["Q_hot"]) -
                    float(scipy["Q_hot"])
                ),
                "Q_cold_error": abs(
                    float(sol["Q_cold"]) -
                    float(scipy["Q_cold"])
                ),
                "seconds": elapsed,
            }

            case_result["runs"].append(row)

            print(
                f"PWL={points:6d} "
                f"objerr={row['objective_error']:.9g} "
                f"qherr={row['Q_hot_error']:.9g} "
                f"qcerr={row['Q_cold_error']:.9g} "
                f"time={elapsed:.2f}s"
            )

        except Exception as exc:
            print(
                f"PWL={points:6d} ERROR: {exc}"
            )

            case_result["runs"].append({
                "config": "baseline",
                "pwl_points": points,
                "error": repr(exc),
            })

    results["results"][label] = case_result


Path("r5_numeric_diagnostic.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("\n" + "=" * 78)
print("R5.2 DIAGNOSTIC COMPLETE")
print("=" * 78)
print("Artifacts:")
print("  r5_numeric_diagnostic.json")
print("  r5_solve_gurobi_round_source.txt")
