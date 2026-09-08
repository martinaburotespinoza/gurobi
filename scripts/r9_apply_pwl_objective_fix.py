"""Apply the R9 PWL-objective stability fix to a local checkout.

The old Gurobi adapter represented each profit curve with an auxiliary y
variable plus addGenConstrPWL(q, y, ...).  For the R1-R4 separable concave
objective this is unnecessarily fragile at numerical boundaries.  This
script replaces that adapter with Gurobi's native setPWLObj representation,
while retaining the same breakpoints, resource constraints, and public
return schema.

The script is intentionally idempotent: it refuses to patch a file that no
longer contains the expected old adapter and writes a .bak copy first.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

NEW_SOLVER = r'''def solve_gurobi_round(sc: Scenario, round_number: int, pwl_points: int = 20001) -> dict:
    """Solve R1-R4 with native Gurobi PWL objectives.

    The exact continuous objective is concave and separable.  Native PWL
    objectives avoid auxiliary profit variables and their general PWL
    constraints, reducing numerical sensitivity while preserving the same
    mathematical piecewise-linear approximation.
    """
    if round_number not in (1, 2, 3, 4):
        raise ValueError("Gurobi adapter currently covers rounds 1-4 only")
    try:
        import gurobipy as gp
    except ImportError as exc:
        raise RuntimeError("gurobipy is not installed") from exc

    include_cold = round_number in (2, 4)
    include_cost = round_number in (3, 4)
    hot_hi, cold_hi = _round_bounds(sc, include_cold, include_cost)
    points = max(2, int(pwl_points))

    m = gp.Model(f"gurobean_r{round_number}")
    m.Params.OutputFlag = 0
    # Tight but still practical tolerances for the certification adapter.
    m.Params.FeasibilityTol = 1e-9
    m.Params.OptimalityTol = 1e-9
    m.Params.NumericFocus = 2

    qh = m.addVar(lb=0.0, ub=hot_hi, name="Q_hot")
    qc = m.addVar(lb=0.0, ub=(cold_hi if include_cold else 0.0), name="Q_cold")

    if np.isfinite(sc.beans_available):
        m.addConstr(sc.beans_hot * qh + sc.beans_cold * qc <= sc.beans_available, name="beans")
    if np.isfinite(sc.water_available):
        m.addConstr(sc.water_hot * qh + sc.water_cold * qc <= sc.water_available, name="water")

    resource_vertices = _resource_vertices(sc, include_cold, hot_hi, cold_hi)

    def set_profit_pwl(var, hi, lam, revenue, cost, salvage, critical_points=None, name="profit"):
        hi = float(hi)
        if hi <= 1e-12:
            return
        if hi < 1e-5:
            # Keep the normalized representation for tiny domains to avoid
            # poorly scaled x coordinates in Gurobi's PWL objective.
            t = m.addVar(lb=0.0, ub=1.0, name=f"{name}_normalized")
            m.addConstr(var == hi * t, name=f"{name}_scale")
            xs = np.linspace(0.0, 1.0, points)
            ys = [expected_newsvendor_profit(float(hi * x), lam, revenue, cost, salvage) for x in xs]
            m.setPWLObj(t, xs.tolist(), ys)
            return

        base_xs = np.linspace(0.0, hi, points)
        extra = [
            float(x) for x in (critical_points or [])
            if -1e-12 <= float(x) <= hi + 1e-12
        ]
        xs = np.asarray(
            sorted({round(float(x), 15) for x in np.concatenate((base_xs, np.asarray(extra, dtype=float)))
                    if -1e-12 <= float(x) <= hi + 1e-12}),
            dtype=float,
        )
        xs = np.clip(xs, 0.0, hi)
        if len(xs) >= 2:
            scale = max(1.0, abs(hi))
            min_dx = max(1.1e-6, 1e-8 * scale)
            filtered = [float(xs[0])]
            for x in xs[1:]:
                x = float(x)
                if x - filtered[-1] >= min_dx:
                    filtered.append(x)
            if filtered[-1] < hi:
                if hi - filtered[-1] >= min_dx:
                    filtered.append(hi)
                elif len(filtered) >= 2:
                    filtered[-1] = hi
            xs = np.asarray(filtered, dtype=float)
        if len(xs) < 2 or np.max(np.diff(xs)) <= 0.0:
            xs = np.asarray([0.0, hi], dtype=float)
        ys = [expected_newsvendor_profit(float(x), lam, revenue, cost, salvage) for x in xs]
        m.setPWLObj(var, xs.tolist(), ys)

    m.setObjective(0.0, gp.GRB.MAXIMIZE)
    set_profit_pwl(
        qh, hot_hi, sc.lambda_hot, sc.revenue_hot,
        sc.cost_hot if include_cost else 0.0, sc.salvage_hot,
        [v[0] for v in resource_vertices], "profit_hot",
    )
    if include_cold:
        set_profit_pwl(
            qc, cold_hi, sc.lambda_cold, sc.revenue_cold,
            sc.cost_cold if include_cost else 0.0, sc.salvage_cold,
            [v[1] for v in resource_vertices], "profit_cold",
        )

    m.optimize()
    if m.Status != gp.GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi did not return OPTIMAL; status={m.Status}")

    qh_value = float(qh.X)
    qc_value = float(qc.X) if include_cold else 0.0
    exact_objective = _round_objective(sc, include_cold, include_cost, qh_value, qc_value)
    return {
        "Q_hot": qh_value,
        "Q_cold": qc_value,
        "objective": float(m.ObjVal),
        "exact_objective": float(exact_objective),
        "method": "gurobi_native_pwl_objective_validation",
        "status": int(m.Status),
        "pwl_points": points,
    }
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="gurobean/model.py")
    args = parser.parse_args()
    path = Path(args.file)
    text = path.read_text(encoding="utf-8")
    start = text.find("def solve_gurobi_round(")
    end = text.find("\ndef solve_round(", start)
    if start < 0 or end < 0:
        raise SystemExit("Expected solve_gurobi_round/solve_round boundaries were not found; refusing to patch")
    old = text[start:end]
    if "addGenConstrPWL" not in old:
        raise SystemExit("The old PWL adapter is not present; refusing to patch")
    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_text(text, encoding="utf-8")
    patched = text[:start] + NEW_SOLVER.rstrip() + text[end:]
    path.write_text(patched, encoding="utf-8")
    print(f"Patched: {path}")
    print(f"Backup : {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
