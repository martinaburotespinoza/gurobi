import math
import numpy as np
import pytest

from gurobean.model import Scenario, expected_newsvendor_gradient, expected_newsvendor_profit, solve_round_scipy


def test_newsvendor_gradient_matches_finite_difference():
    q, lam, rev, cost, salvage = 31.0, 28.0, 4.0, 1.2, 0.2
    h = 1e-5
    numeric = (expected_newsvendor_profit(q+h, lam, rev, cost, salvage) - expected_newsvendor_profit(q-h, lam, rev, cost, salvage)) / (2*h)
    assert math.isclose(expected_newsvendor_gradient(q, lam, rev, cost, salvage), numeric, rel_tol=1e-7, abs_tol=1e-7)


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
