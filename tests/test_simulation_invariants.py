import math

import pytest

from gurobean.simulation import GurobeanSimulationConfig, simulate_gurobean


def base(**overrides):
    values = dict(
        hours=4,
        warmup_hours=0,
        seed=123,
        lambda_rate=20.0,
        p_hot=1.0,
        p_cold=0.0,
        mu_rate=40.0,
        brew_hot_per_hour=30.0,
        brew_cold_per_hour=0.0,
        revenue_hot=3.0,
        revenue_cold=3.0,
        brew_cost_hot=1.0,
        brew_cost_cold=1.0,
        barista_cost_per_hour=0.0,
    )
    values.update(overrides)
    return GurobeanSimulationConfig(**values)


def test_probability_mix_must_sum_to_one():
    with pytest.raises(ValueError):
        base(p_hot=0.8, p_cold=0.1)


def test_zero_arrivals_produce_no_customers_or_sales():
    metrics, economics = simulate_gurobean(base(lambda_rate=0.0))
    assert metrics.arrivals == 0
    assert metrics.served == 0
    assert metrics.lost == 0
    assert economics["served_cups"] == 0


def test_same_seed_is_bitwise_reproducible_at_result_level():
    a = simulate_gurobean(base(seed=77))
    b = simulate_gurobean(base(seed=77))
    assert a == b


def test_warmup_does_not_remove_profit_from_the_full_horizon():
    cold_metrics, cold_economics = simulate_gurobean(base(warmup_hours=0))
    warm_metrics, warm_economics = simulate_gurobean(base(warmup_hours=1))
    assert cold_economics["profit"] == warm_economics["profit"]
    assert warm_metrics.hours == cold_metrics.hours == 4
    assert math.isfinite(warm_metrics.mean_queue)


def test_service_utilization_is_bounded():
    metrics, _ = simulate_gurobean(base(lambda_rate=80.0, mu_rate=10.0))
    assert 0.0 <= metrics.utilization <= 1.0
