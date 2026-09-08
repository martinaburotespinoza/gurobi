from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gurobean.model import Scenario, solve_round
from gurobean.simulation import simulate_queue
from gurobean.experiments import ExperimentSpec, run_experiment


def main() -> None:
    sc = Scenario(lambda_total=100, p_hot=1, p_cold=0, revenue_hot=2, revenue_cold=0, cost_hot=0, cost_cold=0,
                  beans_available=100, water_available=100, beans_hot=1, beans_cold=0, water_hot=1, water_cold=0)
    r1 = solve_round(1, sc, backend='scipy')
    assert r1['Q_hot'] >= 0 and r1['objective'] >= 0
    spec = ExperimentSpec('validation', seeds=(1,2,3,4,5), hours=120, warmup_hours=10)
    rep = run_experiment(spec, lambda seed,h,w: vars(simulate_queue(20,25,h,seed,w)))
    assert rep.aggregate['utilization_mean'] > 0
    print('VALIDATION_OK')
    print('R1_Q_HOT', round(r1['Q_hot'], 6))
    print('SIM_UTIL_MEAN', round(rep.aggregate['utilization_mean'], 6))

if __name__ == '__main__':
    main()
