from __future__ import annotations

from dataclasses import dataclass
from collections import deque
from math import inf
from typing import Callable

import numpy as np


@dataclass(frozen=True)
class SimulationResult:
    hours: int
    arrivals: int
    served: int
    lost: int
    mean_queue: float
    mean_wait: float
    utilization: float


@dataclass(frozen=True)
class GurobeanSimulationConfig:
    """Configurable dynamic simulator for R5-R8 validation.

    This is deliberately a parameterized reference simulator, not a claim that
    the unknown later-round game equations have been reverse-engineered. R5-R8
    behavior is supplied through explicit callables so only observed/calibrated
    rules can enter production decisions.
    """

    hours: int = 120
    warmup_hours: int = 0
    seed: int = 42
    markup: float = 0.0
    lambda_rate: float = 10.0
    p_hot: float = 1.0
    p_cold: float = 0.0
    mu_rate: float = 15.0
    brew_hot_per_hour: float = 20.0
    brew_cold_per_hour: float = 0.0
    revenue_hot: float = 1.0
    revenue_cold: float = 1.0
    brew_cost_hot: float = 0.0
    brew_cost_cold: float = 0.0
    barista_cost_per_hour: float = 0.0
    stay_probability: Callable[[float], float] | None = None
    order_size_sampler: Callable[[np.random.Generator], int] | None = None
    queue_metric: str = "queue"

    def __post_init__(self) -> None:
        if self.hours <= 0 or self.warmup_hours < 0 or self.warmup_hours >= self.hours:
            raise ValueError("hours must be > 0 and 0 <= warmup_hours < hours")
        for name in ("lambda_rate", "mu_rate", "brew_hot_per_hour", "brew_cold_per_hour", "markup", "revenue_hot", "revenue_cold", "brew_cost_hot", "brew_cost_cold", "barista_cost_per_hour"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and >= 0")
        if self.mu_rate <= 0:
            raise ValueError("mu_rate must be > 0")
        if self.p_hot < 0 or self.p_cold < 0 or self.p_hot + self.p_cold > 1 + 1e-12:
            raise ValueError("drink probabilities must be nonnegative and sum <= 1")
        if self.queue_metric not in {"queue", "wait_minutes"}:
            raise ValueError("queue_metric must be 'queue' or 'wait_minutes'")


def _draw_order_size(config: GurobeanSimulationConfig, rng: np.random.Generator) -> int:
    if config.order_size_sampler is None:
        return 1
    size = int(config.order_size_sampler(rng))
    if size < 1:
        raise ValueError("order_size_sampler must return an integer >= 1")
    return size


def _stay(config: GurobeanSimulationConfig, metric: float) -> bool:
    if config.stay_probability is None:
        return True
    p = float(config.stay_probability(metric))
    if not np.isfinite(p) or p < 0 or p > 1:
        raise ValueError("stay_probability must return a value in [0, 1]")
    return p


def simulate_gurobean(config: GurobeanSimulationConfig):
    """Continuous-time coffee-shop simulator with inventory, balking and orders.

    Arrivals are Poisson. Preferences are sampled independently. Orders join a
    FIFO queue, may balk according to a supplied calibrated probability, and
    consume brewed inventory when service begins. Service time is exponential
    with rate ``mu_rate`` per order. Brewing is reset at each simulated hour.
    """
    rng = np.random.default_rng(config.seed)
    end = config.hours * 60.0
    warm = config.warmup_hours * 60.0
    t = 0.0
    next_arrival = rng.exponential(60.0 / config.lambda_rate) if config.lambda_rate else inf
    next_departure = inf
    inventory = {"hot": 0.0, "cold": 0.0}
    queue: deque[tuple[float, str, int]] = deque()
    arrivals = served = lost = 0
    served_cups = 0
    lost_customers = 0
    wait_sum = 0.0
    wait_count = 0
    q_area = 0.0
    busy_area = 0.0
    profit = 0.0
    last = 0.0
    current_service_start = None
    next_brew_hour = 0.0

    def add_brew(hour_index: int) -> None:
        nonlocal profit
        inventory["hot"] += config.brew_hot_per_hour
        inventory["cold"] += config.brew_cold_per_hour
        # Brewing cost is incurred when production is committed, including waste.
        profit -= config.brew_cost_hot * config.brew_hot_per_hour
        profit -= config.brew_cost_cold * config.brew_cold_per_hour

    add_brew(0)
    while t < end:
        next_brew = next_brew_hour + 60.0
        nxt = min(next_arrival, next_departure, next_brew, end)
        left = max(last, warm)
        if nxt > left:
            q_area += len(queue) * (nxt - left)
            if next_departure != inf:
                busy_area += nxt - left
        t = nxt

        if t == next_brew:
            next_brew_hour += 60.0
            if t < end:
                add_brew(int(next_brew_hour // 60))
            last = t
            continue

        if t == next_arrival:
            in_window = t >= warm
            if in_window:
                arrivals += 1
            drink_draw = rng.random()
            drink = "hot" if drink_draw < config.p_hot else "cold" if drink_draw < config.p_hot + config.p_cold else None
            if drink is None:
                if in_window:
                    lost += 1
                    lost_customers += 1
                next_arrival = t + rng.exponential(60.0 / config.lambda_rate) if config.lambda_rate else inf
                last = t
                continue
            order_size = _draw_order_size(config, rng)
            projected_wait = 0.0
            if next_departure != inf:
                projected_wait = max(0.0, next_departure - t) + len(queue) * (60.0 / config.mu_rate)
            metric = float(len(queue)) if config.queue_metric == "queue" else projected_wait
            if not _stay(config, metric):
                if in_window:
                    lost += 1
                    lost_customers += 1
                next_arrival = t + rng.exponential(60.0 / config.lambda_rate) if config.lambda_rate else inf
                last = t
                continue
            queue.append((t, drink, order_size))
            if next_departure == inf:
                next_departure = t + rng.exponential(60.0 / config.mu_rate)
                current_service_start = t
            next_arrival = t + rng.exponential(60.0 / config.lambda_rate) if config.lambda_rate else inf
            last = t
            continue

        if t == next_departure:
            if queue:
                arrival_time, drink, order_size = queue.popleft()
                wait = max(0.0, t - arrival_time)
                if drink in inventory and inventory[drink] + 1e-12 >= order_size:
                    inventory[drink] -= order_size
                    if t >= warm and arrival_time >= warm:
                        served += 1
                        served_cups += order_size
                        wait_sum += wait
                        wait_count += 1
                        profit += order_size * (config.revenue_hot if drink == "hot" else config.revenue_cold)
                else:
                    if t >= warm and arrival_time >= warm:
                        lost += 1
                        lost_customers += 1
                next_departure = t + rng.exponential(60.0 / config.mu_rate)
                current_service_start = t
            else:
                next_departure = inf
                current_service_start = None
            last = t
            continue
        break

    measured_hours = max(config.hours - config.warmup_hours, 1)
    effective_minutes = measured_hours * 60.0
    if config.barista_cost_per_hour:
        profit -= config.barista_cost_per_hour * measured_hours
    result = SimulationResult(
        hours=config.hours,
        arrivals=arrivals,
        served=served,
        lost=lost,
        mean_queue=float(q_area / effective_minutes),
        mean_wait=float(wait_sum / wait_count) if wait_count else 0.0,
        utilization=float(min(1.0, busy_area / effective_minutes)),
    )
    return result, {
        "profit": float(profit),
        "served_cups": int(served_cups),
        "lost_customers": int(lost_customers),
        "inventory_hot_end": float(inventory["hot"]),
        "inventory_cold_end": float(inventory["cold"]),
        "seed": int(config.seed),
    }


def simulate_queue(
    lambda_rate: float,
    mu_rate: float,
    hours: int = 120,
    seed: int = 42,
    warmup_hours: int = 0,
) -> SimulationResult:
    """Reproducible M/M/1 event simulator used as a validation baseline."""
    if not np.isfinite(lambda_rate) or lambda_rate < 0:
        raise ValueError("lambda_rate must be finite and >= 0")
    if not np.isfinite(mu_rate) or mu_rate <= 0:
        raise ValueError("mu_rate must be finite and > 0")
    if hours <= 0 or warmup_hours < 0 or warmup_hours >= hours:
        raise ValueError("hours must be > 0 and 0 <= warmup_hours < hours")

    rng = np.random.default_rng(seed)
    t = 0.0
    queue: list[float] = []
    next_departure = np.inf
    next_arrival = rng.exponential(60.0 / lambda_rate) if lambda_rate else np.inf
    arrivals = served = 0
    q_area = 0.0
    wait_sum = 0.0
    wait_count = 0
    busy_time = 0.0
    end = hours * 60.0
    warm = warmup_hours * 60.0

    def measure(a: float, b: float) -> None:
        nonlocal q_area, busy_time
        left = max(a, warm)
        if b <= left:
            return
        dt = b - left
        q_area += len(queue) * dt
        if next_departure != np.inf:
            busy_time += dt

    while t < end:
        nxt = min(next_arrival, next_departure, end)
        measure(t, nxt)
        t = nxt

        if t == next_arrival:
            in_measurement = t >= warm
            if in_measurement:
                arrivals += 1
            if next_departure == np.inf:
                service = rng.exponential(60.0 / mu_rate)
                next_departure = t + service
                if in_measurement:
                    served += 1
            else:
                queue.append(t)
            next_arrival = t + rng.exponential(60.0 / lambda_rate) if lambda_rate else np.inf
        elif t == next_departure:
            if queue:
                a = queue.pop(0)
                if t >= warm and a >= warm:
                    served += 1
                    wait_sum += t - a
                    wait_count += 1
                next_departure = t + rng.exponential(60.0 / mu_rate)
            else:
                next_departure = np.inf
        else:
            break

    effective = max((hours - warmup_hours) * 60.0, 1.0)
    return SimulationResult(
        hours=hours,
        arrivals=arrivals,
        served=served,
        lost=0,
        mean_queue=float(q_area / effective),
        mean_wait=float(wait_sum / wait_count) if wait_count else 0.0,
        utilization=float(min(1.0, busy_time / effective)),
    )
