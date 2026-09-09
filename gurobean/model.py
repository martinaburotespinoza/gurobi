from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, sqrt, pi
from statistics import NormalDist
from typing import Tuple

import numpy as np

SQRT2PI = sqrt(2 * pi)
_STD_NORMAL = NormalDist()


def phi(z: float) -> float:
    return exp(-0.5 * z * z) / SQRT2PI


def Phi(z: float) -> float:
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


@dataclass(frozen=True)
class Scenario:
    lambda_total: float
    p_hot: float = 1.0
    p_cold: float = 0.0
    revenue_hot: float = 1.0
    revenue_cold: float = 1.0
    cost_hot: float = 0.0
    cost_cold: float = 0.0
    salvage_hot: float = 0.0
    salvage_cold: float = 0.0
    beans_available: float = np.inf
    water_available: float = np.inf
    beans_hot: float = 0.0
    beans_cold: float = 0.0
    water_hot: float = 0.0
    water_cold: float = 0.0

    def __post_init__(self) -> None:
        finite_fields = (
            "lambda_total", "p_hot", "p_cold", "revenue_hot", "revenue_cold",
            "cost_hot", "cost_cold", "salvage_hot", "salvage_cold",
            "beans_hot", "beans_cold", "water_hot", "water_cold",
        )
        for name in finite_fields:
            value = float(getattr(self, name))
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if value < 0:
                raise ValueError(f"{name} must be >= 0")
        for name in ("beans_available", "water_available"):
            value = float(getattr(self, name))
            if np.isnan(value) or np.isneginf(value) or value < 0:
                raise ValueError(f"{name} must be >= 0 or +inf")
        if self.p_hot > 1 or self.p_cold > 1:
            raise ValueError("drink probabilities must be in [0, 1]")
        if abs(self.p_hot + self.p_cold - 1.0) > 1e-12:
            raise ValueError("drink probabilities must sum to 1")

    @property
    def lambda_hot(self) -> float:
        return self.lambda_total * self.p_hot

    @property
    def lambda_cold(self) -> float:
        return self.lambda_total * self.p_cold


@dataclass(frozen=True)
class RoundConfig:
    round_number: int
    include_cold: bool = False
    include_brew_cost: bool = False
    include_markup: bool = False
    include_balking: bool = False
    include_multi_cup: bool = False
    include_service_rate: bool = False

    @staticmethod
    def for_round(n: int) -> "RoundConfig":
        if n not in range(1, 9):
            raise ValueError("round must be 1..8")
        return RoundConfig(
            n, include_cold=n >= 2, include_brew_cost=n >= 3,
            include_markup=n >= 5, include_balking=n >= 6,
            include_multi_cup=n >= 7, include_service_rate=n >= 8,
        )


def expected_newsvendor_profit(Q: float, lam: float, revenue: float, cost: float, salvage: float = 0.0) -> float:
    if Q < 0:
        return -np.inf
    if Q == 0.0:
        return 0.0
    if lam <= 0:
        return Q * (salvage - cost)
    sigma = sqrt(lam)
    z = (Q - lam) / sigma
    cdf = Phi(z)
    pdf = phi(z)
    sales = lam * cdf - sigma * pdf + Q * (1.0 - cdf)
    leftover = (Q - lam) * cdf + sigma * pdf
    return revenue * sales - cost * Q + salvage * leftover


def expected_newsvendor_gradient(Q: float, lam: float, revenue: float, cost: float, salvage: float = 0.0) -> float:
    if Q < 0:
        return np.nan
    if lam <= 0:
        return salvage - cost
    z = (Q - lam) / sqrt(lam)
    return revenue * (1.0 - Phi(z)) - cost + salvage * Phi(z)


def _resource_caps(sc: Scenario, include_cold: bool) -> Tuple[float, float]:
    hot_caps, cold_caps = [], []
    if np.isfinite(sc.beans_available):
        if sc.beans_hot > 0:
            hot_caps.append(sc.beans_available / sc.beans_hot)
        if include_cold and sc.beans_cold > 0:
            cold_caps.append(sc.beans_available / sc.beans_cold)
    if np.isfinite(sc.water_available):
        if sc.water_hot > 0:
            hot_caps.append(sc.water_available / sc.water_hot)
        if include_cold and sc.water_cold > 0:
            cold_caps.append(sc.water_available / sc.water_cold)
    return min(hot_caps) if hot_caps else np.inf, min(cold_caps) if cold_caps else np.inf


def _has_finite_shared_resource(sc: Scenario) -> bool:
    return np.isfinite(sc.beans_available) or np.isfinite(sc.water_available)


def _feasible(qh: float, qc: float, sc: Scenario) -> bool:
    return (
        qh >= -1e-10 and qc >= -1e-10
        and sc.beans_hot * qh + sc.beans_cold * qc <= sc.beans_available + 1e-10
        and sc.water_hot * qh + sc.water_cold * qc <= sc.water_available + 1e-10
    )


def _economic_unconstrained_q(lam: float, revenue: float, cost: float, salvage: float) -> float:
    if lam <= 0:
        return 0.0
    denominator = revenue - salvage
    numerator = revenue - cost
    if denominator <= 0:
        return 0.0
    critical_fractile = numerator / denominator
    if critical_fractile <= 0:
        return 0.0
    if critical_fractile >= 1:
        return np.inf
    return max(0.0, lam + sqrt(lam) * _STD_NORMAL.inv_cdf(critical_fractile))


def solve_round1_closed_form(sc: Scenario) -> dict:
    hot_cap, _ = _resource_caps(sc, False)
    if not np.isfinite(hot_cap):
        raise ValueError("R1 is unbounded without a finite hot-coffee resource cap")
    economic = _economic_unconstrained_q(sc.lambda_hot, sc.revenue_hot, 0.0, sc.salvage_hot)
    if sc.lambda_hot <= 0 and sc.salvage_hot > 0:
        q = hot_cap
    elif not np.isfinite(economic):
        q = hot_cap
    else:
        q = min(hot_cap, economic)
    q = max(0.0, float(q))
    return {"Q_hot": q, "Q_cold": 0.0, "objective": expected_newsvendor_profit(q, sc.lambda_hot, sc.revenue_hot, 0.0, sc.salvage_hot), "method": "closed_form"}


def solve_round1_scipy(sc: Scenario) -> dict:
    from scipy.optimize import minimize_scalar
    hot_cap, _ = _resource_caps(sc, False)
    if not np.isfinite(hot_cap):
        raise ValueError("R1 is unbounded without a finite hot-coffee resource cap")
    res = minimize_scalar(lambda q: -expected_newsvendor_profit(q, sc.lambda_hot, sc.revenue_hot, 0.0, sc.salvage_hot), bounds=(0.0, hot_cap), method="bounded", options={"xatol": 1e-10})
    return {"Q_hot": float(res.x), "Q_cold": 0.0, "objective": -float(res.fun), "method": "scipy_validation"}


def _round_objective(sc: Scenario, include_cold: bool, include_brew_cost: bool, qh: float, qc: float) -> float:
    ch = sc.cost_hot if include_brew_cost else 0.0
    cc = sc.cost_cold if include_brew_cost else 0.0
    value = expected_newsvendor_profit(qh, sc.lambda_hot, sc.revenue_hot, ch, sc.salvage_hot)
    if include_cold:
        value += expected_newsvendor_profit(qc, sc.lambda_cold, sc.revenue_cold, cc, sc.salvage_cold)
    return float(value)


def _round_bounds(sc: Scenario, include_cold: bool, include_brew_cost: bool) -> Tuple[float, float]:
    hot_resource_cap, cold_resource_cap = _resource_caps(sc, include_cold)
    hc = sc.cost_hot if include_brew_cost else 0.0
    cc = sc.cost_cold if include_brew_cost else 0.0
    hot_hi = min(hot_resource_cap, _economic_unconstrained_q(sc.lambda_hot, sc.revenue_hot, hc, sc.salvage_hot))
    cold_hi = min(cold_resource_cap, _economic_unconstrained_q(sc.lambda_cold, sc.revenue_cold, cc, sc.salvage_cold))
    if not np.isfinite(hot_hi):
        raise ValueError("Hot-coffee decision is unbounded under the supplied R2-R4 inputs")
    if include_cold and not np.isfinite(cold_hi):
        raise ValueError("Cold-coffee decision is unbounded under the supplied R2-R4 inputs")
    return max(0.0, float(hot_hi)), max(0.0, float(cold_hi)) if include_cold else 0.0


def solve_round_scipy(sc: Scenario, round_number: int) -> dict:
    if round_number not in (1, 2, 3, 4):
        raise ValueError("solve_round_scipy currently covers rounds 1-4 only")
    include_cold, include_cost = round_number in (2, 4), round_number in (3, 4)
    hot_hi, cold_hi = _round_bounds(sc, include_cold, include_cost)
    if round_number == 1:
        return solve_round1_scipy(sc)
    if round_number == 3:
        from scipy.optimize import minimize_scalar
        if hot_hi <= 1e-12:
            return {"Q_hot": 0.0, "Q_cold": 0.0, "objective": 0.0, "method": "scipy_reference"}
        res = minimize_scalar(lambda q: -expected_newsvendor_profit(q, sc.lambda_hot, sc.revenue_hot, sc.cost_hot, sc.salvage_hot), bounds=(0.0, hot_hi), method="bounded", options={"xatol": 1e-10})
        return {"Q_hot": float(res.x), "Q_cold": 0.0, "objective": -float(res.fun), "method": "scipy_reference"}
    from scipy.optimize import minimize
    def objective(x):
        return -_round_objective(sc, include_cold, include_cost, float(x[0]), float(x[1]))
    def gradient(x):
        ch = sc.cost_hot if include_cost else 0.0
        cc = sc.cost_cold if include_cost else 0.0
        return -np.asarray([
            expected_newsvendor_gradient(float(x[0]), sc.lambda_hot, sc.revenue_hot, ch, sc.salvage_hot),
            expected_newsvendor_gradient(float(x[1]), sc.lambda_cold, sc.revenue_cold, cc, sc.salvage_cold),
        ], dtype=float)
    starts = [np.array([min(hot_hi, sc.lambda_hot), min(cold_hi, sc.lambda_cold)]), np.zeros(2), np.array([hot_hi, 0.0]), np.array([0.0, cold_hi])]
    feasible_starts = []
    for x0 in starts:
        x0 = np.clip(x0, 0.0, [hot_hi, cold_hi])
        if not _feasible(x0[0], x0[1], sc):
            scale = 1.0
            for _ in range(100):
                scale *= 0.5
                candidate = x0 * scale
                if _feasible(candidate[0], candidate[1], sc):
                    x0 = candidate
                    break
        feasible_starts.append(x0)
    constraints = [
        {"type": "ineq", "fun": lambda x: sc.beans_available - sc.beans_hot*x[0] - sc.beans_cold*x[1], "jac": lambda x: np.asarray([-sc.beans_hot, -sc.beans_cold])},
        {"type": "ineq", "fun": lambda x: sc.water_available - sc.water_hot*x[0] - sc.water_cold*x[1], "jac": lambda x: np.asarray([-sc.water_hot, -sc.water_cold])},
    ]
    candidates = []
    for x0 in feasible_starts:
        result = minimize(objective, x0, jac=gradient, method="SLSQP", bounds=[(0.0, hot_hi), (0.0, cold_hi)], constraints=constraints, options={"ftol": 1e-10, "maxiter": 2000})
        if result.success and _feasible(float(result.x[0]), float(result.x[1]), sc):
            candidates.append(result)
    if not candidates:
        raise RuntimeError(f"SLSQP failed for R{round_number}: no feasible successful start")
    result = min(candidates, key=lambda r: float(r.fun))
    qh, qc = map(float, result.x)
    return {"Q_hot": qh, "Q_cold": qc, "objective": _round_objective(sc, include_cold, include_cost, qh, qc), "method": "scipy_reference"}


def _resource_vertices(sc: Scenario, include_cold: bool, hot_hi: float, cold_hi: float) -> list[tuple[float, float]]:
    vertices = {(0.0, 0.0), (float(hot_hi), 0.0), (0.0, float(cold_hi)), (float(hot_hi), float(cold_hi))}
    constraints = []
    if np.isfinite(sc.beans_available):
        constraints.append((float(sc.beans_hot), float(sc.beans_cold if include_cold else 0.0), float(sc.beans_available)))
    if np.isfinite(sc.water_available):
        constraints.append((float(sc.water_hot), float(sc.water_cold if include_cold else 0.0), float(sc.water_available)))
    for a, b, rhs in constraints:
        if abs(a) > 1e-15:
            for qc in (0.0, float(cold_hi)):
                qh = (rhs - b * qc) / a
                if -1e-9 <= qh <= hot_hi + 1e-9 and _feasible(qh, qc, sc):
                    vertices.add((min(max(float(qh), 0.0), float(hot_hi)), float(qc)))
        if include_cold and abs(b) > 1e-15:
            for qh in (0.0, float(hot_hi)):
                qc = (rhs - a * qh) / b
                if -1e-9 <= qc <= cold_hi + 1e-9 and _feasible(qh, qc, sc):
                    vertices.add((float(qh), min(max(float(qc), 0.0), float(cold_hi))))
    if len(constraints) >= 2:
        a1, b1, r1 = constraints[0]
        a2, b2, r2 = constraints[1]
        det = a1 * b2 - a2 * b1
        if abs(det) > 1e-15:
            qh = (r1 * b2 - r2 * b1) / det
            qc = (a1 * r2 - a2 * r1) / det
            if -1e-9 <= qh <= hot_hi + 1e-9 and -1e-9 <= qc <= cold_hi + 1e-9 and _feasible(qh, qc, sc):
                vertices.add((min(max(float(qh), 0.0), float(hot_hi)), min(max(float(qc), 0.0), float(cold_hi))))
    return sorted(vertices)


PWL_APPROX_TOL = 2.0e-7


def _newsvendor_curvature(Q: float, lam: float, revenue: float, salvage: float) -> float:
    if lam <= 0.0 or revenue <= salvage:
        return 0.0
    z = (float(Q) - lam) / sqrt(lam)
    return (revenue - salvage) * phi(z) / sqrt(lam)


def _interval_curvature(a: float, b: float, lam: float, revenue: float, salvage: float) -> float:
    if b <= a:
        return 0.0
    xs = [float(a), float(b)]
    if a <= lam <= b:
        xs.append(float(lam))
    return max(_newsvendor_curvature(x, lam, revenue, salvage) for x in xs)


def _adaptive_pwl_points(hi: float, lam: float, revenue: float, salvage: float, critical_points: list[float] | None, max_points: int) -> list[float]:
    hi = float(hi)
    if hi <= 1e-12:
        return [0.0] if hi <= 0.0 else [0.0, hi]
    anchors = {0.0, hi}
    for value in critical_points or []:
        x = float(value)
        if -1e-12 <= x <= hi + 1e-12:
            anchors.add(min(max(x, 0.0), hi))
    anchors = sorted(anchors)
    if _interval_curvature(0.0, hi, lam, revenue, salvage) == 0.0:
        return anchors
    stack = list(zip(anchors[:-1], anchors[1:]))
    refined = []
    while stack:
        a, b = stack.pop()
        bound = _interval_curvature(a, b, lam, revenue, salvage) * (b - a) ** 2 / 8.0
        if bound <= PWL_APPROX_TOL:
            refined.append((a, b))
            continue
        mid = 0.5 * (a + b)
        if mid <= a or mid >= b:
            refined.append((a, b))
            continue
        stack.append((mid, b))
        stack.append((a, mid))
        if len(stack) + len(refined) > max_points * 2:
            raise RuntimeError(f"adaptive PWL refinement exceeded point budget ({max_points}); domain={hi}, lambda={lam}, revenue={revenue}, salvage={salvage}")
    refined.sort()
    points = [refined[0][0]]
    for a, b in refined:
        if abs(points[-1] - a) > 1e-14:
            points.append(a)
        if b > points[-1]:
            points.append(b)
    if len(points) > max_points:
        raise RuntimeError(f"adaptive PWL refinement requires {len(points)} points > {max_points}")
    return points


def solve_gurobi_round(sc: Scenario, round_number: int, pwl_points: int = 20001) -> dict:
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
    m.Params.MIPGap = 0.0
    m.Params.MIPGapAbs = 1e-9
    m.ModelSense = gp.GRB.MAXIMIZE
    qh = m.addVar(lb=0.0, ub=hot_hi, name="Q_hot")
    qc = m.addVar(lb=0.0, ub=cold_hi if include_cold else 0.0, name="Q_cold")
    if np.isfinite(sc.beans_available):
        m.addConstr(sc.beans_hot * qh + sc.beans_cold * qc <= sc.beans_available, name="beans")
    if np.isfinite(sc.water_available):
        m.addConstr(sc.water_hot * qh + sc.water_cold * qc <= sc.water_available, name="water")
    resource_vertices = _resource_vertices(sc, include_cold, hot_hi, cold_hi)
    objective_constant = 0.0

    def set_profit_pwl(var, hi, lam, revenue, cost, salvage, critical_points=None, name="profit"):
        nonlocal objective_constant
        hi = float(hi)
        if hi <= 1e-12:
            objective_constant += float(expected_newsvendor_profit(0.0, lam, revenue, cost, salvage))
            return
        if hi < 1e-5:
            t = m.addVar(lb=0.0, ub=1.0, name=f"{name}_normalized")
            m.addConstr(var == hi * t, name=f"{name}_scale")
            xs = np.linspace(0.0, 1.0, points)
            ys = [expected_newsvendor_profit(float(hi * x), lam, revenue, cost, salvage) for x in xs]
            m.setPWLObj(t, xs.tolist(), ys)
            return
        xs = _adaptive_pwl_points(hi, lam, revenue, salvage, critical_points, points)
        ys = [expected_newsvendor_profit(float(x), lam, revenue, cost, salvage) for x in xs]
        m.setPWLObj(var, xs, ys)

    set_profit_pwl(qh, hot_hi, sc.lambda_hot, sc.revenue_hot, sc.cost_hot if include_cost else 0.0, sc.salvage_hot, [v[0] for v in resource_vertices], "profit_hot")
    if include_cold:
        set_profit_pwl(qc, cold_hi, sc.lambda_cold, sc.revenue_cold, sc.cost_cold if include_cost else 0.0, sc.salvage_cold, [v[1] for v in resource_vertices], "profit_cold")
    if objective_constant:
        m.ObjCon = objective_constant
    m.optimize()
    if m.Status != gp.GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi did not return OPTIMAL; status={m.Status}")
    qh_value = float(qh.X)
    qc_value = float(qc.X) if include_cold else 0.0
    exact_objective = _round_objective(sc, include_cold, include_cost, qh_value, qc_value)
    return {"Q_hot": qh_value, "Q_cold": qc_value, "objective": float(m.ObjVal), "exact_objective": exact_objective, "method": "gurobi_native_pwl_objective_validation", "status": int(m.Status), "pwl_points": points}


def solve_round(round_number: int, sc: Scenario, backend: str = "scipy") -> dict:
    if round_number not in range(1, 9):
        raise ValueError("round must be 1..8")
    if round_number <= 4:
        if backend == "scipy":
            return solve_round_scipy(sc, round_number)
        if backend == "gurobi":
            return solve_gurobi_round(sc, round_number)
        if backend == "closed_form" and round_number == 1:
            return solve_round1_closed_form(sc)
        raise ValueError("backend must be scipy, gurobi, or closed_form (R1 only)")
    raise NotImplementedError(f"R{round_number} requires calibrated game dynamics; no invented equation is used.")


def solve_gurobi_r1(sc: Scenario):
    return solve_gurobi_round(sc, 1)


def solve_reference_round(sc: Scenario, round_number: int | None = None) -> dict:
    if round_number is None:
        round_number = 1
    if round_number not in (1, 2, 3, 4):
        raise ValueError("reference currently covers rounds 1-4 only")
    result = solve_round_scipy(sc, round_number)
    qh = float(result["Q_hot"])
    qc = float(result["Q_cold"])
    return {"q": qh, "q_cold": qc, "objective": float(_round_objective(sc, round_number in (2, 4), round_number in (3, 4), qh, qc)), "success": True, "method": result.get("method", "scipy_reference")}