import math

from gurobean.model import _economic_unconstrained_q, expected_newsvendor_gradient


def test_extreme_positive_critical_fractile_does_not_clip_to_z_minus_10():
    lam = 80.0
    revenue = 1.0
    cost = 1.0 - 1e-16
    salvage = 0.0

    q = _economic_unconstrained_q(lam, revenue, cost, salvage)
    assert q > 0.0
    assert math.isfinite(q)
    assert expected_newsvendor_gradient(q, lam, revenue, cost, salvage) <= 1e-12


def test_normal_quantile_solution_is_stationary_for_high_demand():
    lam = 80.0
    revenue = 1.0
    cost = 1.0 - 1e-12
    salvage = 0.0

    q = _economic_unconstrained_q(lam, revenue, cost, salvage)
    assert q > 0.0
    assert abs(expected_newsvendor_gradient(q, lam, revenue, cost, salvage)) <= 1e-12
