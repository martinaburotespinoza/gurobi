"""Apply the R9 native-PWL objective fix to a local checkout.

This replaces the auxiliary-y/addGenConstrPWL adapter with Gurobi's native
setPWLObj representation. Zero-width economic domains are represented by an
explicit constant objective so boundary cases retain the exact Q=0 profit.
"""
from __future__ import annotations

import argparse
from pathlib import Path

NEW_SOLVER = r'''def solve_gurobi_round(sc: Scenario, round_number: int, pwl_points: int = 20001) -> dict:
    """Solve R1-R4 with native Gurobi PWL objectives."""
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
    objective_constant = 0.0

    def set_profit_pwl(var, hi, lam, revenue, cost, salvage, critical_points=None, name="profit"):
        nonlocal objective_constant
        hi = float(hi)
        f0 = expected_newsvendor_profit(0.0, lam, revenue, cost, salvage)
        if hi <= 1e-12:
            # Gurobi has no PWL variable to attach on a fixed zero domain;
            # preserve the exact constant contribution explicitly.
            objective_constant += float(f0)
            return
        if hi < 1e-5:
            t = m.addVar(lb=0.0, ub=1.0, name=f"{name}_normalized")
            m.addConstr(var == hi * t, name=f"{name}_scale")
            xs = np.linspace(0.0, 1.0, points)
            ys = [expected_newsvendor_profit(float(hi * x), lam, revenue, cost, salvage) for x in xs]
            m.setPWLObj(t, xs.tolist(), ys)
            return

        base_xs = np.linspace(0.0, hi, points)
        extra = [float(x) for x in (critical_points or []) if -1e-12 <= float(x) <= hi + 1e-12]
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

    # Establish the objective sense before adding native PWL pieces.
    m.setObjective(objective_constant, gp.GRB.MAXIMIZE)
    set_profit_pwl(qh, hot_hi, sc.lambda_hot, sc.revenue_hot,
                   sc.cost_hot if include_cost else 0.0, sc.salvage_hot,
                   [v[0] for v in resource_vertices], "profit_hot")
    if include_cold:
        set_profit_pwl(qc, cold_hi, sc.lambda_cold, sc.revenue_cold,
                       sc.cost_cold if include_cost else 0.0, sc.salvage_cold,
                       [v[1] for v in resource_vertices], "profit_cold")

    # Add any constants discovered after the initial objective construction.
    if objective_constant != 0.0:
        # Re-apply only the constant through the objective expression without
        # disturbing the native PWL pieces: Gurobi's PWL terms are additive.
        m.ObjCon = float(objective_constant)

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
    path.write_text(text[:start] + NEW_SOLVER.rstrip() + text[end:], encoding="utf-8")
    print(f"Patched: {path}")
    print(f"Backup : {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
