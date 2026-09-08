from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gurobean.model import Scenario, solve_round_scipy


def main() -> None:
    scenario = Scenario(
        lambda_total=80,
        p_hot=0.5,
        p_cold=0.5,
        revenue_hot=4.0,
        revenue_cold=5.0,
        cost_hot=1.5,
        cost_cold=2.0,
        beans_available=100.0,
        water_available=100.0,
        beans_hot=1.0,
        beans_cold=1.0,
        water_hot=1.0,
        water_cold=1.0,
    )
    results = {f"R{r}": solve_round_scipy(scenario, r) for r in (1, 2, 3, 4)}
    report = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "rounds": results,
        "gurobipy_installed": _gurobi_available(),
    }
    print(json.dumps(report, indent=2, sort_keys=True))


def _gurobi_available() -> bool:
    try:
        import gurobipy  # noqa: F401
    except ImportError:
        return False
    return True


if __name__ == "__main__":
    main()
