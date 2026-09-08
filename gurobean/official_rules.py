from __future__ import annotations

"""Authoritative game-rule relationships explicitly published by Gurobi.

This module is deliberately separate from the optimization model. A published
relationship may be evaluated here without claiming that the full round is
certified. Round promotion still requires the evidence gate and the complete
set of scenario parameters.
"""

from math import exp, isfinite, log


def arrival_rate_from_markup(
    markup: float,
    baseline_rate: float,
    reference_rate: float,
    reference_markup: float,
) -> float:
    """Evaluate Gurobi's published R5 markup-to-arrival relationship.

    The Gurobean technical teaching deck publishes:

        lambda(m) = lambda_bar * exp(a*m/m0)
        a = ln(lambda_0 / lambda_bar)

    Thus ``baseline_rate`` is lambda_bar, ``reference_rate`` is lambda_0,
    and ``reference_markup`` is m0. Consequently lambda(0)=lambda_bar and
    lambda(m0)=lambda_0.

    This is a rule evaluator, not an R5 certification claim. The actual game
    scenario must supply the corresponding parameter values.
    """
    values = {
        "markup": markup,
        "baseline_rate": baseline_rate,
        "reference_rate": reference_rate,
        "reference_markup": reference_markup,
    }
    if any(not isfinite(value) for value in values.values()):
        raise ValueError("R5 parameters must be finite")
    if markup < 0:
        raise ValueError("markup must be >= 0")
    if baseline_rate <= 0 or reference_rate <= 0:
        raise ValueError("arrival rates must be > 0")
    if reference_markup <= 0:
        raise ValueError("reference_markup must be > 0")

    a = log(reference_rate / baseline_rate)
    exponent = a * markup / reference_markup
    return baseline_rate * exp(exponent)


def validate_r5_anchor_points(
    baseline_rate: float,
    reference_rate: float,
    reference_markup: float,
    tolerance: float = 1e-12,
) -> None:
    """Verify the two defining anchors of the published R5 relationship."""
    if tolerance < 0 or not isfinite(tolerance):
        raise ValueError("tolerance must be finite and >= 0")
    at_zero = arrival_rate_from_markup(
        0.0, baseline_rate, reference_rate, reference_markup
    )
    at_reference = arrival_rate_from_markup(
        reference_markup, baseline_rate, reference_rate, reference_markup
    )
    if abs(at_zero - baseline_rate) > tolerance * max(1.0, baseline_rate):
        raise AssertionError("R5 baseline anchor is inconsistent")
    if abs(at_reference - reference_rate) > tolerance * max(1.0, reference_rate):
        raise AssertionError("R5 reference anchor is inconsistent")
