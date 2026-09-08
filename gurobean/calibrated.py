from __future__ import annotations

"""Runtime evaluators for promoted calibration models.

These functions only consume fitted parameters; they never infer game rules on
their own. Promotion remains the responsibility of the evidence gate.
"""

from math import exp, lgamma, log
from .calibration import FitResult


def evaluate_r5(fit: FitResult, markup: float) -> float:
    if fit.round_number != 5:
        raise ValueError("expected an R5 fit")
    if markup < 0:
        raise ValueError("markup must be >= 0")
    if fit.family == "linear":
        return max(0.0, fit.parameters["a"] + fit.parameters["b"] * markup)
    if fit.family == "exponential":
        return max(0.0, fit.parameters["a"] * exp(-fit.parameters["b"] * markup))
    raise ValueError(f"unsupported R5 family: {fit.family}")


def evaluate_r6(fit: FitResult, queue_or_wait: float) -> float:
    if fit.round_number != 6:
        raise ValueError("expected an R6 fit")
    if queue_or_wait < 0:
        raise ValueError("queue_or_wait must be >= 0")
    if fit.family != "logistic":
        raise ValueError(f"unsupported R6 family: {fit.family}")
    eta = max(-40.0, min(40.0, fit.parameters["a"] + fit.parameters["b"] * queue_or_wait))
    return 1.0 / (1.0 + exp(-eta))


def evaluate_r7(fit: FitResult, order_size: int) -> float:
    """Return PMF for the promoted R7 distribution."""
    if fit.round_number != 7 or order_size < 1:
        raise ValueError("expected an R7 fit and order_size >= 1")
    k = order_size - 1
    if fit.family == "shifted_poisson":
        theta = fit.parameters["theta"]
        return exp(-theta + (k * log(theta) if k else 0.0) - lgamma(k + 1)) if theta > 0 else (1.0 if k == 0 else 0.0)
    if fit.family == "geometric":
        p = fit.parameters["p"]
        return p * (1.0 - p) ** k
    raise ValueError(f"unsupported R7 family: {fit.family}")


def evaluate_r8(fit: FitResult, service_rate: float) -> float:
    if fit.round_number != 8:
        raise ValueError("expected an R8 fit")
    if service_rate < 0:
        raise ValueError("service_rate must be >= 0")
    if fit.family == "linear":
        return fit.parameters["a"] + fit.parameters["b"] * service_rate
    if fit.family == "quadratic":
        return fit.parameters["a"] + fit.parameters["b"] * service_rate + fit.parameters["c"] * service_rate * service_rate
    raise ValueError(f"unsupported R8 family: {fit.family}")
