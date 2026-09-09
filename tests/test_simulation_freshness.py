from gurobean.simulation import GurobeanSimulationConfig, simulate_gurobean


def test_inventory_does_not_carry_between_hours():
    # With zero arrivals, every hourly batch must expire as waste. If inventory
    # accumulated, the end-of-run waste would incorrectly be 2x the batch after
    # two hours plus an unexpired balance.
    config = GurobeanSimulationConfig(
        hours=2,
        seed=7,
        lambda_rate=0.0,
        p_hot=1.0,
        p_cold=0.0,
        mu_rate=10.0,
        brew_hot_per_hour=10.0,
        brew_cold_per_hour=0.0,
    )
    result, economics = simulate_gurobean(config)

    assert result.arrivals == 0
    assert result.served == 0
    assert economics["inventory_hot_end"] == 0.0
    assert economics["waste_hot"] == 20.0


def test_inventory_is_fresh_after_hour_boundary():
    # The exact event sequence is deterministic for a fixed seed. This test
    # mainly protects the invariant that the returned ending inventory is zero
    # and that waste is explicitly accounted for rather than silently carried.
    config = GurobeanSimulationConfig(
        hours=1,
        seed=11,
        lambda_rate=0.0,
        p_hot=1.0,
        p_cold=0.0,
        mu_rate=10.0,
        brew_hot_per_hour=7.5,
    )
    _, economics = simulate_gurobean(config)
    assert economics["inventory_hot_end"] == 0.0
    assert economics["waste_hot"] == 7.5
