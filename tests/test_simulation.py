from gurobean.simulation import simulate_queue


def test_simulation_is_reproducible_and_bounded():
    a = simulate_queue(10, 15, hours=10, seed=7, warmup_hours=1)
    b = simulate_queue(10, 15, hours=10, seed=7, warmup_hours=1)
    assert a == b
    assert a.arrivals >= a.served
    assert a.lost == 0
    assert 0 <= a.mean_queue
    assert 0 <= a.mean_wait
    assert 0 <= a.utilization <= 1

from gurobean.simulation import GurobeanSimulationConfig, simulate_gurobean


def test_dynamic_simulation_reproducible_and_can_balk():
    cfg = GurobeanSimulationConfig(
        hours=8, warmup_hours=1, seed=11, lambda_rate=20, mu_rate=10,
        brew_hot_per_hour=40, p_hot=1.0,
        stay_probability=lambda q: 0.5,
    )
    a = simulate_gurobean(cfg)
    b = simulate_gurobean(cfg)
    assert a == b
    result, metrics = a
    assert result.arrivals >= result.served
    assert result.lost >= 0
    assert 0 <= result.utilization <= 1
    assert metrics["profit"] <= 40 * 8


def test_dynamic_simulation_supports_multicup_orders_and_inventory_loss():
    cfg = GurobeanSimulationConfig(
        hours=4, seed=3, lambda_rate=4, mu_rate=20,
        brew_hot_per_hour=2, p_hot=1.0,
        order_size_sampler=lambda rng: 2,
    )
    result, metrics = simulate_gurobean(cfg)
    assert metrics["served_cups"] >= result.served * 2
    assert result.lost >= 0
    assert metrics["inventory_hot_end"] >= 0
