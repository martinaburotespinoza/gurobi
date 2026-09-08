import math

from gurobean.calibration import FitResult
from gurobean.calibrated import evaluate_r5, evaluate_r6, evaluate_r7, evaluate_r8


def test_promoted_runtime_evaluators():
    assert math.isclose(evaluate_r5(FitResult(5, "linear", {"a": 20, "b": -2}, 0, 8, 0, {}), 3), 14)
    p = evaluate_r6(FitResult(6, "logistic", {"a": 0, "b": -1}, 0, 8, 0, {}), 0)
    assert 0 < p < 1
    pmf = evaluate_r7(FitResult(7, "geometric", {"p": 0.5}, 0, 8, 0, {}), 2)
    assert math.isclose(pmf, 0.25)
    assert math.isclose(evaluate_r8(FitResult(8, "quadratic", {"a": 2, "b": 1, "c": 0.1}, 0, 8, 0, {}), 10), 22)
