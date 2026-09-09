import numpy as np
import pytest

from gurobean.full_rounds import DynamicRoundParams, solve_dynamic_round
from gurobean.model import Scenario, expected_newsvendor_profit
from gurobean.simulation import GurobeanSimulationConfig, _draw_order_size, simulate_gurobean


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


def _dynamic_params():
    return DynamicRoundParams(
        arrival_baseline_rate=20.0,
        arrival_reference_rate=10.0,
        reference_markup=1.0,
        hours=2,
        replications=1,
        coordinate_points=3,
        seed=11,
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


def test_invalid_order_sampler_is_rejected_at_draw_time():
    cfg = GurobeanSimulationConfig(
        hours=1, seed=1, lambda_rate=0.0, p_hot=1.0, p_cold=0.0,
        mu_rate=30.0, brew_hot_per_hour=10.0,
        order_size_sampler=lambda _rng: 0,
    )
    with pytest.raises(ValueError, match="order_size_sampler"):
        _draw_order_size(cfg, np.random.default_rng(cfg.seed))


def test_dynamic_round_returns_resource_feasible_decision():
    sc = _scenario()
    result = solve_dynamic_round(sc, 8, _dynamic_params())
    assert result["Q_hot"] >= 0
    assert result["Q_cold"] >= 0
    assert sc.beans_hot * result["Q_hot"] + sc.beans_cold * result["Q_cold"] <= sc.beans_available + 1e-9
    assert sc.water_hot * result["Q_hot"] + sc.water_cold * result["Q_cold"] <= sc.water_available + 1e-9
    assert result["objective"] == result["expected_profit"]


@pytest.mark.parametrize("field", [
    "lambda_total", "revenue_hot", "revenue_cold", "cost_hot", "cost_cold",
    "salvage_hot", "salvage_cold", "beans_hot", "beans_cold", "water_hot", "water_cold",
])
def test_scenario_rejects_non_finite_economic_inputs(field):
    values = _scenario().__dict__.copy()
    values[field] = np.nan
    with pytest.raises(ValueError, match=field):
        Scenario(**values)


def test_scenario_allows_infinite_resource_availability_but_not_nan():
    sc = _scenario()
    Scenario(**{**sc.__dict__, "beans_available": np.inf, "water_available": np.inf})
    with pytest.raises(ValueError, match="beans_available"):
        Scenario(**{**sc.__dict__, "beans_available": np.nan})


def test_zero_demand_profit_is_exactly_zero():
    assert expected_newsvendor_profit(0.0, 0.0, 10.0, 2.0, 1.0) == 0.0
