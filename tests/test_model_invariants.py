import math
import numpy as np
import pytest

from gurobean.model import (
    Scenario,
    expected_newsvendor_gradient,
    expected_newsvendor_profit,
    solve_round1_closed_form,
    solve_round_scipy,
)


def test_newsvendor_gradient_matches_finite_difference():
    q, lam, rev, cost, salvage = 31.0, 28.0, 4.0, 1.2, 0.2
    h = 1e-5
    numeric = (expected_newsvendor_profit(q+h, lam, rev, cost, salvage) - expected_newsvendor_profit(q-h, lam, rev, cost, salvage)) / (2*h)
    assert math.isclose(expected_newsvendor_gradient(q, lam, rev, cost, salvage), numeric, rel_tol=1e-7, abs_tol=1e-7)


def test_newsvendor_objective_is_concave_on_positive_lambda():
    lam, rev, cost, salvage = 37.0, 5.0, 1.3, 0.4
    qs = np.linspace(0.0, 90.0, 181)
    gradients = np.array([expected_newsvendor_gradient(float(q), lam, rev, cost, salvage) for q in qs])
    # The derivative of a concave function is non-increasing.
    assert np.all(np.diff(gradients) <= 1e-10)
    # With positive revenue margin, curvature is strictly negative away from numerical tails.
    assert gradients[20] > gradients[120]


def test_newsvendor_stationary_point_matches_critical_fractile():
    lam, rev, cost, salvage = 64.0, 6.0, 1.5, 0.5
    critical = (rev - cost) / (rev - salvage)
    expected_q = lam + math.sqrt(lam) * __import__("statistics").NormalDist().inv_cdf(critical)
    q = expected_q
    assert abs(expected_newsvendor_gradient(q, lam, rev, cost, salvage)) < 1e-10


def test_newsvendor_gradient_monotone_and_boundary_signs():
    lam, rev, cost, salvage = 25.0, 4.0, 1.0, 0.0
    assert expected_newsvendor_gradient(0.0, lam, rev, cost, salvage) > 0.0
    assert expected_newsvendor_gradient(100.0, lam, rev, cost, salvage) < 0.0
    assert expected_newsvendor_gradient(0.0, lam, rev, cost, salvage) >= expected_newsvendor_gradient(100.0, lam, rev, cost, salvage)


def test_lambda_zero_has_exact_linear_economics():
    assert expected_newsvendor_profit(12.0, 0.0, 4.0, 1.5, 0.25) == 12.0 * (0.25 - 1.5)
    assert expected_newsvendor_gradient(12.0, 0.0, 4.0, 1.5, 0.25) == 0.25 - 1.5
    assert expected_newsvendor_profit(12.0, 0.0, 4.0, 1.5, 2.0) == 12.0 * (2.0 - 1.5)


def test_round1_closed_form_matches_reference_objective():
    sc = Scenario(
        lambda_total=42.0,
        revenue_hot=4.0,
        cost_hot=0.0,
        salvage_hot=0.25,
        beans_available=100.0,
        beans_hot=1.0,
        water_available=100.0,
        water_hot=1.0,
    )
    closed = solve_round1_closed_form(sc)
    reference = solve_round_scipy(sc, 1)
    assert math.isclose(closed["objective"], reference["objective"], rel_tol=1e-8, abs_tol=1e-8)
    assert math.isclose(closed["Q_hot"], reference["Q_hot"], rel_tol=1e-6, abs_tol=1e-6)


def test_resource_constraints_are_respected_r2_r4():
    for round_number in (2, 4):
        sc = Scenario(lambda_total=60, p_hot=.6, p_cold=.4, revenue_hot=4, revenue_cold=5,
                      cost_hot=.8, cost_cold=1.1, beans_available=40, water_available=50,
                      beans_hot=1.0, beans_cold=1.5, water_hot=1.0, water_cold=2.0)
        sol = solve_round_scipy(sc, round_number)
        assert sol['Q_hot'] >= -1e-8 and sol['Q_cold'] >= -1e-8
        assert sc.beans_hot*sol['Q_hot'] + sc.beans_cold*sol['Q_cold'] <= sc.beans_available + 1e-6
        assert sc.water_hot*sol['Q_hot'] + sc.water_cold*sol['Q_cold'] <= sc.water_available + 1e-6


def test_zero_economic_margin_returns_exact_zero():
    sc = Scenario(lambda_total=10, revenue_hot=3, cost_hot=3, beans_available=100, beans_hot=1, water_available=100, water_hot=1)
    sol = solve_round_scipy(sc, 3)
    assert sol['Q_hot'] == 0.0
    assert sol['objective'] == 0.0


def test_invalid_negative_scenario_is_rejected():
    with pytest.raises(ValueError):
        Scenario(lambda_total=-1)
    with pytest.raises(ValueError):
        Scenario(lambda_total=1, p_hot=.8, p_cold=.3)
    with pytest.raises(ValueError):
        Scenario(lambda_total=1, p_hot=.7, p_cold=.2)


def test_r4_optimizer_handles_tight_coupled_resource_case():
    sc = Scenario(
        lambda_total=74.450445976897, p_hot=0.71892429678667, p_cold=0.28107570321333,
        revenue_hot=1.9771673811980053, revenue_cold=1.6297898743755597,
        cost_hot=1.1274313878795992, cost_cold=0.21771253559845877,
        beans_available=54.54888236324721, water_available=55.3262942954221,
        beans_hot=1.2202893410203626, beans_cold=1.7468284207283398,
        water_hot=1.4804218888528107, water_cold=0.735841964262733,
    )
    sol = solve_round_scipy(sc, 4)
    assert np.isfinite(sol["objective"])
    assert sc.beans_hot * sol["Q_hot"] + sc.beans_cold * sol["Q_cold"] <= sc.beans_available + 1e-6
    assert sc.water_hot * sol["Q_hot"] + sc.water_cold * sol["Q_cold"] <= sc.water_available + 1e-6
