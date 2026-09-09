import math

import numpy as np
import pytest

from gurobean.simulation import GurobeanSimulationConfig, _draw_order_size, simulate_gurobean


def test_zero_arrival_has_no_sales_and_exact_inventory_accounting():
    cfg = GurobeanSimulationConfig(hours=12, lambda_rate=0.0, p_hot=1.0, p_cold=0.0, mu_rate=30.0, brew_hot_per_hour=7.0, brew_cold_per_hour=0.0, brew_cost_hot=1.25, revenue_hot=4.0, seed=11)
    metrics, economics = simulate_gurobean(cfg)
    produced = 7.0 * 12
    assert metrics.arrivals == 0
    assert metrics.served == 0
    assert metrics.lost == 0
    assert economics["served_cups"] == 0
    assert math.isclose(economics["inventory_hot_end"], 0.0, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(economics["waste_hot"], produced, rel_tol=0.0, abs_tol=1e-12)
    assert math.isclose(economics["profit"], -produced * 1.25, rel_tol=0.0, abs_tol=1e-12)


def test_simulation_is_bitwise_reproducible_for_same_seed():
    cfg = GurobeanSimulationConfig(hours=24, lambda_rate=18.0, p_hot=0.65, p_cold=0.35, mu_rate=28.0, brew_hot_per_hour=15.0, brew_cold_per_hour=10.0, revenue_hot=4.0, revenue_cold=4.5, brew_cost_hot=0.7, brew_cost_cold=0.9, seed=12345)
    assert simulate_gurobean(cfg) == simulate_gurobean(cfg)


def test_simulation_metrics_obey_basic_bounds():
    cfg = GurobeanSimulationConfig(hours=48, lambda_rate=35.0, p_hot=0.7, p_cold=0.3, mu_rate=45.0, brew_hot_per_hour=40.0, brew_cold_per_hour=20.0, revenue_hot=5.0, revenue_cold=5.5, brew_cost_hot=1.0, brew_cost_cold=1.2, seed=2026)
    metrics, economics = simulate_gurobean(cfg)
    assert 0 <= metrics.served <= metrics.arrivals
    assert 0 <= metrics.lost <= metrics.arrivals
    assert 0 <= metrics.utilization <= 1
    assert metrics.mean_queue >= 0
    assert metrics.mean_wait >= 0
    assert economics["served_cups"] >= metrics.served
    assert economics["lost_customers"] >= metrics.lost
    assert all(np.isfinite(x) for x in (metrics.mean_queue, metrics.mean_wait, metrics.utilization, economics["profit"]))


def test_multicup_sampler_never_creates_zero_or_negative_orders():
    def bad_sampler(rng):
        return 0

    cfg = GurobeanSimulationConfig(hours=2, lambda_rate=1.0, mu_rate=20.0, p_hot=1.0, p_cold=0.0, order_size_sampler=bad_sampler)
    with pytest.raises(ValueError, match="order_size_sampler"):
        _draw_order_size(cfg, np.random.default_rng(0))
