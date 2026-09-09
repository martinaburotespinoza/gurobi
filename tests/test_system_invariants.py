import numpy as np
import pytest

from gurobean.full_rounds import DynamicRoundParams, solve_dynamic_round
from gurobean.model import Scenario
from gurobean.simulation import GurobeanSimulationConfig, simulate_gurobean


def _scenario():
    return Scenario(
        lambda_total=20.0,
        p_hot=0.7,
        p_cold=0.3,
        revenue_hot=5.0,
        revenue_cold=4.0,
        cost_hot=2.0,
        cost_cold=1.5,
        beans_available=100.0,
        water_available=100.0,
        beans_hot=1.0,
        beans_cold=1.0,
        water_hot=1.0,
        water_cold=1.0,
    )


def test_simulation_is_bitwise_reproducible_for_same_seed():
    cfg = GurobeanSimulationConfig(
        hours=4, seed=123, lambda_rate=12.0, p_hot=0.7, p_cold=0.3,
        mu_rate=30.0, brew_hot_per_hour=20.0, brew_cold_per_hour=20.0,
        revenue_hot=5.0, revenue_cold=4.0,
    )
    a = simulate_gurobean(cfg)
    b = simulate_gurobean(cfg)
    assert a == b


def test_zero_arrivals_produce_no_customers_and_finite_economics():
    cfg = GurobeanSimulationConfig(
        hours=2, seed=7, lambda_rate=0.0, p_hot=1.0, p_cold=0.0,
        mu_rate=30.0, brew_hot_per_hour=10.0, revenue_hot=5.0,
    )
    metrics, economics = simulate_gurobean(cfg)
    assert metrics.arrivals == 0
    assert metrics.served == 0
    assert metrics.lost == 0
    assert economics["served_cups"] == 0
    assert np.isfinite(economics["profit"])


def test_invalid_order_sampler_cannot_silently_create_zero_cup_orders():
    cfg = GurobeanSimulationConfig(
        hours=1, seed=1, lambda_rate=1.0, p_hot=1.0, p_cold=0.0,
        mu_rate=30.0, brew_hot_per_hour=10.0,
        order_size_sampler=lambda _rng: 0,
    )
    with pytest.raises(ValueError, match="order_size_sampler"):
        simulate_gurobean(cfg)


def test_dynamic_round_returns_resource_feasible_decision():
    result = solve_dynamic_round(
        _scenario(),
        8,
        DynamicRoundParams(hours=2, replications=1, coordinate_points=3, seed=11),
    )
    assert result["Q_hot"] >= 0
    assert result["Q_cold"] >= 0
    assert _scenario().beans_hot * result["Q_hot"] + _scenario().beans_cold * result["Q_cold"] <= _scenario().beans_available + 1e-9
    assert _scenario().water_hot * result["Q_hot"] + _scenario().water_cold * result["Q_cold"] <= _scenario().water_available + 1e-9
    assert result["objective"] == result["expected_profit"]
