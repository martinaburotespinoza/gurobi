from gurobean.calibration import Observation, FitResult, calibration_gate


def test_gate_blocks_small_samples():
    obs = [Observation(5, {"markup": float(i)}, {"arrival_rate": 10.0}) for i in range(3)]
    fit = FitResult(5, "linear", {"a": 10.0, "b": 0.0}, 0.0, 3, 0.0, {})
    d = calibration_gate(obs, [fit], min_observations=8, require_monotone=True)
    assert not d.eligible
    assert d.reason == "insufficient_observations"


def test_gate_accepts_sufficient_evidence():
    obs = [Observation(5, {"markup": float(i)}, {"arrival_rate": 20.0 - i}) for i in range(8)]
    fit = FitResult(5, "linear", {"a": 20.0, "b": -1.0}, 0.0, 8, 0.0, {})
    d = calibration_gate(obs, [fit], min_observations=8, max_rmse=0.1, require_monotone=True)
    assert d.eligible
    assert d.reason == "promotion_gate_passed"
