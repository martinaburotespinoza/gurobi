import math

from gurobean import Scenario
from gurobean.evaluation import compare_summaries, evaluate_scenario
from gurobean.full_rounds import DynamicRoundParams, solve_dynamic_round


def test_evaluate_scenario_is_reproducible():
    sc = Scenario(lambda_total=10.0, p_hot=1.0, revenue_hot=3.0, cost_hot=1.0)
    a = evaluate_scenario(sc, markup=0.5, q_hot=12.0, q_cold=0.0, service_rate=20.0, replications=4, seed=77, hours=12)
    b = evaluate_scenario(sc, markup=0.5, q_hot=12.0, q_cold=0.0, service_rate=20.0, replications=4, seed=77, hours=12)
    assert a == b
    assert a.replications == 4
    assert a.hours == 12
    assert math.isfinite(a.mean_profit)
    assert a.profit_sd >= 0
    assert a.ci95_low <= a.mean_profit <= a.ci95_high


def test_dynamic_r7_evaluation_matches_solver_candidate():
    sc = Scenario(
        lambda_total=36.0,
        p_hot=0.7,
        p_cold=0.3,
        revenue_hot=4.5,
        revenue_cold=5.0,
        cost_hot=1.5,
        cost_cold=1.2,
        salvage_hot=0.3,
        salvage_cold=0.2,
        beans_available=1000.0,
        water_available=1000.0,
        beans_hot=10.0,
        beans_cold=10.0,
        water_hot=1.0,
        water_cold=1.0,
    )
    params = DynamicRoundParams(
        arrival_baseline_rate=60.0,
        arrival_reference_rate=36.0,
        reference_markup=1.0,
        balking_a=2.0,
        balking_b=-0.15,
        multi_cup_theta=1.0,
        service_rate_base=65.0,
        service_rate_min=50.0,
        service_rate_max=90.0,
        service_cost_fixed=0.0,
        service_cost_linear=4.0,
        service_cost_quadratic=0.0,
        hours=120,
        warmup_hours=0,
        replications=4,
        seed=42,
        coordinate_points=7,
    )
    solved = solve_dynamic_round(sc, 7, params)
    evaluated = evaluate_scenario(
        sc,
        markup=solved["markup"],
        q_hot=solved["Q_hot"],
        q_cold=solved["Q_cold"],
        service_rate=solved["service_rate"],
        replications=4,
        seed=42,
        hours=120,
        warmup_hours=0,
        dynamic=params,
        round_number=7,
    )
    assert math.isclose(evaluated.mean_profit, solved["expected_profit"], rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(evaluated.mean_queue, solved["mean_queue"], rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(evaluated.mean_wait_minutes, solved["mean_wait_minutes"], rel_tol=0.0, abs_tol=1e-9)


def test_compare_summaries_reports_delta_without_certification():
    sc = Scenario(lambda_total=10.0, p_hot=1.0, revenue_hot=3.0, cost_hot=1.0)
    candidate = evaluate_scenario(sc, markup=0.5, q_hot=12.0, q_cold=0.0, service_rate=20.0, replications=3, seed=10, hours=8)
    reference = evaluate_scenario(sc, markup=0.5, q_hot=10.0, q_cold=0.0, service_rate=20.0, replications=3, seed=10, hours=8)
    comparison = compare_summaries(candidate, reference)
    assert math.isclose(comparison["profit_delta"], candidate.mean_profit - reference.mean_profit)
    assert comparison["formal_game_certified"] is False
