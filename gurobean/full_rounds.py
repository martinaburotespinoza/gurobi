from __future__ import annotations

"""Operational R5-R8 solver built on the configurable coffee-shop simulator.

R1-R4 keep their analytical/Gurobi certification path. R5-R8 are nonlinear,
stochastic rounds: this module makes them executable through deterministic
common-random-number Monte Carlo optimization. The response coefficients are
explicit inputs so the engine never silently invents a game calibration.

The official Gurobean guide defines the progression: markup affects arrivals,
balking depends on congestion, multi-cup orders scale demand, and service rate
becomes a decision with a cost. Exact game parity still requires observations
from the real game and the repository evidence gate.
"""

from dataclasses import dataclass
from math import exp, isfinite
from typing import Callable

import numpy as np

from .model import Scenario
from .official_rules import arrival_rate_from_markup
from .simulation import GurobeanSimulationConfig, simulate_gurobean


@dataclass(frozen=True)
class DynamicRoundParams:
    """Explicit R5-R8 response parameters.

    ``arrival_baseline_rate``, ``arrival_reference_rate`` and
    ``reference_markup`` are the R5 anchor parameters. R6 uses a logistic
    stay-probability model over queue length. R7 uses a shifted-Poisson order
    size. R8 uses a configurable convex hourly service-cost curve.
    """

    arrival_baseline_rate: float
    arrival_reference_rate: float
    reference_markup: float
    markup_min: float = 0.0
    markup_max: float = 5.0
    balking_a: float = 2.0
    balking_b: float = -0.15
    multi_cup_theta: float = 1.0
    service_rate_base: float = 65.0
    service_rate_min: float = 50.0
    service_rate_max: float = 90.0
    service_cost_fixed: float = 0.0
    service_cost_linear: float = 0.0
    service_cost_quadratic: float = 0.0
    hours: int = 120
    warmup_hours: int = 0
    replications: int = 4
    seed: int = 42
    coordinate_points: int = 7

    def __post_init__(self) -> None:
        numeric = (
            "arrival_baseline_rate", "arrival_reference_rate", "reference_markup",
            "markup_min", "markup_max", "balking_a", "balking_b",
            "multi_cup_theta", "service_rate_base", "service_rate_min",
            "service_rate_max", "service_cost_fixed", "service_cost_linear",
            "service_cost_quadratic", "hours", "warmup_hours", "replications",
            "seed", "coordinate_points",
        )
        for name in numeric:
            value = float(getattr(self, name))
            if not isfinite(value):
                raise ValueError(f"{name} must be finite")
        if self.arrival_baseline_rate <= 0 or self.arrival_reference_rate <= 0:
            raise ValueError("arrival anchor rates must be > 0")
        if self.arrival_reference_rate > self.arrival_baseline_rate:
            raise ValueError("arrival_reference_rate must be <= arrival_baseline_rate")
        if self.reference_markup <= 0:
            raise ValueError("reference_markup must be > 0")
        if self.markup_min < 0 or self.markup_max <= self.markup_min:
            raise ValueError("invalid markup bounds")
        if self.multi_cup_theta < 0:
            raise ValueError("multi_cup_theta must be >= 0")
        if self.service_rate_min <= 0 or self.service_rate_max < self.service_rate_min:
            raise ValueError("invalid service-rate bounds")
        if not self.service_rate_min <= self.service_rate_base <= self.service_rate_max:
            raise ValueError("service_rate_base must lie inside service-rate bounds")
        if self.service_cost_fixed < 0 or self.service_cost_linear < 0 or self.service_cost_quadratic < 0:
            raise ValueError("service costs must be >= 0")
        if self.hours <= 0 or self.warmup_hours < 0 or self.warmup_hours >= self.hours:
            raise ValueError("invalid simulation horizon")
        if self.replications < 1 or self.coordinate_points < 3:
            raise ValueError("replications >= 1 and coordinate_points >= 3 are required")

    def arrival_rate(self, markup: float) -> float:
        return arrival_rate_from_markup(
            markup,
            self.arrival_baseline_rate,
            self.arrival_reference_rate,
            self.reference_markup,
        )

    def stay_probability(self, queue_length: float) -> float:
        eta = max(-40.0, min(40.0, self.balking_a + self.balking_b * queue_length))
        return 1.0 / (1.0 + exp(-eta))

    def service_cost(self, service_rate: float) -> float:
        delta = max(0.0, service_rate - self.service_rate_base)
        return (
            self.service_cost_fixed
            + self.service_cost_linear * delta
            + self.service_cost_quadratic * delta * delta
        )


def _resource_caps(sc: Scenario) -> tuple[float, float]:
    hot = []
    cold = []
    if np.isfinite(sc.beans_available):
        if sc.beans_hot > 0:
            hot.append(sc.beans_available / sc.beans_hot)
        if sc.beans_cold > 0:
            cold.append(sc.beans_available / sc.beans_cold)
    if np.isfinite(sc.water_available):
        if sc.water_hot > 0:
            hot.append(sc.water_available / sc.water_hot)
        if sc.water_cold > 0:
            cold.append(sc.water_available / sc.water_cold)
    return (min(hot) if hot else np.inf, min(cold) if cold else np.inf)


def _feasible(qh: float, qc: float, sc: Scenario) -> bool:
    return (
        qh >= 0 and qc >= 0
        and sc.beans_hot * qh + sc.beans_cold * qc <= sc.beans_available + 1e-9
        and sc.water_hot * qh + sc.water_cold * qc <= sc.water_available + 1e-9
    )


def _project_feasible(qh: float, qc: float, sc: Scenario) -> tuple[float, float]:
    """Project a nonnegative starting point into the shared-resource polygon."""
    qh = max(0.0, float(qh))
    qc = max(0.0, float(qc))
    if _feasible(qh, qc, sc):
        return qh, qc
    scale = 1.0
    for _ in range(80):
        scale *= 0.5
        candidate = (qh * scale, qc * scale)
        if _feasible(candidate[0], candidate[1], sc):
            return candidate
    if _feasible(0.0, 0.0, sc):
        return 0.0, 0.0
    raise ValueError("supplied resource constraints make the zero-production point infeasible")


def _order_sampler(theta: float) -> Callable[[np.random.Generator], int]:
    def sample(rng: np.random.Generator) -> int:
        return 1 + int(rng.poisson(theta))
    return sample


def _simulate_candidate(
    sc: Scenario,
    params: DynamicRoundParams,
    round_number: int,
    qh: float,
    qc: float,
    markup: float,
    service_rate: float,
) -> dict[str, float]:
    arrival = params.arrival_rate(markup)
    stay = params.stay_probability if round_number >= 6 else None
    order_sampler = _order_sampler(params.multi_cup_theta) if round_number >= 7 else None
    price_hot = sc.cost_hot + markup
    price_cold = sc.cost_cold + markup
    profits: list[float] = []
    served: list[float] = []
    lost: list[float] = []
    queues: list[float] = []
    waits: list[float] = []
    utilizations: list[float] = []

    for rep in range(params.replications):
        seed = int(params.seed + rep * 100003)
        cfg = GurobeanSimulationConfig(
            hours=params.hours,
            warmup_hours=params.warmup_hours,
            seed=seed,
            markup=markup,
            lambda_rate=arrival,
            p_hot=sc.p_hot,
            p_cold=sc.p_cold,
            mu_rate=service_rate,
            brew_hot_per_hour=qh,
            brew_cold_per_hour=qc,
            revenue_hot=price_hot,
            revenue_cold=price_cold,
            brew_cost_hot=sc.cost_hot,
            brew_cost_cold=sc.cost_cold,
            barista_cost_per_hour=params.service_cost(service_rate) if round_number >= 8 else 0.0,
            stay_probability=stay,
            order_size_sampler=order_sampler,
            queue_metric="queue",
        )
        metrics, economics = simulate_gurobean(cfg)
        profits.append(economics["profit"])
        served.append(float(metrics.served))
        lost.append(float(metrics.lost))
        queues.append(metrics.mean_queue)
        waits.append(metrics.mean_wait)
        utilizations.append(metrics.utilization)

    return {
        "expected_profit": float(np.mean(profits)),
        "profit_sd": float(np.std(profits, ddof=0)),
        "served_customers": float(np.mean(served)),
        "lost_customers": float(np.mean(lost)),
        "mean_queue": float(np.mean(queues)),
        "mean_wait_minutes": float(np.mean(waits)),
        "utilization": float(np.mean(utilizations)),
        "arrival_rate": float(arrival),
        "price_hot": float(price_hot),
        "price_cold": float(price_cold),
        "service_cost_per_hour": float(params.service_cost(service_rate) if round_number >= 8 else 0.0),
    }


def _coordinate_grid(value: float, low: float, high: float, points: int) -> np.ndarray:
    if high <= low + 1e-12:
        return np.asarray([low], dtype=float)
    span = high - low
    left = max(low, value - 0.35 * span)
    right = min(high, value + 0.35 * span)
    grid = np.linspace(left, right, points)
    return np.unique(np.concatenate((grid, np.asarray([low, high], dtype=float))))


def solve_dynamic_round(
    sc: Scenario,
    round_number: int,
    params: DynamicRoundParams,
) -> dict:
    if round_number not in (5, 6, 7, 8):
        raise ValueError("dynamic solver covers R5-R8")

    hot_cap, cold_cap = _resource_caps(sc)
    hot_hi = min(hot_cap, max(sc.lambda_total * 2.0, 1.0))
    cold_hi = min(cold_cap, max(sc.lambda_total * max(sc.p_cold, 0.25) * 2.0, 1.0))
    if not np.isfinite(hot_hi) or not np.isfinite(cold_hi):
        raise ValueError("R5-R8 require finite beans/water resource caps")
    hot_hi = max(0.0, float(hot_hi))
    cold_hi = max(0.0, float(cold_hi))

    qh, qc = _project_feasible(min(hot_hi, sc.lambda_hot), min(cold_hi, sc.lambda_cold), sc)
    markup = 0.5 * (params.markup_min + params.markup_max)
    service = params.service_rate_base
    best: dict | None = None

    def evaluate(values: tuple[float, float, float, float]) -> dict:
        xq, xc, xm, xv = values
        if not _feasible(xq, xc, sc):
            return {"expected_profit": -float("inf")}
        return _simulate_candidate(sc, params, round_number, xq, xc, xm, xv)

    for _pass in range(4):
        dimensions = [
            ("qh", _coordinate_grid(qh, 0.0, hot_hi, params.coordinate_points)),
            ("qc", _coordinate_grid(qc, 0.0, cold_hi, params.coordinate_points)),
            ("markup", _coordinate_grid(markup, params.markup_min, params.markup_max, params.coordinate_points)),
        ]
        if round_number >= 8:
            dimensions.append(("service_rate", _coordinate_grid(service, params.service_rate_min, params.service_rate_max, params.coordinate_points)))
        else:
            dimensions.append(("service_rate", np.asarray([params.service_rate_base], dtype=float)))

        current = _project_feasible(qh, qc, sc) + (markup, service)
        for name, grid in dimensions:
            local_best = None
            index = {"qh": 0, "qc": 1, "markup": 2, "service_rate": 3}[name]
            for candidate in grid:
                trial = list(current)
                trial[index] = float(candidate)
                metrics = evaluate(tuple(trial))
                if local_best is None or metrics["expected_profit"] > local_best[0]:
                    local_best = (metrics["expected_profit"], tuple(trial), metrics)
            if local_best is not None:
                current = local_best[1]
                if best is None or local_best[2]["expected_profit"] > best["metrics"]["expected_profit"]:
                    best = {"values": current, "metrics": local_best[2]}
            qh, qc, markup, service = current
            qh, qc = _project_feasible(qh, qc, sc)

    if best is None:
        raise RuntimeError("dynamic R5-R8 optimizer found no feasible candidate")

    qh, qc, markup, service = best["values"]
    qh, qc = _project_feasible(qh, qc, sc)

    # The stored best metrics can refer to the pre-projection candidate from an
    # earlier coordinate pass. Recompute at the exact decision returned to the
    # caller so /solve and /evaluate use the identical candidate and CRN seed.
    metrics = _simulate_candidate(sc, params, round_number, qh, qc, markup, service)

    return {
        "Q_hot": float(qh),
        "Q_cold": float(qc),
        "markup": float(markup),
        "service_rate": float(service),
        "objective": float(metrics["expected_profit"]),
        "expected_profit": float(metrics["expected_profit"]),
        "profit_sd": float(metrics["profit_sd"]),
        "arrival_rate": float(metrics["arrival_rate"]),
        "price_hot": float(metrics["price_hot"]),
        "price_cold": float(metrics["price_cold"]),
        "served_customers": float(metrics["served_customers"]),
        "lost_customers": float(metrics["lost_customers"]),
        "mean_queue": float(metrics["mean_queue"]),
        "mean_wait_minutes": float(metrics["mean_wait_minutes"]),
        "utilization": float(metrics["utilization"]),
        "service_cost_per_hour": float(metrics["service_cost_per_hour"]),
        "method": "common_random_numbers_monte_carlo_coordinate_search",
        "simulation_hours": params.hours,
        "replications": params.replications,
        "seed": params.seed,
        "operational": True,
        "formal_game_certified": False,
        "certification_note": "R5-R8 are executable simulation rounds; formal game parity requires real-game observations and evidence-gate promotion.",
    }
