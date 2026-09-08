import pytest

from gurobean import Scenario, solve_round


def test_r5_r8_are_not_silently_promoted():
    scenario = Scenario(
        lambda_total=50.0,
        p_hot=0.6,
        p_cold=0.4,
        revenue_hot=4.0,
        revenue_cold=5.0,
        cost_hot=1.0,
        cost_cold=1.2,
        beans_available=100.0,
        water_available=100.0,
        beans_hot=1.0,
        beans_cold=1.0,
        water_hot=1.0,
        water_cold=1.0,
    )
    for round_number in (5, 6, 7, 8):
        with pytest.raises(NotImplementedError, match=f"R{round_number}"):
            solve_round(round_number, scenario, backend="scipy")
