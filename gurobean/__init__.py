from .model import (
    Scenario,
    RoundConfig,
    expected_newsvendor_profit,
    expected_newsvendor_gradient,
    solve_round1_closed_form,
    solve_round1_scipy,
    solve_round_scipy,
    solve_gurobi_round,
    solve_gurobi_r1,
    solve_round,
)
from .simulation import simulate_queue

__all__ = [
    "Scenario",
    "RoundConfig",
    "expected_newsvendor_profit",
    "expected_newsvendor_gradient",
    "solve_round1_closed_form",
    "solve_round1_scipy",
    "solve_round_scipy",
    "solve_gurobi_round",
    "solve_gurobi_r1",
    "solve_round",
    "simulate_queue",
    "CalibrationDataset", "Observation", "FitResult", "PromotionDecision",
    "best_fit", "calibration_gate", "validate_observations",
    "strict_calibration_gate",
]

from .calibration import (
    CalibrationDataset, Observation, FitResult, PromotionDecision, best_fit,
    calibration_gate, validate_observations,
)
from .evidence_gate import strict_calibration_gate

from .experiments import ExperimentSpec, ExperimentRun, ExperimentReport, run_experiment, kfold_split, cross_validated_rmse
from .validation import MonteCarloCheck, monte_carlo_newsvendor_check
from .calibrated import evaluate_r5, evaluate_r6, evaluate_r7, evaluate_r8

from .simulation import GurobeanSimulationConfig, SimulationResult, simulate_gurobean, simulate_queue
