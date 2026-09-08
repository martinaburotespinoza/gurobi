from __future__ import annotations

"""Robust Gurobi adapter for R1-R4.

The legacy adapter used Model.setPWLObj().  This backend represents every
piecewise-linear profit function explicitly with addGenConstrPWL() and an
auxiliary value variable, then maximizes the sum of those value variables.
This removes ambiguity around native PWL objective handling while preserving
the same mathematical PWL approximation and exact post-solve audit.
"""

import math

import numpy as np

from . import model as _model


PWL_POINTS_DEFAULT = 20001


def _economic_anchor(lam: float, revenue: float, cost: float, salvage: float, hi: float) -> float:
    """Return the exact unconstrained Newsvendor stationary point when valid."""
    q = _model._economic_unconstrained_q(
        float(lam), float(revenue), float(cost), float(salvage)
    )
    if not math.isfinite(q):
        return float(hi)
    return min(max(float(q), 0.0), float(hi))


def solve_gurobi_round(sc, round_number: int, pwl_points: int = PWL_POINTS_DEFAULT) -> dict:
    if round_number not in (1, 2, 3, 4):
        raise ValueError("Gurobi adapter currently covers rounds 1-4 only")
    try:
        import gurobipy as gp
    except ImportError as exc:
        raise RuntimeError("gurobipy is not installed") from exc

    include_cold = round_number in (2, 4)
    include_cost = round_number in (3, 4)
    hot_hi, cold_hi = _model._round_bounds(sc, include_cold, include_cost)
    points = max(2, int(pwl_points))

    m = gp.Model(f"gurobean_r{round_number}")
    m.Params.OutputFlag = 0
    m.Params.FeasibilityTol = 1e-9
    m.Params.OptimalityTol = 1e-9
    m.Params.NumericFocus = 2
    m.Params.MIPGap = 0.0
    m.Params.MIPGapAbs = 1e-9
    m.ModelSense = gp.GRB.MAXIMIZE

    qh = m.addVar(lb=0.0, ub=hot_hi, name="Q_hot")
    qc = m.addVar(lb=0.0, ub=cold_hi if include_cold else 0.0, name="Q_cold")

    if np.isfinite(sc.beans_available):
        m.addConstr(
            sc.beans_hot * qh + sc.beans_cold * qc <= sc.beans_available,
            name="beans",
        )
    if np.isfinite(sc.water_available):
        m.addConstr(
            sc.water_hot * qh + sc.water_cold * qc <= sc.water_available,
            name="water",
        )

    vertices = _model._resource_vertices(sc, include_cold, hot_hi, cold_hi)

    def add_profit(var, hi, lam, revenue, cost, salvage, critical_points, name):
        hi = float(hi)
        if hi <= 1e-12:
            return None

        # The exact economic stationary point is an optimizer whenever the
        # corresponding resource constraints are inactive.  Anchoring it in
        # the PWL mesh prevents the solver from being forced to a neighboring
        # breakpoint merely because the global mesh spacing is finite.
        anchors = list(critical_points or [])
        anchors.append(_economic_anchor(lam, revenue, cost, salvage, hi))

        xs = _model._adaptive_pwl_points(
            hi, lam, revenue, salvage, anchors, points
        )
        ys = [
            _model.expected_newsvendor_profit(
                float(x), lam, revenue, cost, salvage
            )
            for x in xs
        ]
        y = m.addVar(lb=-gp.GRB.INFINITY, name=f"{name}_value")
        m.addGenConstrPWL(var, y, xs, ys, name=f"{name}_pwl")
        return y

    yh = add_profit(
        qh,
        hot_hi,
        sc.lambda_hot,
        sc.revenue_hot,
        sc.cost_hot if include_cost else 0.0,
        sc.salvage_hot,
        [v[0] for v in vertices],
        "profit_hot",
    )
    yc = None
    if include_cold:
        yc = add_profit(
            qc,
            cold_hi,
            sc.lambda_cold,
            sc.revenue_cold,
            sc.cost_cold if include_cost else 0.0,
            sc.salvage_cold,
            [v[1] for v in vertices],
            "profit_cold",
        )

    objective = gp.LinExpr()
    if yh is not None:
        objective += yh
    if yc is not None:
        objective += yc
    m.setObjective(objective, gp.GRB.MAXIMIZE)
    m.optimize()

    if m.Status != gp.GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi did not return OPTIMAL; status={m.Status}")

    qh_value = float(qh.X)
    qc_value = float(qc.X) if include_cold else 0.0
    exact_objective = _model._round_objective(
        sc, include_cold, include_cost, qh_value, qc_value
    )
    if not (
        math.isfinite(qh_value)
        and math.isfinite(qc_value)
        and _model._feasible(qh_value, qc_value, sc)
    ):
        raise RuntimeError("Gurobi returned a non-finite or infeasible solution")

    return {
        "Q_hot": qh_value,
        "Q_cold": qc_value,
        "objective": float(m.ObjVal),
        "exact_objective": float(exact_objective),
        "method": "gurobi_genconstr_pwl_objective_validation",
        "status": int(m.Status),
        "pwl_points": points,
    }


def install() -> None:
    """Install this backend as the public model Gurobi adapter."""
    _model.solve_gurobi_round = solve_gurobi_round
    _model.solve_gurobi_r1 = lambda sc: solve_gurobi_round(sc, 1)
