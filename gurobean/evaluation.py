from __future__ import annotations

"""Evaluation layer for candidate decisions.

This module deliberately separates evaluation from optimization. A candidate is
scored under repeated, reproducible simulations and reported with uncertainty;
no result here is treated as formal game certification.
"""

from dataclasses import dataclass
from math import sqrt
from typing import Callable

import numpy as np

from .model import Scenario
from .simulation import GurobeanSimulationConfig, SimulationResult, simulate_gurobean


@dataclass(frozen=True)
class EvaluationSummary:
    replications: int
    hours: int
    seed: int
    mean_profit: float
    profit_sd: float
    profit_se: float
    ci95_low: float
    ci95_high: float
    mean_served_customers: float
    mean_served_cups: float
    mean_lost_customers: float
    mean_queue: float
    mean_wait_minutes: float
    mean_utilization: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "replications": self.replications,
            "hours": self.hours,
            "seed": self.seed,
            "mean_profit": self.mean_profit,
            "profit_sd": self.profit_sd,
            "profit_se": self.profit_se,
            "ci95_low": self.ci95_low,
            "ci95_high": self.ci95_high,
            "mean_served_customers": self.mean_served_customers,
            "mean_served_cups": self.mean_served_cups,
            "mean_lost_customers": self.mean_lost_customers,
            "mean_queue": self.mean_queue,
            "mean_wait_minutes": self.mean_wait_minutes,
            "mean_utilization": self.mean_utilization,
        }


def _validate_replications(replications: int) -> None:
    if replications < 1:
        raise ValueError("replications must be >= 1")


def evaluate_candidate(
    config_factory: Callable[[int], GurobeanSimulationConfig],
    *,
    replications: int = 30,
    seed: int = 42,
) -> EvaluationSummary:
    """Evaluate one decision over repeated independent seeds.

    ``config_factory`` receives a deterministic seed for each replication.
    Common configuration is supplied by the caller; the evaluator owns only
    the replication schedule and aggregation.
    """
    _validate_replications(replications)
    profits: list[float] = []
    served: list[float] = []
    cups: list[float] = []
    lost: list[float] = []
    queues: list[float] = []
    waits: list[float] = []
    utilizations: list[float] = []
    hours: int | None = None

    for i in range(replications):
        rep_seed = int(seed + i * 100003)
        result, economics = simulate_gurobean(config_factory(rep_seed))
        if hours is None:
            hours = result.hours
        elif result.hours != hours:
            raise ValueError("all replications must use the same simulation horizon")
        profits.append(float(economics["profit"]))
        served.append(float(result.served))
        cups.append(float(economics["served_cups"]))
        lost.append(float(result.lost))
        queues.append(float(result.mean_queue))
        waits.append(float(result.mean_wait))
        utilizations.append(float(result.utilization))

    arr = np.asarray(profits, dtype=float)
    mean = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1)) if replications > 1 else 0.0
    se = float(sd / sqrt(replications)) if replications > 1 else 0.0
    margin = float(1.96 * se)
    return EvaluationSummary(
        replications=replications,
        hours=int(hours or 0),
        seed=int(seed),
        mean_profit=mean,
        profit_sd=sd,
        profit_se=se,
        ci95_low=mean - margin,
        ci95_high=mean + margin,
        mean_served_customers=float(np.mean(served)),
        mean_served_cups=float(np.mean(cups)),
        mean_lost_customers=float(np.mean(lost)),
        mean_queue=float(np.mean(queues)),
        mean_wait_minutes=float(np.mean(waits)),
        mean_utilization=float(np.mean(utilizations)),
    )


def evaluate_scenario(
    scenario: Scenario,
    *,
    markup: float,
    q_hot: float,
    q_cold: float,
    service_rate: float,
    replications: int = 30,
    seed: int = 42,
    hours: int = 120,
    warmup_hours: int = 0,
    barista_cost_per_hour: float = 0.0,
) -> EvaluationSummary:
    """Evaluate a concrete decision under the supplied scenario."""
    if q_hot < 0 or q_cold < 0:
        raise ValueError("brew quantities must be >= 0")
    if service_rate <= 0:
        raise ValueError("service_rate must be > 0")

    def factory(rep_seed: int) -> GurobeanSimulationConfig:
        return GurobeanSimulationConfig(
            hours=hours,
            warmup_hours=warmup_hours,
            seed=rep_seed,
            markup=markup,
            lambda_rate=scenario.lambda_total,
            p_hot=scenario.p_hot,
            p_cold=scenario.p_cold,
            mu_rate=service_rate,
            brew_hot_per_hour=q_hot,
            brew_cold_per_hour=q_cold,
            revenue_hot=scenario.revenue_hot + markup,
            revenue_cold=scenario.revenue_cold + markup,
            brew_cost_hot=scenario.cost_hot,
            brew_cost_cold=scenario.cost_cold,
            barista_cost_per_hour=barista_cost_per_hour,
        )

    return evaluate_candidate(factory, replications=replications, seed=seed)


def compare_summaries(candidate: EvaluationSummary, reference: EvaluationSummary) -> dict[str, float | bool]:
    """Compare two repeated-simulation evaluations without claiming certification."""
    delta = float(candidate.mean_profit - reference.mean_profit)
    reference_ci_contains_candidate = reference.ci95_low <= candidate.mean_profit <= reference.ci95_high
    return {
        "candidate_mean_profit": candidate.mean_profit,
        "reference_mean_profit": reference.mean_profit,
        "profit_delta": delta,
        "candidate_minus_reference_pct": float(100.0 * delta / abs(reference.mean_profit)) if reference.mean_profit else 0.0,
        "reference_ci95_low": reference.ci95_low,
        "reference_ci95_high": reference.ci95_high,
        "candidate_mean_inside_reference_ci95": bool(reference_ci_contains_candidate),
        "formal_game_certified": False,
    }
