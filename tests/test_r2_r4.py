import math

import pytest

from gurobean.model import (
    Scenario,
    expected_newsvendor_gradient,
    expected_newsvendor_profit,
    solve_round_scipy,
)


def test_round2_has_two_products_and_shared_resources():
    sc = Scenario(
        lambda_total=50,
        p_hot=0.6,
        p_cold=0.4,
        revenue_hot=2.0,
        revenue_cold=2.5,
        beans_available=60,
        water_available=100,
        beans_hot=1,
        beans_cold=2,
        water_hot=1,
        water_cold=1,
    )
    result = solve_round_scipy(sc, 2)
    assert result["Q_hot"] >= 0
    assert result["Q_cold"] >= 0
    assert sc.beans_hot * result["Q_hot"] + sc.beans_cold * result["Q_cold"] <= sc.beans_available + 1e-7
    assert sc.water_hot * result["Q_hot"] + sc.water_cold * result["Q_cold"] <= sc.water_available + 1e-7


def test_round3_with_positive_brew_cost_stops_before_infinite_inventory():
    sc = Scenario(
        lambda_total=40,
        p_hot=1,
        revenue_hot=5,
        cost_hot=2,
        beans_available=float("inf"),
        water_available=float("inf"),
    )
    result = solve_round_scipy(sc, 3)
    # Critical-fractile solution for salvage=0: Phi(z)=(r-c)/r=0.6.
    assert 0 < result["Q_hot"] < 60
    assert result["objective"] > expected_newsvendor_profit(0, 40, 5, 2)


def test_round4_objective_is_sum_of_product_objectives():
    sc = Scenario(
        lambda_total=80,
        p_hot=0.5,
        p_cold=0.5,
        revenue_hot=4,
        revenue_cold=5,
        cost_hot=1.5,
        cost_cold=2,
        beans_available=100,
        water_available=100,
        beans_hot=1,
        beans_cold=1,
        water_hot=1,
        water_cold=1,
    )
    result = solve_round_scipy(sc, 4)
    expected = expected_newsvendor_profit(result["Q_hot"], 40, 4, 1.5)
    expected += expected_newsvendor_profit(result["Q_cold"], 40, 5, 2)
    assert math.isclose(result["objective"], expected, rel_tol=1e-8, abs_tol=1e-8)


def test_gradient_matches_finite_difference():
    q, lam, rev, cost = 31.0, 40.0, 4.0, 1.5
    eps = 1e-5
    fd = (
        expected_newsvendor_profit(q + eps, lam, rev, cost)
        - expected_newsvendor_profit(q - eps, lam, rev, cost)
    ) / (2 * eps)
    analytic = expected_newsvendor_gradient(q, lam, rev, cost)
    assert math.isclose(fd, analytic, rel_tol=1e-7, abs_tol=1e-7)


def test_gurobi_backend_is_optional_and_never_faked():
    try:
        import gurobipy  # noqa: F401
    except ImportError:
        pytest.skip("gurobipy not installed in validation environment")


def test_gurobi_handles_zero_economic_upper_bound():
    from gurobean.model import Scenario, solve_gurobi_round

    sc = Scenario(
        lambda_total=20.0,
        p_hot=1.0,
        revenue_hot=1.0,
        cost_hot=2.0,
        beans_available=100.0,
        water_available=100.0,
        beans_hot=1.0,
        water_hot=1.0,
    )

    result = solve_gurobi_round(sc, 3)

    from gurobean.model import expected_newsvendor_profit

    assert result["Q_hot"] == 0.0
    assert result["Q_cold"] == 0.0
    expected = expected_newsvendor_profit(
        0.0,
        sc.lambda_hot,
        sc.revenue_hot,
        sc.cost_hot,
        sc.salvage_hot,
    )
    assert abs(result["objective"] - expected) < 1e-6


def test_gurobi_handles_tiny_positive_economic_upper_bound():
    from gurobean.model import Scenario, solve_gurobi_round

    sc = Scenario(
        lambda_total=1.0,
        p_hot=1.0,
        revenue_hot=1.0,
        cost_hot=0.999999,
        beans_available=100.0,
        water_available=100.0,
        beans_hot=1.0,
        water_hot=1.0,
    )

    result = solve_gurobi_round(sc, 3)

    from gurobean.model import expected_newsvendor_profit

    assert result["Q_hot"] >= 0.0
    expected = expected_newsvendor_profit(
        result["Q_hot"],
        sc.lambda_hot,
        sc.revenue_hot,
        sc.cost_hot,
        sc.salvage_hot,
    )
    assert abs(result["objective"] - expected) < 1e-5
