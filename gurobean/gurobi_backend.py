from __future__ import annotations

"""Robust Gurobi adapter for R1-R4.

The adapter represents the concave Newsvendor objective explicitly with
addGenConstrPWL() and auxiliary value variables.  The PWL mesh is guaranteed
to contain the exact stationary candidates of the continuous concave problem,
including stationary points on resource-boundary segments.  Since linear
interpolation of a concave function is a lower approximation, an exact global
optimizer that is a mesh breakpoint cannot be beaten by the PWL model.
"""

import math

import numpy as np

from . import model as _model


PWL_POINTS_DEFAULT = 20001


def _economic_anchor(lam: float, revenue: float, cost: float, salvage: float, hi: float) -> float:
    q = _model._economic_unconstrained_q(float(lam), float(revenue), float(cost), float(salvage))
    if not math.isfinite(q):
        return float(hi)
    return min(max(float(q), 0.0), float(hi))


def _gradient(q: float, lam: float, revenue: float, cost: float, salvage: float) -> float:
    return float(_model.expected_newsvendor_gradient(q, lam, revenue, cost, salvage))


def _segment_stationary(a, b, lam_h, rev_h, cost_h, sal_h, lam_c, rev_c, cost_c, sal_c):
    """Find the stationary point of the exact concave objective on a segment."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    d = b - a
    if float(np.max(np.abs(d))) <= 1e-14:
        return None

    def directional(t: float) -> float:
        q = a + float(t) * d
        gh = _gradient(float(q[0]), lam_h, rev_h, cost_h, sal_h)
        gc = _gradient(float(q[1]), lam_c, rev_c, cost_c, sal_c)
        return gh * float(d[0]) + gc * float(d[1])

    fa = directional(0.0)
    fb = directional(1.0)
    if not (math.isfinite(fa) and math.isfinite(fb)):
        return None
    if abs(fa) <= 1e-12:
        return tuple(a)
    if abs(fb) <= 1e-12:
        return tuple(b)
    if fa * fb > 0.0:
        return None

    lo, hi = 0.0, 1.0
    # Concavity makes the directional derivative monotone non-increasing.
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        fm = directional(mid)
        if not math.isfinite(fm):
            return None
        if abs(fm) <= 1e-13:
            lo = hi = mid
            break
        if fm > 0.0:
            lo = mid
        else:
            hi = mid
    q = a + (0.5 * (lo + hi)) * d
    return float(q[0]), float(q[1])


def _exact_candidate_points(sc, round_number, hot_hi, cold_hi, vertices):
    """Return exact KKT candidates whose coordinates should be PWL breakpoints."""
    include_cold = round_number in (2, 4)
    include_cost = round_number in (3, 4)
    ch = sc.cost_hot if include_cost else 0.0
    cc = sc.cost_cold if include_cost else 0.0

    hot_candidates = {0.0, float(hot_hi), _economic_anchor(sc.lambda_hot, sc.revenue_hot, ch, sc.salvage_hot, hot_hi)}
    cold_candidates = {0.0, float(cold_hi), _economic_anchor(sc.lambda_cold, sc.revenue_cold, cc, sc.salvage_cold, cold_hi)} if include_cold else {0.0}
    if 0.0 < sc.lambda_hot < hot_hi:
        hot_candidates.add(float(sc.lambda_hot))
    if include_cold and 0.0 < sc.lambda_cold < cold_hi:
        cold_candidates.add(float(sc.lambda_cold))

    for v in vertices:
        hot_candidates.add(float(v[0]))
        if include_cold:
            cold_candidates.add(float(v[1]))

    if include_cold:
        # Every pair of polygon vertices is cheap to inspect and guarantees
        # that every feasible polygon edge receives its exact 1-D stationary
        # candidate. Interior chords are harmless extra anchors.
        for i, a in enumerate(vertices):
            for b in vertices[i + 1:]:
                p = _segment_stationary(
                    a, b,
                    sc.lambda_hot, sc.revenue_hot, ch, sc.salvage_hot,
                    sc.lambda_cold, sc.revenue_cold, cc, sc.salvage_cold,
                )
                if p is not None:
                    hot_candidates.add(float(p[0]))
                    cold_candidates.add(float(p[1]))

    def clean(values, hi):
        return [min(max(float(x), 0.0), float(hi)) for x in values if -1e-12 <= float(x) <= float(hi) + 1e-12]

    return clean(hot_candidates, hot_hi), clean(cold_candidates, cold_hi if include_cold else 0.0)


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
        m.addConstr(sc.beans_hot * qh + sc.beans_cold * qc <= sc.beans_available, name="beans")
    if np.isfinite(sc.water_available):
        m.addConstr(sc.water_hot * qh + sc.water_cold * qc <= sc.water_available, name="water")

    vertices = _model._resource_vertices(sc, include_cold, hot_hi, cold_hi)
    hot_candidates, cold_candidates = _exact_candidate_points(sc, round_number, hot_hi, cold_hi, vertices)

    def add_profit(var, hi, lam, revenue, cost, salvage, critical_points, name):
        hi = float(hi)
        if hi <= 1e-12:
            return None
        anchors = list(critical_points or [])
        # Preserve the curvature peak for stable error-controlled refinement.
        if 0.0 < float(lam) < hi:
            anchors.append(float(lam))
        xs = _model._adaptive_pwl_points(hi, lam, revenue, salvage, anchors, points)
        ys = [_model.expected_newsvendor_profit(float(x), lam, revenue, cost, salvage) for x in xs]
        y = m.addVar(lb=-gp.GRB.INFINITY, name=f"{name}_value")
        m.addGenConstrPWL(var, y, xs, ys, name=f"{name}_pwl")
        return y

    yh = add_profit(qh, hot_hi, sc.lambda_hot, sc.revenue_hot, sc.cost_hot if include_cost else 0.0, sc.salvage_hot, hot_candidates, "profit_hot")
    yc = None
    if include_cold:
        yc = add_profit(qc, cold_hi, sc.lambda_cold, sc.revenue_cold, sc.cost_cold if include_cost else 0.0, sc.salvage_cold, cold_candidates, "profit_cold")

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
    exact_objective = _model._round_objective(sc, include_cold, include_cost, qh_value, qc_value)
    if not (math.isfinite(qh_value) and math.isfinite(qc_value) and _model._feasible(qh_value, qc_value, sc)):
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
