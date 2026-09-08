import math
import pytest

from gurobean.experiments import ExperimentSpec, cross_validated_rmse, kfold_split, run_experiment
from gurobean.calibration import Observation, fit_r5_arrival_rate


def test_experiment_reproducible_and_aggregated():
    spec = ExperimentSpec("demo", seeds=(1, 2, 3), hours=10)
    report = run_experiment(spec, lambda seed, hours, warmup: {"value": seed + hours + warmup})
    assert report.aggregate["value_mean"] == 12.0
    assert report.aggregate["value_std"] > 0
    assert len(report.runs) == 3


def test_kfold_is_complete_and_disjoint():
    obs = [Observation(5, {"markup": float(i)}, {"arrival_rate": 10 - i}) for i in range(10)]
    folds = kfold_split(obs, 5)
    assert len(folds) == 5
    for train, test in folds:
        assert not set(map(id, train)) & set(map(id, test))
        assert len(train) + len(test) == len(obs)


def test_cv_r5_linear_model():
    obs = [Observation(5, {"markup": float(i)}, {"arrival_rate": 20 - 2*i}) for i in range(10)]
    rmse = cross_validated_rmse(
        obs,
        fit_r5_arrival_rate,
        lambda fit, o: fit.parameters["a"] + fit.parameters["b"] * o.variables["markup"],
        folds=5,
    )
    assert rmse < 1e-8


def test_invalid_experiment_rejected():
    with pytest.raises(ValueError):
        run_experiment(ExperimentSpec("bad", seeds=(), hours=10), lambda *_: {})
    with pytest.raises(ValueError):
        run_experiment(ExperimentSpec("bad", seeds=(1,), hours=10, warmup_hours=10), lambda *_: {})
