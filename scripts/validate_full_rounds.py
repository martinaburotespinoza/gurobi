from __future__ import annotations

import math

from gurobean import Scenario
from gurobean.full_rounds import DynamicRoundParams, solve_dynamic_round


def main() -> int:
    sc = Scenario(
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
    params = DynamicRoundParams(
        arrival_baseline_rate=30.0,
        arrival_reference_rate=18.0,
        reference_markup=1.0,
        markup_max=3.0,
        balking_a=2.0,
        balking_b=-0.15,
        multi_cup_theta=0.5,
        service_rate_base=45.0,
        service_rate_min=35.0,
        service_rate_max=60.0,
        service_cost_linear=1.0,
        hours=120,
        warmup_hours=0,
        replications=2,
        seed=123,
        coordinate_points=3,
    )

    print("=== GUROBEAN R5-R8 OPERATIONAL VALIDATION ===")
    for round_number in range(5, 9):
        result = solve_dynamic_round(sc, round_number, params)
        assert result["operational"] is True
        assert result["formal_game_certified"] is False
        assert result["simulation_hours"] == 120
        assert result["replications"] == 2
        assert math.isfinite(result["objective"])
        assert result["Q_hot"] >= 0 and result["Q_cold"] >= 0
        assert result["markup"] >= 0
        assert result["service_rate"] > 0
        print(
            f"R{round_number}: PASS | Q_hot={result['Q_hot']:.4f} "
            f"Q_cold={result['Q_cold']:.4f} markup={result['markup']:.4f} "
            f"mu={result['service_rate']:.4f} objective={result['objective']:.4f}"
        )
    print("R5-R8 STATUS: OPERATIONAL")
    print("CERTIFICATION: EVIDENCE-GATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())