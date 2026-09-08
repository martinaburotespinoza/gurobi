from __future__ import annotations

"""Evidence-gated calibration for the unknown R5-R8 game dynamics."""

from dataclasses import dataclass, field
from math import lgamma, log
from typing import Dict, Iterable, List, Sequence

import numpy as np


@dataclass(frozen=True)
class Observation:
    round_number: int
    variables: Dict[str, float]
    outputs: Dict[str, float]
    repetitions: int = 1
    source: str = "game"
    successes: int | None = None
    trials: int | None = None

    def __post_init__(self) -> None:
        if self.repetitions < 1:
            raise ValueError("repetitions must be >= 1")
        if self.successes is not None or self.trials is not None:
            if self.successes is None or self.trials is None:
                raise ValueError("successes and trials must be supplied together")
            if self.trials < 1 or self.successes < 0 or self.successes > self.trials:
                raise ValueError("R6 successes/trials must satisfy 0 <= successes <= trials and trials >= 1")


@dataclass
class CalibrationDataset:
    observations: List[Observation] = field(default_factory=list)

    def add(self, observation: Observation) -> None:
        if observation.round_number not in (5, 6, 7, 8):
            raise ValueError("calibration observations must belong to R5-R8")
        if observation.repetitions < 1:
            raise ValueError("repetitions must be >= 1")
        self.observations.append(observation)

    def for_round(self, round_number: int) -> List[Observation]:
        return [o for o in self.observations if o.round_number == round_number]


@dataclass(frozen=True)
class FitResult:
    round_number: int
    family: str
    parameters: Dict[str, float]
    rmse: float
    n: int
    score: float
    diagnostics: Dict[str, float | str]


@dataclass(frozen=True)
class PromotionDecision:
    eligible: bool
    round_number: int
    family: str | None
    reason: str
    metrics: Dict[str, float]


def _rmse(y: np.ndarray, yhat: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y - yhat) ** 2)))


def _aic(y: np.ndarray, yhat: np.ndarray, k: int) -> float:
    n = len(y)
    rss = max(float(np.sum((y - yhat) ** 2)), 1e-12)
    return float(n * log(rss / n) + 2 * k)


def _validate_numeric_pairs(observations: Sequence[Observation], x_key: str, y_key: str) -> tuple[np.ndarray, np.ndarray]:
    if not observations:
        raise ValueError("no observations supplied")
    x, y = [], []
    for i, o in enumerate(observations):
        if x_key not in o.variables or y_key not in o.outputs:
            raise ValueError(f"observation {i} missing {x_key!r} or {y_key!r}")
        xv, yv = float(o.variables[x_key]), float(o.outputs[y_key])
        if not np.isfinite(xv) or not np.isfinite(yv):
            raise ValueError(f"observation {i} contains non-finite values")
        x.append(xv); y.append(yv)
    return np.asarray(x), np.asarray(y)


def fit_r5_arrival_rate(observations: Sequence[Observation]) -> List[FitResult]:
    """Fit λ(markup), enforcing economically sensible non-increasing candidates."""
    from scipy.optimize import least_squares
    m, y = _validate_numeric_pairs(observations, "markup", "arrival_rate")
    if np.any(m < 0) or np.any(y < 0):
        raise ValueError("R5 markup and arrival_rate must be >= 0")
    results: List[FitResult] = []

    X = np.column_stack([np.ones_like(m), m])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    # Projection onto b <= 0 keeps the candidate economically monotone.
    b = min(float(beta[1]), 0.0)
    a = max(float(np.mean(y - b * m)), 0.0)
    pred = a + b * m
    results.append(FitResult(5, "linear", {"a": a, "b": b}, _rmse(y, pred), len(y), _aic(y, pred, 2), {"monotone": 1.0}))

    def residual(theta: np.ndarray) -> np.ndarray:
        a_, b_ = theta
        return a_ * np.exp(-b_ * m) - y

    fit = least_squares(residual, x0=[max(float(np.max(y)), 1e-6), 0.01], bounds=([0.0, 0.0], [np.inf, np.inf]))
    a_, b_ = map(float, fit.x)
    pred = a_ * np.exp(-b_ * m)
    results.append(FitResult(5, "exponential", {"a": a_, "b": b_}, _rmse(y, pred), len(y), _aic(y, pred, 2), {"monotone": 1.0}))
    return sorted(results, key=lambda r: r.score)


def fit_r6_balking(observations: Sequence[Observation]) -> List[FitResult]:
    """Fit stay probability versus queue/wait using a binomial-logistic model."""
    from scipy.optimize import minimize
    if not observations:
        raise ValueError("no observations supplied")
    key = "queue" if all("queue" in o.variables for o in observations) else "wait_minutes"
    x = np.asarray([float(o.variables[key]) for o in observations], dtype=float)
    y = np.asarray([float(o.outputs["stay_probability"]) for o in observations], dtype=float)
    if np.any(~np.isfinite(x)) or np.any((y < 0) | (y > 1)):
        raise ValueError("R6 contains invalid queue/wait or stay_probability values")
    X = np.column_stack([np.ones_like(x), x])
    counts_available = all(o.successes is not None and o.trials is not None for o in observations)
    if counts_available:
        successes = np.asarray([int(o.successes) for o in observations], dtype=float)
        trials = np.asarray([int(o.trials) for o in observations], dtype=float)
        y = successes / trials
        weights = trials
    else:
        y_clip = np.clip(y, 1e-8, 1 - 1e-8)
        weights = np.ones_like(y)

    y_clip = np.clip(y, 1e-8, 1 - 1e-8)
    z = np.log(y_clip / (1 - y_clip))
    beta, *_ = np.linalg.lstsq(X * np.sqrt(weights)[:, None], z * np.sqrt(weights), rcond=None)
    beta[1] = min(float(beta[1]), 0.0)

    def nll(b: np.ndarray) -> float:
        eta = np.clip(X @ b, -40, 40)
        p = 1 / (1 + np.exp(-eta))
        if counts_available:
            return float(-np.sum(successes * np.log(p) + (trials - successes) * np.log(1 - p)))
        return float(-np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))

    fit = minimize(nll, beta, method="BFGS")
    b0, b1 = map(float, fit.x)
    b1 = min(b1, 0.0)
    pred = 1 / (1 + np.exp(-np.clip(X @ [b0, b1], -40, 40)))
    diagnostics = {"input": key, "monotone": 1.0, "binomial_counts": 1.0 if counts_available else 0.0}
    return [FitResult(6, "logistic", {"a": b0, "b": b1}, _rmse(y, pred), len(y), _aic(y, pred, 2), diagnostics)]


def _log_factorial(n: int) -> float:
    if n < 0:
        raise ValueError("n must be >= 0")
    return lgamma(n + 1)


def fit_r7_order_size(observations: Sequence[Observation]) -> List[FitResult]:
    sizes = np.asarray([int(o.outputs["order_size"]) for o in observations], dtype=int)
    if len(sizes) == 0 or np.any(sizes < 1):
        raise ValueError("R7 order_size must contain integers >= 1")
    n = len(sizes)
    mean = float(np.mean(sizes))
    theta = max(mean - 1.0, 1e-12)
    ll_pois = float(np.sum(-theta + (sizes - 1) * np.log(theta) - np.array([_log_factorial(int(k)) for k in sizes - 1])))
    aic_pois = -2 * ll_pois + 2
    p = min(max(1.0 / max(mean, 1.0), 1e-12), 1 - 1e-12)
    ll_geo = float(np.sum(np.log(p) + (sizes - 1) * np.log(1 - p)))
    aic_geo = -2 * ll_geo + 2
    return sorted([
        FitResult(7, "shifted_poisson", {"theta": theta}, 0.0, n, aic_pois, {}),
        FitResult(7, "geometric", {"p": p}, 0.0, n, aic_geo, {}),
    ], key=lambda r: r.score)


def fit_r8_service_cost(observations: Sequence[Observation]) -> List[FitResult]:
    mu, cost = _validate_numeric_pairs(observations, "service_rate", "barista_cost_per_hour")
    if np.any(mu < 0) or np.any(cost < 0):
        raise ValueError("R8 service rate and cost must be >= 0")
    results: List[FitResult] = []
    from scipy.optimize import least_squares
    # Positive coefficients keep the fitted wage curve non-negative and
    # non-decreasing over the calibrated domain.
    fit1 = least_squares(lambda b: b[0] + b[1] * mu - cost, x0=[max(float(np.min(cost)), 0.0), 0.01], bounds=([0.0, 0.0], [np.inf, np.inf]))
    a1, b_1 = map(float, fit1.x)
    pred1 = a1 + b_1 * mu
    results.append(FitResult(8, "linear", {"a": a1, "b": b_1}, _rmse(cost, pred1), len(cost), _aic(cost, pred1, 2), {"monotone": 1.0, "nonnegative": 1.0}))
    fit2 = least_squares(lambda b: b[0] + b[1] * mu + b[2] * mu * mu - cost, x0=[max(float(np.min(cost)), 0.0), 0.0, 0.001], bounds=([0.0, 0.0, 0.0], [np.inf, np.inf, np.inf]))
    a2, b_2, c2 = map(float, fit2.x)
    pred2 = a2 + b_2 * mu + c2 * mu * mu
    results.append(FitResult(8, "quadratic", {"a": a2, "b": b_2, "c": c2}, _rmse(cost, pred2), len(cost), _aic(cost, pred2, 3), {"monotone": 1.0, "nonnegative": 1.0}))
    return sorted(results, key=lambda r: r.score)


def best_fit(results: Iterable[FitResult]) -> FitResult:
    results = list(results)
    if not results:
        raise ValueError("no calibration results")
    return min(results, key=lambda r: r.score)


def calibration_gate(observations: Sequence[Observation], results: Sequence[FitResult], *, min_observations: int = 8, max_rmse: float | None = None, require_monotone: bool = False) -> PromotionDecision:
    if not results:
        return PromotionDecision(False, 0, None, "no_fit_results", {})
    round_number = results[0].round_number
    try:
        validate_observations(observations, round_number)
    except ValueError as exc:
        return PromotionDecision(False, round_number, None, str(exc), {})
    best = min(results, key=lambda r: r.score)
    n_eff = sum(o.repetitions for o in observations)
    metrics = {"observations": float(len(observations)), "effective_repetitions": float(n_eff), "rmse": float(best.rmse), "score": float(best.score)}
    if len(observations) < min_observations:
        return PromotionDecision(False, round_number, best.family, "insufficient_observations", metrics)
    if max_rmse is not None and best.rmse > max_rmse:
        return PromotionDecision(False, round_number, best.family, "rmse_above_threshold", metrics)
    if require_monotone and round_number == 5 and best.family == "linear" and best.parameters.get("b", 0) > 1e-12:
        return PromotionDecision(False, round_number, best.family, "arrival_rate_not_monotone_decreasing", metrics)
    return PromotionDecision(True, round_number, best.family, "promotion_gate_passed", metrics)


def validate_observations(observations: Sequence[Observation], round_number: int) -> None:
    if round_number not in (5, 6, 7, 8):
        raise ValueError("calibration round must be 5..8")
    if not observations:
        raise ValueError(f"R{round_number}: no observations supplied")
    for i, o in enumerate(observations):
        if o.round_number != round_number:
            raise ValueError(f"observation {i} belongs to R{o.round_number}, expected R{round_number}")
        if not o.variables or not o.outputs:
            raise ValueError(f"observation {i} must contain variables and outputs")
        if o.repetitions < 1:
            raise ValueError(f"observation {i}: repetitions must be >= 1")


def promotion_report(observations: Sequence[Observation], fits: Sequence[FitResult], *, min_observations: int = 8, max_rmse: float | None = None, require_monotone: bool = False) -> dict:
    """Machine-readable promotion decision plus selected model parameters."""
    decision = calibration_gate(observations, fits, min_observations=min_observations, max_rmse=max_rmse, require_monotone=require_monotone)
    selected = min(fits, key=lambda r: r.score) if fits else None
    return {
        "eligible": decision.eligible,
        "round": decision.round_number,
        "family": decision.family,
        "reason": decision.reason,
        "metrics": decision.metrics,
        "selected_parameters": selected.parameters if selected else {},
    }
