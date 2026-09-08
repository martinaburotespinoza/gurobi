import inspect
from pathlib import Path
import gurobean.model as gm

print("=" * 78)
print("R5.4 — AUDITORÍA DE LA FUNCIÓN ANALÍTICA")
print("=" * 78)

names = [
    "expected_newsvendor_profit",
    "_round_bounds",
    "_resource_vertices",
]

for name in names:
    obj = getattr(gm, name, None)

    print("\n" + "-" * 78)
    print(name)
    print("-" * 78)

    if obj is None:
        print("NO ENCONTRADA")
        continue

    try:
        src = inspect.getsource(obj)
        print(src)
    except Exception as exc:
        print("ERROR:", exc)

print("\n" + "=" * 78)
print("CONSTANTES / IMPORTS RELACIONADOS")
print("=" * 78)

src = inspect.getsource(gm)

for i, line in enumerate(src.splitlines(), 1):
    if any(x in line.lower() for x in [
        "scipy",
        "norm.",
        "normcdf",
        "expected_newsvendor",
        "salvage",
        "lambda",
        "revenue",
        "cost",
    ]):
        print(f"{i:04d}: {line}")

Path("r5_analytic_audit.txt").write_text(
    src,
    encoding="utf-8"
)

print("\nArtefacto generado:")
print("  r5_analytic_audit.txt")
print("=" * 78)
