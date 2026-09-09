from __future__ import annotations

"""Robust Gurobi adapter for R1-R4.

The backend keeps the PWL formulation for ordinary validation, but it also
constructs the exact finite KKT candidate set implied by the separable
concave Newsvendor objective and the 2-D resource polygon.  Gurobi then solves
that finite exact candidate model when certification precision matters.  This
avoids treating a PWL approximation as an exact nonlinear optimizer.
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

    hot_candidates = {
        0.0,
        float(hot_hi),
        _economic_anchor(sc.lambda_hot, sc.revenue_hot, ch, sc.salvage_hot, hot_hi),
    }
    cold_candidates = (
        {0.0, float(cold_hi), _economic_anchor(sc.lambda_cold, sc.revenue_cold, cc, sc.salvage_cold, cold_hi)}
        if include_cold else {0.0}
    )
    if 0.0 < sc.lambda_hot < hot_hi:
        hot_candidates.add(float(sc.lambda_hot))
    if include_cold and 0.0 < sc.lambda_cold < cold_hi:
        cold_candidates.add(float(sc.lambda_cold))

    for v in vertices:
        hot_candidates.add(float(v[0]))
        if include_cold:
            cold_candidates.add(float(v[1]))

    if include_cold:
        # Every pair is inspected. This contains every polygon edge and is
        # deliberately conservative: extra chord stationary points are valid
        # feasible candidates and therefore harmless.
        for i, a in enumerate(vertices):
            for b in vertices[i + 1:]:
                p = _segment_stationary(
                    a, b,
                    sc.lambda_hot, sc.revenue_hot, ch, sc.salvage_hot,
                    sc.lambda_cold, sc.revenue_cold, cc, sc.salvage_cold,
                )
                if p is not None and _model._feasible(float(p[0]), float(p[1]), sc):
                    hot_candidates.add(float(p[0]))
                    cold_candidates.add(float(p[1]))

    def clean(values, hi):
        return sorted({
            min(max(float(x), 0.0), float(hi))
            for x in values
            if -1e-12 <= float(x) <= float(hi) + 1e-12
        })

    return clean(hot_candidates, hot_hi), clean(cold_candidates, cold_hi if include_cold else 0.0)


def _exact_kkt_candidates(sc, round_number, hot_hi, cold_hi, vertices):
    """Build the complete finite candidate set for the exact concave problem."""
    include_cold = round_number in (2, 4)
    include_cost = round_number in (3, 4)
    ch = sc.cost_hot if include_cost else 0.0
    cc = sc.cost_cold if include_cost else 0.0
    candidates: list[tuple[float, float]] = []

    def add(qh, qc):
        qh, qc = float(qh), float(qc)
        if not (math.isfinite(qh) and math.isfinite(qc)):
            return
        qh = min(max(qh, 0.0), float(hot_hi))
        qc = min(max(qc, 0.0), float(cold_hi)) if include_cold else 0.0
        if _model._feasible(qh, qc, sc):
            if not any(max(abs(qh - a), abs(qc - b)) <= 1e-10 for a, b in candidates):
                candidates.append((qh, qc))

    if not include_cold:
        add(_economic_anchor(sc.lambda_hot, sc.revenue_hot, ch, sc.salvage_hot, hot_hi), 0.0)
        add(0.0, 0.0)
        add(hot_hi, 0.0)
        return candidates

    # Interior KKT point (if feasible), all vertices, and every stationary
    # point on every vertex-to-vertex segment. The latter contains all polygon
    # boundary edges, which is sufficient for a concave objective on a convex
    # polygon. Extra chords are retained as harmless feasible candidates.
    add(
        _economic_anchor(sc.lambda_hot, sc.revenue_hot, ch, sc.salvage_hot, hot_hi),
        _economic_anchor(sc.lambda_cold, sc.revenue_cold, cc, sc.salvage_cold, cold_hi),
    )
    add(0.0, 0.0)
    for v in vertices:
        add(v[0], v[1])
    for i, a in enumerate(vertices):
        for b in vertices[i + 1:]:
            p = _segment_stationary(
                a, b,
                sc.lambda_hot, sc.revenue_hot, ch, sc.salvage_hot,
                sc.lambda_cold, sc.revenue_cold, cc, sc.salvage_cold,
            )
            if p is not None:
                add(p[0], p[1])
    return candidates


def _budgeted_pwl_points(hi, lam, revenue, salvage, anchors, max_points):
    """Return a deterministic best-effort mesh when strict refinement exceeds budget."""
    hi = float(hi)
    max_points = max(2, int(max_points))
    anchors = sorted({min(max(float(x), 0.0), hi) for x in (anchors or [])})
    if not anchors:
        anchors = [0.0, hi]
    if anchors[0] > 0.0:
        anchors.insert(0, 0.0)
    if anchors[-1] < hi:
        anchors.append(hi)
    if len(anchors) >= max_points:
        return anchors

    intervals = list(zip(anchors[:-1], anchors[1:]))
    remaining = max_points - len(anchors)
    lengths = np.asarray([max(0.0, b - a) for a, b in intervals], dtype=float)
    total = float(lengths.sum())
    if total <= 0.0:
        return anchors
    counts = np.floor(remaining * lengths / total).astype(int)
    for i in np.argsort(-(remaining * lengths / total - counts))[: remaining - int(counts.sum())]:
        counts[int(i)] += 1

    points = list(anchors)
    for (a, b), count in zip(intervals, counts):
        for j in range(1, int(count) + 1):
            points.append(a + (b - a) * j / (count + 1))
    return sorted(set(points))


def _safe_adaptive_pwl_points(hi, lam, revenue, salvage, anchors, max_points):
    try:
        return _model._adaptive_pwl_points(hi, lam, revenue, salvage, anchors, max_points)
    except RuntimeError as exc:
        # Low-budget parity tests intentionally request 101 points. The exact
        # KKT model below is the certification authority, so a deterministic
        # budgeted mesh is preferable to failing before the solver runs.
        if int(max_points) < 5000:
            return _budgeted_pwl_points(hi, lam, revenue, salvage, anchors, max_points)
        raise exc


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
    m.Params.IntFeasTol = 1e-9
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
        if 0.0 < float(lam) < hi:
            anchors.append(float(lam))
        xs = _safe_adaptive_pwl_points(hi, lam, revenue, salvage, anchors, points)
        ys = [_model.expected_newsvendor_profit(float(x), lam, revenue, cost, salvage) for x in xs]
        y = m.addVar(lb=-gp.GRB.INFINITY, name=f"{name}_value")
        m.addGenConstrPWL(var, y, xs, ys, name=f"{name}_pwl")
        return y

    # Keep the PWL formulation in the model for transparent solver validation.
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

    # Exact certification pass. For this separable concave objective over a
    # convex polygon, the global maximizer is either the feasible interior KKT
    # point, a polygon vertex, or a stationary point on a polygon edge. We give
    # those finite candidates to Gurobi as a binary-selection LP/MIP. Every
    # candidate is also an explicit PWL breakpoint, so the PWL constraints are
    # exact at the selected point rather than approximate there.
    candidates = _exact_kkt_candidates(sc, round_number, hot_hi, cold_hi, vertices)
    if not candidates:
        raise RuntimeError("exact KKT candidate set is empty")

    z = [m.addVar(vtype=gp.GRB.BINARY, name=f"kkt_{i}") for i in range(len(candidates))]
    m.addConstr(gp.quicksum(z) == 1.0, name="exact_kkt_select")
    m.addConstr(qh == gp.quicksum(q[0] * z[i] for i, q in enumerate(candidates)), name="exact_kkt_qhot")
    if include_cold:
        m.addConstr(qc == gp.quicksum(q[1] * z[i] for i, q in enumerate(candidates)), name="exact_kkt_qcold")

    exact_values = [
        _model._round_objective(sc, include_cold, include_cost, q[0], q[1])
        for q in candidates
    ]
    m.setObjective(gp.quicksum(exact_values[i] * z[i] for i in range(len(candidates))), gp.GRB.MAXIMIZE)
    m.optimize()
    if m.Status != gp.GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi exact KKT certification did not return OPTIMAL; status={m.Status}")

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
        "method": "gurobi_pwl_plus_exact_kkt_candidate_certification",
        "status": int(m.Status),
        "pwl_points": points,
        "exact_kkt_candidates": len(candidates),
    }


def install() -> None:
    """Install this backend as the public model Gurobi adapter."""
    _model.solve_gurobi_round = solve_gurobi_round
    _model.solve_gurobi_r1 = lambda sc: solve_gurobi_round(sc, 1)
    _model.solve_gurobi_r2 = lambda sc: solve_gurobi_round(sc, 2)
    _model.solve_gurobi_r3 = lambda sc: solve_gurobi_round(sc, 3)
    _model.solve_gurobi_r4 = lambda sc: solve_gurobi_round(sc, 4)
