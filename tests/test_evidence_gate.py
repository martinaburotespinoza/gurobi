from gurobean.calibration import FitResult, Observation
from gurobean.evidence_gate import strict_calibration_gate


def _fit():
    return FitResult(5, "linear", {"a": 20.0, "b": -1.0}, 0.0, 8, 0.0, {})


def test_strict_gate_rejects_synthetic_provenance():
    obs = [
        Observation(5, {"markup": float(i)}, {"arrival_rate": 20.0 - i}, source="synthetic")
        for i in range(8)
    ]
    decision = strict_calibration_gate(obs, [_fit()], min_observations=8, require_monotone=True)
    assert not decision.eligible
    assert decision.reason == "non_game_observation_source"


def test_strict_gate_accepts_real_game_provenance_when_statistics_pass():
    obs = [
        Observation(5, {"markup": float(i)}, {"arrival_rate": 20.0 - i}, source="game")
        for i in range(8)
    ]
    decision = strict_calibration_gate(obs, [_fit()], min_observations=8, max_rmse=0.1, require_monotone=True)
    assert decision.eligible
    assert decision.reason == "promotion_gate_passed"
