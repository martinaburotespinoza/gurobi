import math

import numpy as np

from gurobean.model import Scenario, expected_newsvendor_gradient, solve_round_scipy


def _random_scenario(rng: np.random.Generator) -> Scenario:
    p_hot = float(rng.uniform(0.15, 0.85))
    p_cold = 1.0 - p_hot
    return Scenario(
        lambda_total=float(rng.uniform(15.0, 100.0)),
        p_hot=p_hot,
        p_cold=p_cold,
        revenue_hot=float(rng.uniform(2.0, 7.0)),
        revenue_cold=float(rng.uniform(2.0, 7.0)),
        cost_hot=float(rng.uniform(0.0, 1.8)),
        cost_cold=float(rng.uniform(0.0, 1.8)),
        salvage_hot=float(rng.uniform(0.0, 0.5)),
        salvage_cold=float(rng.uniform(0.0, 0.5)),
        beans_available=float(rng.uniform(25.0, 90.0)),
        water_available=float(rng.uniform(25.0, 90.0)),
        beans_hot=float(rng.uniform(0.4, 2.0)),
        beans_cold=float(rng.uniform(0.4, 2.0)),
        water_hot=float(rng.uniform(0.4, 2.0)),
        water_cold=float(rng.uniform(0.4, 2.0)),
    )


def _resource_caps(sc: Scenario) -> tuple[float, float]:
    hot = min(sc.beans_available / sc.beans_hot, sc.water_available / sc.water_hot)
    cold = min(sc.beans_available / sc.beans_cold, sc.water_available / sc.water_cold)
    return hot, cold


def _objective(sc: Scenario, qh: float, qc: float) -> float:
    from gurobean.model import expected_newsvendor_profit

    return expected_newsvendor_profit(
        qh, sc.lambda_hot, sc.revenue_hot, sc.cost_hot, sc.salvage_hot
    ) + expected_newsvendor_profit(
        qc, sc.lambda_cold, sc.revenue_cold, sc.cost_cold, sc.salvage_cold
    )


def test_r2_r4_solutions_dominate_dense_feasible_grid():
    rng = np.random.default_rng(20260908)
    for round_number in (2, 4):
        for _ in range(24):
            sc = _random_scenario(rng)
            if round_number == 2:
                sc = Scenario(
                    **{**sc.__dict__, "cost_hot": 0.0, "cost_cold": 0.0}
                )
            sol = solve_round_scipy(sc, round_number)
            qh, qc = float(sol["Q_hot"]), float(sol["Q_cold"])
            assert sc.beans_hot * qh + sc.beans_cold * qc <= sc.beans_available + 1e-7
            assert sc.water_hot * qh + sc.water_cold * qc <= sc.water_available + 1e-7

            hot_cap, cold_cap = _resource_caps(sc)
            best_grid = -math.inf
            grid = np.linspace(0.0, 1.0, 61)
            for ah in grid:
                for ac in grid:
                    xh, xc = ah * hot_cap, ac * cold_cap
                    if (
                        sc.beans_hot * xh + sc.beans_cold * xc <= sc.beans_available + 1e-10
                        and sc.water_hot * xh + sc.water_cold * xc <= sc.water_available + 1e-10
                    ):
                        best_grid = max(best_grid, _objective(sc, xh, xc))
            assert sol["objective"] + 1e-8 >= best_grid


def test_interior_r2_r4_solution_satisfies_first_order_conditions():
    sc = Scenario(
        lambda_total=55.0,
        p_hot=0.6,
        p_cold=0.4,
        revenue_hot=6.0,
        revenue_cold=5.5,
        cost_hot=1.0,
        cost_cold=0.8,
        salvage_hot=0.2,
        salvage_cold=0.2,
        beans_available=500.0,
        water_available=500.0,
        beans_hot=1.0,
        beans_cold=1.0,
        water_hot=1.0,
        water_cold=1.0,
    )
    for round_number in (2, 4):
        sol = solve_round_scipy(sc, round_number)
        assert math.isfinite(sol["objective"])
        assert abs(
            expected_newsvendor_gradient(
                sol["Q_hot"], sc.lambda_hot, sc.revenue_hot,
                sc.cost_hot if round_number == 4 else 0.0, sc.salvage_hot
            )
        ) < 1e-5
        assert abs(
            expected_newsvendor_gradient(
                sol["Q_cold"], sc.lambda_cold, sc.revenue_cold,
                sc.cost_cold if round_number == 4 else 0.0, sc.salvage_cold
            )
        ) < 1e-5
