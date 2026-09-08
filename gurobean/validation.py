from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import numpy as np

from .model import expected_newsvendor_profit


@dataclass(frozen=True)
class MonteCarloCheck:
    q: float
    lam: float
    revenue: float
    cost: float
    salvage: float
    analytical_profit: float
    sampled_profit: float
    standard_error: float
    z_score: float
    passed: bool

    def to_dict(self) -> dict:
        return asdict(self)


def monte_carlo_newsvendor_check(
    q: float, lam: float, revenue: float, cost: float, salvage: float = 0.0,
    *, samples: int = 200_000, seed: int = 12345, z_limit: float = 5.0,
) -> MonteCarloCheck:
    """Validate the closed-form Normal objective against independent sampling."""
    if samples < 10_000:
        raise ValueError("samples must be >= 10000 for a useful validation")
    if q < 0 or lam < 0 or revenue < 0 or cost < 0 or salvage < 0:
        raise ValueError("economic inputs must be non-negative and q >= 0")
    rng = np.random.default_rng(seed)
    if lam == 0:
        sampled = np.zeros(samples)
    else:
        demand = rng.normal(lam, math.sqrt(lam), samples)
        sales = np.minimum(q, demand)
        leftover = np.maximum(q - demand, 0.0)
        sampled = revenue * sales - cost * q + salvage * leftover
    sample_mean = float(np.mean(sampled))
    se = float(np.std(sampled, ddof=1) / math.sqrt(samples)) if samples > 1 else 0.0
    analytical = float(expected_newsvendor_profit(q, lam, revenue, cost, salvage))
    z = abs(sample_mean - analytical) / max(se, 1e-15)
    return MonteCarloCheck(q, lam, revenue, cost, salvage, analytical, sample_mean, se, float(z), bool(z <= z_limit))
