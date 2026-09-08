from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
from gurobean.experiments import ExperimentSpec, run_experiment
from gurobean.simulation import simulate_queue


def main() -> None:
    spec = ExperimentSpec("mm1_reference_120h", seeds=(42, 43, 44, 45, 46), hours=120, warmup_hours=10)
    report = run_experiment(
        spec,
        lambda seed, hours, warmup: _metrics(seed, hours, warmup),
    )
    print(report.to_json())


def _metrics(seed: int, hours: int, warmup: int) -> dict[str, float]:
    result = simulate_queue(lambda_rate=20.0, mu_rate=25.0, hours=hours, seed=seed, warmup_hours=warmup)
    return {
        "arrivals": result.arrivals,
        "served": result.served,
        "lost": result.lost,
        "mean_queue": result.mean_queue,
        "mean_wait": result.mean_wait,
        "utilization": result.utilization,
    }


if __name__ == "__main__":
    main()
