from pathlib import Path
import inspect
import gurobean.model as gm

print("=" * 78)
print("R5.3 — AUDITORÍA QUIRÚRGICA DE LA FORMULACIÓN PWL")
print("=" * 78)

src = inspect.getsource(gm.solve_gurobi_round)

lines = src.splitlines()

markers = [
    "addGenConstrPWL",
    "pwl_points",
    "linspace",
    "np.linspace",
    "lb=",
    "ub=",
    "setParam",
    "FeasibilityTol",
    "OptimalityTol",
    "NumericFocus",
    "ScaleFlag",
    "IntFeasTol",
    "MIPGap",
    "MIPGapAbs",
    "Model(",
    "optimize",
]

print("\n--- FRAGMENTOS RELEVANTES ---")

for i, line in enumerate(lines):
    if any(m in line for m in markers):
        start = max(0, i - 6)
        end = min(len(lines), i + 10)

        print(f"\n{'-' * 78}")
        print(f"LINEAS {start + 1}..{end}")
        print(f"{'-' * 78}")

        for j in range(start, end):
            print(f"{j + 1:04d}: {lines[j]}")

print("\n" + "=" * 78)
print("MODELO COMPLETO DE solve_gurobi_round")
print("=" * 78)
print(src)

Path("r5_r3_solve_gurobi_round_full.txt").write_text(
    src,
    encoding="utf-8"
)

print("\nArtefacto:")
print("  r5_r3_solve_gurobi_round_full.txt")
print("=" * 78)
