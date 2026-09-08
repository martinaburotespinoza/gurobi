from __future__ import annotations

try:
    import gurobipy as gp
except ImportError:
    print("GUROBI_PYTHON=NOT_INSTALLED")
    raise SystemExit(2)

print("GUROBI_PYTHON=", gp.gurobi.version())
env = None
try:
    env = gp.Env(empty=True)
    env.setParam("OutputFlag", 0)
    env.start()
except Exception as exc:
    print("GUROBI_LICENSE=UNAVAILABLE")
    print(type(exc).__name__ + ": " + str(exc))
    raise SystemExit(3)
finally:
    if env is not None:
        try:
            env.dispose()
        except Exception:
            pass
print("GUROBI_LICENSE=OK")
