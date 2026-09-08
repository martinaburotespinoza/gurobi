"""Deterministic load/robustness battery for the dynamic R5-R8 simulator.

This battery is intentionally lightweight enough for CI while exercising the
same 120-hour horizon used by the evaluation protocol. It is not game-parity
evidence; it is a software robustness gate against non-finite outputs,
resource violations, invalid metrics and loss of reproducibility.
"""

import math

from gurobean import Scenario
from gurobean.full_rounds import DynamicRoundParams, solve_dynamic_round


def _scenario(lambda_total: float, hot: float, cold: float) -> Scenario:
    return Scenario(
        lambda_total=lambda_total,
        p_hot=hot,
        p_cold=cold,
        revenue_hot=3.0,
        revenue_cold=3.5,
        cost_hot=1.2,
        cost_cold=1.5,
        beans_available=160.0,
        water_available=160.0,
        beans_hot=1.0,
        beans_cold=1.0,
        water_hot=1.0,
        water_cold=1.0,
    )


def _params(seed: int) -> DynamicRoundParams:
    return DynamicRoundParams(
        arrival_baseline_rate=36.0,
        arrival_reference_rate=20.0,
        reference_markup=1.0,
        markup_min=0.0,
        markup_max=3.0,
        balking_a=2.0,
        balking_b=-0.15,
        multi_cup_theta=0.75,
        service_rate_base=55.0,
        service_rate_min=40.0,
        service_rate_max=80.0,
        service_cost_linear=0.8,
        service_cost_quadratic=0.02,
        hours=120,
        warmup_hours=0,
        replications=2,
        seed=seed,
        coordinate_points=3,
    )


def test_120h_r5_r8_load_battery_is_finite_and_reproducible():
    scenarios = (
        _scenario(8.0, 0.5, 0.5),
        _scenario(20.0, 0.7, 0.3),
        _scenario(36.0, 0.2, 0.8),
    )
    for index, sc in enumerate(scenarios):
        for round_number in range(5, 9):
            p = _params(1000 + index * 100 + round_number)
            first = solve_dynamic_round(sc, round_number, p)
            second = solve_dynamic_round(sc, round_number, p)
            assert first == second
            assert first["operational"] is True
            assert first["formal_game_certified"] is False
            for key in ("objective", "Q_hot", "Q_cold", "markup", "service_rate"):
                assert math.isfinite(float(first[key]))
            for key in ("mean_queue", "mean_wait_minutes", "utilization"):
                assert math.isfinite(float(first[key]))
                assert float(first[key]) >= 0.0
            assert 0.0 <= float(first["utilization"]) <= 1.0 + 1e-12
            assert first["Q_hot"] >= 0.0
            assert first["Q_cold"] >= 0.0
            assert first["markup"] >= 0.0
            assert first["service_rate"] > 0.0


def test_120h_r8_load_battery_exercises_service_cost():
    sc = _scenario(28.0, 0.6, 0.4)
    p = _params(4242)
    result = solve_dynamic_round(sc, 8, p)
    assert result["simulation_hours"] == 120
    assert result["service_cost_per_hour"] >= 0.0
    assert math.isfinite(float(result["service_cost_per_hour"]))
