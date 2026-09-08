import math

from gurobean import Scenario
from gurobean.full_rounds import DynamicRoundParams, solve_dynamic_round


def scenario() -> Scenario:
    return Scenario(
        lambda_total=30.0,
        p_hot=0.7,
        p_cold=0.3,
        revenue_hot=3.0,
        revenue_cold=3.5,
        cost_hot=1.2,
        cost_cold=1.5,
        beans_available=80.0,
        water_available=80.0,
        beans_hot=1.0,
        beans_cold=1.0,
        water_hot=1.0,
        water_cold=1.0,
    )


def params() -> DynamicRoundParams:
    return DynamicRoundParams(
        arrival_baseline_rate=30.0,
        arrival_reference_rate=18.0,
        reference_markup=1.0,
        markup_min=0.0,
        markup_max=3.0,
        balking_a=2.0,
        balking_b=-0.15,
        multi_cup_theta=0.5,
        service_rate_base=45.0,
        service_rate_min=35.0,
        service_rate_max=60.0,
        service_cost_linear=1.0,
        hours=12,
        warmup_hours=0,
        replications=1,
        seed=123,
        coordinate_points=3,
    )


def test_r5_r8_are_executable_and_finite():
    sc = scenario()
    for round_number in range(5, 9):
        result = solve_dynamic_round(sc, round_number, params())
        assert result["operational"] is True
        assert result["formal_game_certified"] is False
        assert math.isfinite(result["objective"])
        assert result["Q_hot"] >= 0
        assert result["Q_cold"] >= 0
        assert result["markup"] >= 0
        assert result["service_rate"] > 0


def test_r5_markup_changes_arrival_rate():
    p = params()
    assert p.arrival_rate(0.0) > p.arrival_rate(1.0)


def test_r6_stay_probability_decreases_with_queue():
    p = params()
    assert p.stay_probability(10.0) < p.stay_probability(0.0)


def test_r7_order_sampler_parameter_is_nonnegative():
    assert params().multi_cup_theta >= 0


def test_r8_service_cost_is_monotone_under_positive_linear_cost():
    p = params()
    assert p.service_cost(60.0) >= p.service_cost(45.0)
