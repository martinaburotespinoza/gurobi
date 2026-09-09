import math

import pytest

from gurobean import Scenario
from gurobean.evaluation import evaluate_scenario
from gurobean.full_rounds import DynamicRoundParams, solve_dynamic_round


SCENARIO = Scenario(
    lambda_total=30.0,
    p_hot=0.7,
    p_cold=0.3,
    revenue_hot=3.0,
    revenue_cold=3.5,
    cost_hot=1.2,
    cost_cold=1.5,
    salvage_hot=0.0,
    salvage_cold=0.0,
    beans_available=80.0,
    water_available=80.0,
    beans_hot=1.0,
    beans_cold=1.0,
    water_hot=1.0,
    water_cold=1.0,
)


PARAMS = DynamicRoundParams(
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
    service_cost_fixed=1.0,
    service_cost_linear=1.0,
    service_cost_quadratic=0.1,
    hours=12,
    warmup_hours=0,
    replications=1,
    seed=123,
    coordinate_points=3,
)


@pytest.mark.parametrize("round_number", [5, 6, 7, 8])
def test_dynamic_solver_and_evaluator_are_identical_for_same_candidate(round_number: int):
    solved = solve_dynamic_round(SCENARIO, round_number, PARAMS)
    evaluated = evaluate_scenario(
        SCENARIO,
        markup=solved["markup"],
        q_hot=solved["Q_hot"],
        q_cold=solved["Q_cold"],
        service_rate=solved["service_rate"],
        replications=PARAMS.replications,
        seed=PARAMS.seed,
        hours=PARAMS.hours,
        warmup_hours=PARAMS.warmup_hours,
        barista_cost_per_hour=0.0,
        dynamic=PARAMS,
        round_number=round_number,
    )

    assert math.isfinite(solved["expected_profit"])
    assert evaluated.replications == PARAMS.replications
    assert evaluated.hours == PARAMS.hours
    assert evaluated.seed == PARAMS.seed
    assert evaluated.mean_profit == pytest.approx(solved["expected_profit"], abs=1e-9)
    assert evaluated.mean_served_customers == pytest.approx(solved["served_customers"], abs=1e-9)
    assert evaluated.mean_lost_customers == pytest.approx(solved["lost_customers"], abs=1e-9)
    assert evaluated.mean_queue == pytest.approx(solved["mean_queue"], abs=1e-12)
    assert evaluated.mean_wait_minutes == pytest.approx(solved["mean_wait_minutes"], abs=1e-12)
    assert evaluated.mean_utilization == pytest.approx(solved["utilization"], abs=1e-12)
