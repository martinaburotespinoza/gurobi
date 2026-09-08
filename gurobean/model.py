from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, sqrt, pi
from typing import Dict, Optional, Tuple

import numpy as np

SQRT2PI = sqrt(2 * pi)


def phi(z: float) -> float:
    return exp(-0.5 * z * z) / SQRT2PI


def Phi(z: float) -> float:
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


@dataclass(frozen=True)
class Scenario:
    """Parameters explicitly supported by the Gurobean Game Guide model."""

    lambda_total: float
    p_hot: float = 1.0
    p_cold: float = 0.0
    revenue_hot: float = 1.0
    revenue_cold: float = 1.0
    cost_hot: float = 0.0
    cost_cold: float = 0.0
    # Kept as an explicit extension hook. The official guide's base formulation
    # uses waste rather than a positive salvage value, so the default is zero.
    salvage_hot: float = 0.0
    salvage_cold: float = 0.0
    beans_available: float = np.inf
    water_available: float = np.inf
    beans_hot: float = 0.0
    beans_cold: float = 0.0
    water_hot: float = 0.0
    water_cold: float = 0.0

    def __post_init__(self) -> None:
        if self.lambda_total < 0:
            raise ValueError("lambda_total must be >= 0")
        if self.p_hot < 0 or self.p_cold < 0:
            raise ValueError("drink probabilities must be >= 0")
        if self.p_hot + self.p_cold > 1 + 1e-12:
            raise ValueError("drink probabilities must sum <= 1")
        for name in (
            "revenue_hot", "revenue_cold", "cost_hot", "cost_cold",
            "salvage_hot", "salvage_cold", "beans_available",
            "water_available", "beans_hot", "beans_cold", "water_hot",
            "water_cold",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be >= 0")

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
            n,
            include_cold=n >= 2,
            include_brew_cost=n >= 3,
            include_markup=n >= 5,
            include_balking=n >= 6,
            include_multi_cup=n >= 7,
            include_service_rate=n >= 8,
        )


def expected_newsvendor_profit(
    Q: float,
    lam: float,
    revenue: float,
    cost: float,
    salvage: float = 0.0,
) -> float:
    """Exact expected profit under Gurobi's Normal approximation.

    The Game Guide states that hourly Poisson demand is approximated for the
    optimization by Normal(lam, lam). For D~N(lam, lam):

      E[min(Q,D)] = lam*Phi(z) - sqrt(lam)*phi(z) + Q*(1-Phi(z))
      E[(Q-D)+]  = (Q-lam)*Phi(z) + sqrt(lam)*phi(z)
      z = (Q-lam)/sqrt(lam)

    Profit = revenue*sales - cost*Q + salvage*leftover.
    """
    if Q < 0:
        return -np.inf
    if lam <= 0:
        return Q * (salvage - cost) if Q > 0 else 0.0

    sigma = sqrt(lam)
    z = (Q - lam) / sigma
    cdf = Phi(z)
    pdf = phi(z)
    sales = lam * cdf - sigma * pdf + Q * (1.0 - cdf)
    leftover = (Q - lam) * cdf + sigma * pdf
    return revenue * sales - cost * Q + salvage * leftover


def expected_newsvendor_gradient(
    Q: float,
    lam: float,
    revenue: float,
    cost: float,
    salvage: float = 0.0,
) -> float:
    """Derivative of the exact Normal-newsboy objective with respect to Q."""
    if Q < 0:
        return np.nan
    if lam <= 0:
        return salvage - cost
    z = (Q - lam) / sqrt(lam)
    # dE[min(Q,D)]/dQ = P(D >= Q) = 1-Phi(z)
    # dE[(Q-D)+]/dQ = P(D <= Q) = Phi(z)
    return revenue * (1.0 - Phi(z)) - cost + salvage * Phi(z)


def _resource_caps(sc: Scenario, include_cold: bool) -> Tuple[float, float]:
    """Return independent upper bounds implied by beans and water."""
    hot_caps = []
    cold_caps = []
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
    return (
        min(hot_caps) if hot_caps else np.inf,
        min(cold_caps) if cold_caps else np.inf,
    )


def _has_finite_shared_resource(sc: Scenario) -> bool:
    return np.isfinite(sc.beans_available) or np.isfinite(sc.water_available)


def _feasible(qh: float, qc: float, sc: Scenario) -> bool:
    return (
        qh >= -1e-10
        and qc >= -1e-10
        and sc.beans_hot * qh + sc.beans_cold * qc <= sc.beans_available + 1e-10
        and sc.water_hot * qh + sc.water_cold * qc <= sc.water_available + 1e-10
    )


def _economic_unconstrained_q(lam: float, revenue: float, cost: float, salvage: float) -> float:
    """Continuous single-product optimum under the exact Normal approximation."""
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
    # scipy is intentionally not required for the analytic reference.
    # Use a high-accuracy inverse-normal via a short bisection.
    lo, hi = -10.0, 10.0
    for _ in range(90):
        mid = 0.5 * (lo + hi)
        if Phi(mid) < critical_fractile:
            lo = mid
        else:
            hi = mid
    return max(0.0, lam + sqrt(lam) * 0.5 * (lo + hi))


def solve_round1_closed_form(sc: Scenario) -> dict:
    """R1 closed-form optimizer with an explicit finite resource cap.

    R1 has no brewing cost. With zero demand the objective can still have a
    positive salvage value, so the previous revenue-only early exit was too
    aggressive. The economic optimum is therefore computed first and then
    clipped by the physical resource cap.
    """
    hot_cap, _ = _resource_caps(sc, include_cold=False)
    if not np.isfinite(hot_cap):
        raise ValueError("R1 is unbounded without a finite hot-coffee resource cap")
    economic = _economic_unconstrained_q(
        sc.lambda_hot, sc.revenue_hot, 0.0, sc.salvage_hot
    )
    if sc.lambda_hot <= 0 and sc.salvage_hot > 0:
        q = hot_cap
    elif not np.isfinite(economic):
        q = hot_cap
    else:
        q = min(hot_cap, economic)
    q = max(0.0, float(q))
    return {
        "Q_hot": float(q),
        "Q_cold": 0.0,
        "objective": expected_newsvendor_profit(q, sc.lambda_hot, sc.revenue_hot, 0.0, sc.salvage_hot),
        "method": "closed_form",
    }


def solve_round1_scipy(sc: Scenario) -> dict:
    from scipy.optimize import minimize_scalar

    hot_cap, _ = _resource_caps(sc, include_cold=False)
    if not np.isfinite(hot_cap):
        raise ValueError("R1 is unbounded without a finite hot-coffee resource cap")
    res = minimize_scalar(
        lambda q: -expected_newsvendor_profit(q, sc.lambda_hot, sc.revenue_hot, 0.0, sc.salvage_hot),
        bounds=(0.0, hot_cap),
        method="bounded",
        options={"xatol": 1e-10},
    )
    return {
        "Q_hot": float(res.x),
        "Q_cold": 0.0,
        "objective": -float(res.fun),
        "method": "scipy_validation",
    }


def _round_objective(sc: Scenario, include_cold: bool, include_brew_cost: bool, qh: float, qc: float) -> float:
    cost_h = sc.cost_hot if include_brew_cost else 0.0
    cost_c = sc.cost_cold if include_brew_cost else 0.0
    value = expected_newsvendor_profit(qh, sc.lambda_hot, sc.revenue_hot, cost_h, sc.salvage_hot)
    if include_cold:
        value += expected_newsvendor_profit(qc, sc.lambda_cold, sc.revenue_cold, cost_c, sc.salvage_cold)
    return float(value)


def _round_bounds(sc: Scenario, include_cold: bool, include_brew_cost: bool) -> Tuple[float, float]:
    hot_resource_cap, cold_resource_cap = _resource_caps(sc, include_cold)
    hot_cost = sc.cost_hot if include_brew_cost else 0.0
    cold_cost = sc.cost_cold if include_brew_cost else 0.0

    hot_economic = _economic_unconstrained_q(sc.lambda_hot, sc.revenue_hot, hot_cost, sc.salvage_hot)
    cold_economic = _economic_unconstrained_q(sc.lambda_cold, sc.revenue_cold, cold_cost, sc.salvage_cold)

    hot_hi = min(hot_resource_cap, hot_economic)
    cold_hi = min(cold_resource_cap, cold_economic)

    if not np.isfinite(hot_hi):
        raise ValueError("Hot-coffee decision is unbounded under the supplied R2-R4 inputs")
    if include_cold and not np.isfinite(cold_hi):
        raise ValueError("Cold-coffee decision is unbounded under the supplied R2-R4 inputs")
    return max(0.0, float(hot_hi)), (max(0.0, float(cold_hi)) if include_cold else 0.0)


def solve_round_scipy(sc: Scenario, round_number: int) -> dict:
    """Reference optimizer for R1-R4 using the exact analytic objective.

    R1 and R3 are one-dimensional and admit analytic newsvendor structure.
    R2/R4 are two-product constrained problems; SLSQP is used only as a
    numerical cross-check/reference, never as a substitute for the Gurobi
    model adapter.
    """
    if round_number not in (1, 2, 3, 4):
        raise ValueError("solve_round_scipy currently covers rounds 1-4 only")

    include_cold = round_number in (2, 4)
    include_cost = round_number in (3, 4)
    hot_hi, cold_hi = _round_bounds(sc, include_cold, include_cost)

    if round_number == 1:
        return solve_round1_scipy(sc)

    if round_number == 3:
        from scipy.optimize import minimize_scalar
        cost = sc.cost_hot
        if hot_hi <= 1e-12:
            return {"Q_hot": 0.0, "Q_cold": 0.0, "objective": 0.0, "method": "scipy_reference"}
        res = minimize_scalar(
            lambda q: -expected_newsvendor_profit(q, sc.lambda_hot, sc.revenue_hot, cost, sc.salvage_hot),
            bounds=(0.0, hot_hi),
            method="bounded",
            options={"xatol": 1e-10},
        )
        return {"Q_hot": float(res.x), "Q_cold": 0.0, "objective": -float(res.fun), "method": "scipy_reference"}

    from scipy.optimize import minimize

    def objective(x: np.ndarray) -> float:
        return -_round_objective(sc, include_cold, include_cost, float(x[0]), float(x[1]))

    def gradient(x: np.ndarray) -> np.ndarray:
        cost_h = sc.cost_hot if include_cost else 0.0
        cost_c = sc.cost_cold if include_cost else 0.0
        return -np.asarray([
            expected_newsvendor_gradient(float(x[0]), sc.lambda_hot, sc.revenue_hot, cost_h, sc.salvage_hot),
            expected_newsvendor_gradient(float(x[1]), sc.lambda_cold, sc.revenue_cold, cost_c, sc.salvage_cold),
        ], dtype=float)

    starts = [
        np.array([min(hot_hi, sc.lambda_hot), min(cold_hi, sc.lambda_cold)], dtype=float),
        np.zeros(2, dtype=float),
        np.array([hot_hi, 0.0], dtype=float),
        np.array([0.0, cold_hi], dtype=float),
    ]
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
        {"type": "ineq", "fun": lambda x: sc.beans_available - sc.beans_hot * x[0] - sc.beans_cold * x[1],
         "jac": lambda x: np.asarray([-sc.beans_hot, -sc.beans_cold])},
        {"type": "ineq", "fun": lambda x: sc.water_available - sc.water_hot * x[0] - sc.water_cold * x[1],
         "jac": lambda x: np.asarray([-sc.water_hot, -sc.water_cold])},
    ]
    candidates = []
    for x0 in feasible_starts:
        result = minimize(
            objective, x0, jac=gradient, method="SLSQP",
            bounds=[(0.0, hot_hi), (0.0, cold_hi)],
            constraints=constraints,
            options={"ftol": 1e-10, "maxiter": 2000},
        )
        if result.success and _feasible(float(result.x[0]), float(result.x[1]), sc):
            candidates.append(result)
    if not candidates:
        raise RuntimeError(f"SLSQP failed for R{round_number}: no feasible successful start")
    result = min(candidates, key=lambda r: float(r.fun))
    qh, qc = map(float, result.x)
    return {
        "Q_hot": qh,
        "Q_cold": qc,
        "objective": _round_objective(sc, include_cold, include_cost, qh, qc),
        "method": "scipy_reference",
    }



def _resource_vertices(
    sc: Scenario,
    include_cold: bool,
    hot_hi: float,
    cold_hi: float,
) -> list[tuple[float, float]]:
    """Return feasible vertices of the bounded R1-R4 resource polygon.

    The PWL adapter can otherwise shift a true optimum located at a resource
    intersection onto a nearby PWL segment. Adding exact resource vertices
    as breakpoints preserves those economically important points without
    requiring an enormous uniform grid.
    """
    vertices: set[tuple[float, float]] = {
        (0.0, 0.0),
        (float(hot_hi), 0.0),
        (0.0, float(cold_hi)),
        (float(hot_hi), float(cold_hi)),
    }

    constraints: list[tuple[float, float, float]] = []

    if np.isfinite(sc.beans_available):
        constraints.append(
            (
                float(sc.beans_hot),
                float(sc.beans_cold if include_cold else 0.0),
                float(sc.beans_available),
            )
        )

    if np.isfinite(sc.water_available):
        constraints.append(
            (
                float(sc.water_hot),
                float(sc.water_cold if include_cold else 0.0),
                float(sc.water_available),
            )
        )

    for a, b, rhs in constraints:
        if abs(a) > 1e-15:
            for qc in (0.0, float(cold_hi)):
                qh = (rhs - b * qc) / a
                if (
                    -1e-9 <= qh <= hot_hi + 1e-9
                    and _feasible(qh, qc, sc)
                ):
                    vertices.add(
                        (
                            min(max(float(qh), 0.0), float(hot_hi)),
                            float(qc),
                        )
                    )

        if include_cold and abs(b) > 1e-15:
            for qh in (0.0, float(hot_hi)):
                qc = (rhs - a * qh) / b
                if (
                    -1e-9 <= qc <= cold_hi + 1e-9
                    and _feasible(qh, qc, sc)
                ):
                    vertices.add(
                        (
                            float(qh),
                            min(max(float(qc), 0.0), float(cold_hi)),
                        )
                    )

    if len(constraints) >= 2:
        a1, b1, r1 = constraints[0]
        a2, b2, r2 = constraints[1]
        det = a1 * b2 - a2 * b1

        if abs(det) > 1e-15:
            qh = (r1 * b2 - r2 * b1) / det
            qc = (a1 * r2 - a2 * r1) / det

            if (
                -1e-9 <= qh <= hot_hi + 1e-9
                and -1e-9 <= qc <= cold_hi + 1e-9
                and _feasible(qh, qc, sc)
            ):
                vertices.add(
                    (
                        min(max(float(qh), 0.0), float(hot_hi)),
                        min(max(float(qc), 0.0), float(cold_hi)),
                    )
                )

    return sorted(vertices)


def solve_gurobi_round(sc: Scenario, round_number: int, pwl_points: int = 20001) -> dict:
    """Build/solve the R1-R4 model in Gurobi using solver-backed PWL objectives."""
    if round_number not in (1, 2, 3, 4):
        raise ValueError("Gurobi adapter currently covers rounds 1-4 only")
    try:
        import gurobipy as gp
    except ImportError as exc:
        raise RuntimeError("gurobipy is not installed") from exc

    include_cold = round_number in (2, 4)
    include_cost = round_number in (3, 4)
    hot_hi, cold_hi = _round_bounds(sc, include_cold, include_cost)

    m = gp.Model(f"gurobean_r{round_number}")
    m.Params.OutputFlag = 0
    qh = m.addVar(lb=0.0, ub=hot_hi, name="Q_hot")
    qc = m.addVar(lb=0.0, ub=(cold_hi if include_cold else 0.0), name="Q_cold")

    if np.isfinite(sc.beans_available):
        m.addConstr(sc.beans_hot * qh + sc.beans_cold * qc <= sc.beans_available, name="beans")
    if np.isfinite(sc.water_available):
        m.addConstr(sc.water_hot * qh + sc.water_cold * qc <= sc.water_available, name="water")

    resource_vertices = _resource_vertices(sc, include_cold, hot_hi, cold_hi)

    def add_profit_pwl(q, hi, lam, revenue, cost, salvage, name, critical_points=None):
        hi = float(hi)
        if hi <= 1e-12:
            value = expected_newsvendor_profit(0.0, lam, revenue, cost, salvage)
            return m.addVar(lb=value, ub=value, name=name)
        points = max(2, int(pwl_points))
        if hi < 1e-5:
            t = m.addVar(lb=0.0, ub=1.0, name=f"{name}_normalized")
            m.addConstr(q == hi * t, name=f"{name}_scale")
            xs = np.linspace(0.0, 1.0, points)
            ys = [expected_newsvendor_profit(float(hi * x), lam, revenue, cost, salvage) for x in xs]
            y_lo, y_hi = min(ys), max(ys)
            y = m.addVar(lb=y_lo - max(1.0, abs(y_lo) * 1e-9), ub=y_hi + max(1.0, abs(y_hi) * 1e-9), name=name)
            m.addGenConstrPWL(t, y, xs.tolist(), ys, name=f"{name}_pwl")
            return y
        base_xs = np.linspace(0.0, hi, points)
        extra = [float(x) for x in (critical_points or []) if -1e-12 <= float(x) <= hi + 1e-12]
        xs = np.asarray(sorted({round(float(x), 15) for x in np.concatenate((base_xs, np.asarray(extra, dtype=float))) if -1e-12 <= float(x) <= hi + 1e-12}), dtype=float)
        xs = np.clip(xs, 0.0, hi)
        if len(xs) >= 2:
            scale = max(1.0, abs(float(hi)))
            min_dx = max(1.1e-6, 1e-8 * scale)
            filtered = [float(xs[0])]
            for x in xs[1:]:
                x = float(x)
                if x - filtered[-1] >= min_dx:
                    filtered.append(x)
            if filtered[-1] < float(hi):
                if float(hi) - filtered[-1] >= min_dx:
                    filtered.append(float(hi))
                elif len(filtered) >= 2:
                    filtered[-1] = float(hi)
            xs = np.asarray(filtered, dtype=float)
        if len(xs) < 2 or np.max(np.diff(xs)) <= 0.0:
            xs = np.asarray([0.0, hi], dtype=float)
        ys = [expected_newsvendor_profit(float(x), lam, revenue, cost, salvage) for x in xs]
        y_lo, y_hi = min(ys), max(ys)
        y = m.addVar(lb=y_lo - max(1.0, abs(y_lo) * 1e-9), ub=y_hi + max(1.0, abs(y_hi) * 1e-9), name=name)
        m.addGenConstrPWL(q, y, xs.tolist(), ys, name=f"{name}_pwl")
        return y

    yh = add_profit_pwl(qh, hot_hi, sc.lambda_hot, sc.revenue_hot, sc.cost_hot if include_cost else 0.0, sc.salvage_hot, "profit_hot", [v[0] for v in resource_vertices])
    yc = m.addVar(lb=0.0, ub=0.0, name="profit_cold_zero")
    if include_cold:
        yc = add_profit_pwl(qc, cold_hi, sc.lambda_cold, sc.revenue_cold, sc.cost_cold if include_cost else 0.0, sc.salvage_cold, "profit_cold", [v[1] for v in resource_vertices])

    m.setObjective(yh + yc, gp.GRB.MAXIMIZE)
    m.optimize()
    if m.Status != gp.GRB.OPTIMAL:
        raise RuntimeError(f"Gurobi did not return OPTIMAL; status={m.Status}")

    return {
        "Q_hot": float(qh.X),
        "Q_cold": float(qc.X) if include_cold else 0.0,
        "objective": float(m.ObjVal),
        "method": "gurobi_pwl_validation",
        "status": int(m.Status),
        "pwl_points": int(pwl_points),
    }


def solve_round(round_number: int, sc: Scenario, backend: str = "scipy") -> dict:
    """Unified R1-R4 entry point; later rounds remain calibration-gated."""
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
    raise NotImplementedError(
        f"R{round_number} requires calibrated game dynamics; no invented equation is used."
    )


def solve_gurobi_r1(sc: Scenario):
    """Backward-compatible R1 entry point."""
    return solve_gurobi_round(sc, 1)
