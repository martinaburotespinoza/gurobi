import math

from gurobean import Scenario
from gurobean.evaluation import compare_summaries, evaluate_scenario


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


def test_compare_summaries_reports_delta_without_certification():
    sc = Scenario(lambda_total=10.0, p_hot=1.0, revenue_hot=3.0, cost_hot=1.0)
    candidate = evaluate_scenario(sc, markup=0.5, q_hot=12.0, q_cold=0.0, service_rate=20.0, replications=3, seed=10, hours=8)
    reference = evaluate_scenario(sc, markup=0.5, q_hot=10.0, q_cold=0.0, service_rate=20.0, replications=3, seed=10, hours=8)
    comparison = compare_summaries(candidate, reference)
    assert math.isclose(comparison["profit_delta"], candidate.mean_profit - reference.mean_profit)
    assert comparison["formal_game_certified"] is False
