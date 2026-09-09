from __future__ import annotations

"""Strict evidence gate for promoting calibrated R5-R8 behavior.

A fitted response is never sufficient by itself. Promotion requires observations
whose provenance is explicitly the real game. Synthetic, generated, demo, or
unspecified provenance is rejected before statistical calibration runs.

The strict gate also performs a deterministic holdout validation. This prevents
an in-sample fit from being treated as production evidence merely because its
training RMSE is small. A quantitative out-of-sample threshold is mandatory for
promotion; the gate never invents an acceptable error level for the caller.
"""

from typing import Sequence

import numpy as np

from .calibration import (
    FitResult,
    Observation,
    PromotionDecision,
    calibration_gate,
    fit_r5_arrival_rate,
    fit_r6_balking,
    fit_r7_order_size,
    fit_r8_service_cost,
)

ALLOWED_GAME_SOURCES = frozenset({"game", "game_capture", "game_observation"})


def _fit_for_round(observations: Sequence[Observation], round_number: int) -> list[FitResult]:
    if round_number == 5:
        return fit_r5_arrival_rate(observations)
    if round_number == 6:
        return fit_r6_balking(observations)
    if round_number == 7:
        return fit_r7_order_size(observations)
    if round_number == 8:
        return fit_r8_service_cost(observations)
    raise ValueError(f"unsupported calibration round: {round_number}")


def _predict(fit: FitResult, observation: Observation) -> float:
    p = fit.parameters
    if fit.round_number == 5:
        x = float(observation.variables["markup"])
        if fit.family == "linear":
            return max(0.0, p["a"] + p["b"] * x)
        return max(0.0, p["a"] * np.exp(-p["b"] * x))
    if fit.round_number == 6:
        x_key = "queue" if "queue" in observation.variables else "wait_minutes"
        eta = np.clip(p["a"] + p["b"] * float(observation.variables[x_key]), -40.0, 40.0)
        return float(1.0 / (1.0 + np.exp(-eta)))
    if fit.round_number == 7:
        if fit.family == "shifted_poisson":
            return 1.0 + max(0.0, p["theta"])
        prob = min(max(p["p"], 1e-12), 1.0 - 1e-12)
        return 1.0 / prob
    if fit.round_number == 8:
        x = float(observation.variables["service_rate"])
        if fit.family == "linear":
            return max(0.0, p["a"] + p["b"] * x)
        return max(0.0, p["a"] + p["b"] * x + p["c"] * x * x)
    raise ValueError(f"unsupported calibration round: {fit.round_number}")


def _held_out_rmse(observations: Sequence[Observation], round_number: int) -> tuple[float, str]:
    """Fit on the deterministic training prefix and score the held-out suffix."""
    n = len(observations)
    if n < 8:
        raise ValueError("at least 8 observations are required for out-of-sample validation")
    split = max(6, int(np.floor(0.75 * n)))
    if split >= n:
        split = n - 2
    train = list(observations[:split])
    test = list(observations[split:])
    fits = _fit_for_round(train, round_number)
    best = min(fits, key=lambda r: r.score)

    y = []
    yhat = []
    for obs in test:
        if round_number == 5:
            target = float(obs.outputs["arrival_rate"])
        elif round_number == 6:
            target = float(obs.outputs["stay_probability"])
        elif round_number == 7:
            target = float(obs.outputs["order_size"])
        else:
            target = float(obs.outputs["barista_cost_per_hour"])
        prediction = float(_predict(best, obs))
        if not np.isfinite(target) or not np.isfinite(prediction):
            raise ValueError("out-of-sample validation produced a non-finite value")
        y.append(target)
        yhat.append(prediction)
    rmse = float(np.sqrt(np.mean((np.asarray(y) - np.asarray(yhat)) ** 2)))
    return rmse, best.family


def strict_calibration_gate(
    observations: Sequence[Observation],
    results: Sequence[FitResult],
    *,
    min_observations: int = 8,
    max_rmse: float | None = None,
    require_monotone: bool = False,
    require_out_of_sample: bool = True,
) -> PromotionDecision:
    """Apply provenance, statistical and deterministic holdout validation.

    ``max_rmse`` is mandatory whenever out-of-sample validation is required.
    This makes promotion reproducible and prevents an unspecified/floating
    statistical acceptance criterion from being interpreted as certification.
    """
    if not observations:
        return PromotionDecision(False, 0, None, "no_observations", {})

    rounds = {o.round_number for o in observations}
    if len(rounds) != 1 or next(iter(rounds)) not in (5, 6, 7, 8):
        return PromotionDecision(False, 0, None, "mixed_or_invalid_rounds", {})

    round_number = next(iter(rounds))
    invalid_sources = sorted({o.source for o in observations if o.source not in ALLOWED_GAME_SOURCES})
    if invalid_sources:
        return PromotionDecision(
            False,
            round_number,
            None,
            "non_game_observation_source",
            {"invalid_source_count": float(len(invalid_sources))},
        )

    if not results or any(r.round_number != round_number for r in results):
        return PromotionDecision(False, round_number, None, "fit_round_mismatch", {})

    if require_out_of_sample:
        if max_rmse is None:
            return PromotionDecision(False, round_number, None, "missing_oos_rmse_threshold", {})
        if not np.isfinite(float(max_rmse)) or float(max_rmse) < 0:
            return PromotionDecision(False, round_number, None, "invalid_oos_rmse_threshold", {})

    base = calibration_gate(
        observations,
        results,
        min_observations=min_observations,
        max_rmse=max_rmse,
        require_monotone=require_monotone,
    )
    if not base.eligible:
        return base

    metrics = dict(base.metrics)
    if require_out_of_sample:
        try:
            oos_rmse, oos_family = _held_out_rmse(observations, round_number)
        except (KeyError, TypeError, ValueError) as exc:
            return PromotionDecision(False, round_number, base.family, "out_of_sample_validation_failed", {**metrics, "validation_error": str(exc)})
        metrics["out_of_sample_rmse"] = oos_rmse
        metrics["out_of_sample_family"] = oos_family
        if not np.isfinite(oos_rmse):
            return PromotionDecision(False, round_number, base.family, "out_of_sample_non_finite", metrics)
        if oos_rmse > float(max_rmse):
            return PromotionDecision(False, round_number, base.family, "out_of_sample_rmse_exceeded", metrics)

    return PromotionDecision(True, round_number, base.family, "promotion_gate_passed", metrics)
