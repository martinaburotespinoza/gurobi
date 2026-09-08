from __future__ import annotations

"""Reproducible experiment runner for calibration and model validation."""

from dataclasses import dataclass, asdict
from typing import Callable, Iterable, Sequence
import json
import math
import numpy as np

from .calibration import Observation, FitResult, best_fit


@dataclass(frozen=True)
class ExperimentSpec:
    name: str
    seeds: tuple[int, ...] = (42, 43, 44, 45, 46)
    warmup_hours: int = 0
    hours: int = 120


@dataclass(frozen=True)
class ExperimentRun:
    seed: int
    metrics: dict[str, float]


@dataclass(frozen=True)
class ExperimentReport:
    name: str
    runs: tuple[ExperimentRun, ...]
    aggregate: dict[str, float]

    def to_dict(self) -> dict:
        return {"name": self.name, "runs": [asdict(r) for r in self.runs], "aggregate": self.aggregate}

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def run_experiment(spec: ExperimentSpec, runner: Callable[[int, int, int], dict[str, float]]) -> ExperimentReport:
    if not spec.seeds:
        raise ValueError("at least one seed is required")
    if spec.hours <= 0 or spec.warmup_hours < 0 or spec.warmup_hours >= spec.hours:
        raise ValueError("hours must be > 0 and warmup_hours must satisfy 0 <= warmup < hours")
    runs = tuple(ExperimentRun(int(seed), {k: float(v) for k, v in runner(int(seed), spec.hours, spec.warmup_hours).items()}) for seed in spec.seeds)
    keys = sorted(set().union(*(r.metrics.keys() for r in runs)))
    aggregate: dict[str, float] = {}
    for key in keys:
        vals = np.asarray([r.metrics[key] for r in runs if key in r.metrics], dtype=float)
        aggregate[f"{key}_mean"] = float(np.mean(vals))
        aggregate[f"{key}_std"] = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
        aggregate[f"{key}_min"] = float(np.min(vals))
        aggregate[f"{key}_max"] = float(np.max(vals))
    return ExperimentReport(spec.name, runs, aggregate)


def kfold_split(observations: Sequence[Observation], folds: int = 5) -> list[tuple[list[Observation], list[Observation]]]:
    if folds < 2:
        raise ValueError("folds must be >= 2")
    n = len(observations)
    if n < folds:
        raise ValueError("number of observations must be >= folds")
    indices = np.array_split(np.arange(n), folds)
    result = []
    for i in range(folds):
        test_idx = set(int(x) for x in indices[i])
        train = [o for j, o in enumerate(observations) if j not in test_idx]
        test = [o for j, o in enumerate(observations) if j in test_idx]
        result.append((train, test))
    return result


def cross_validated_rmse(
    observations: Sequence[Observation],
    fitter: Callable[[Sequence[Observation]], Sequence[FitResult]],
    predictor: Callable[[FitResult, Observation], float],
    folds: int = 5,
) -> float:
    errors: list[float] = []
    for train, test in kfold_split(observations, folds):
        fit = best_fit(fitter(train))
        for obs in test:
            errors.append(float(predictor(fit, obs) - _target(obs, fit.round_number)) ** 2)
    return float(math.sqrt(np.mean(errors))) if errors else float("inf")


def _target(obs: Observation, round_number: int) -> float:
    targets = {5: "arrival_rate", 6: "stay_probability", 7: "order_size", 8: "barista_cost_per_hour"}
    key = targets[round_number]
    if key not in obs.outputs:
        raise ValueError(f"missing calibration target {key!r}")
    return float(obs.outputs[key])
