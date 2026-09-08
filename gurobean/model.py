from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, sqrt, pi
from typing import Dict, Optional, Tuple

import numpy as np

SQRT2PI = sqrt(2 * pi)


def phi(z: float) -> float:
    return exp(-0.5 * z * z) / SQRT2PI


def Phi(z: float) -> float:
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


@dataclass(frozen=True)
class Scenario:
    """Parameters explicitly supported by the Gurobean Game Guide model."""

    lambda_total: float
    p_hot: float = 1.0
    p_cold: float = 0.0
    revenue_hot: float = 1.0
    revenue_cold: float = 1.0
    cost_hot: float = 0.0
    cost_cold: float = 0.0
    # Kept as an explicit extension hook. The official guide's base formulation
    # uses waste rather than a positive salvage value, so the default is zero.
    salvage_hot: float = 0.0
    salvage_cold: float = 0.0
    beans_available: float = np.inf
    water_available: float = np.inf
    beans_hot: float = 0.0
    beans_cold: float = 0.0
    water_hot: float = 0.0
    water_cold: float = 0.0

    def __post_init__(self) -> None:
        if self.lambda_total < 0:
            raise ValueError("lambda_total must be >= 0")
        if self.p_hot < 0 or self.p_cold < 0:
            raise ValueError("drink probabilities must be >= 0")
        if abs((self.p_hot + self.p_cold) - 1.0) > 1e-12:
            raise ValueError("drink probabilities must sum to 1")
        for name in (
            "revenue_hot", "revenue_cold", "cost_hot", "cost_cold",
            "salvage_hot", "salvage_cold", "beans_available",
            "water_available", "beans_hot", "beans_cold", "water_hot",
            "water_cold",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be >= 0")

    @property
    def lambda_hot(self) -> float:
        return self.lambda_total * self.p_hot

    @property
    def lambda_cold(self) -> float:
        return self.lambda_total * self.p_cold


@dataclass(frozen=True)
class RoundConfig:
    round_number: int
    include_cold: bool = False
    include_brew_cost: bool = False
    include_markup: bool = False
    include_balking: bool = False
    include_multi_cup: bool = False
    include_service_rate: bool = False

    @staticmethod
    def for_round(n: int) -> "RoundConfig":
        if n not in range(1, 9):
            raise ValueError("round must be 1..8")
        return RoundConfig(
            n,
            include_cold=n >= 2,
            include_brew_cost=n >= 3,
            include_markup=n >= 5,
            include_balking=n >= 6,
            include_multi_cup=n >= 7,
            include_service_rate=n >= 8,
        )


def expected_newsvendor_profit(
    Q: float,
    lam: float,
    revenue: float,
    cost: float,
    salvage: float = 0.0,
) -> float:
    """Exact expected profit under Gurobi's Normal approximation.

    The Game Guide states that hourly Poisson demand is approximated for the
    optimization by Normal(lam, lam). For D~N(lam, lam):

      E[min(Q,D)] = lam*Phi(z) - sqrt(lam)*phi(z) + Q*(1-Phi(z))
      E[(Q-D)+]  = (Q-lam)*Phi(z) + sqrt(lam)*phi(z)
      z = (Q-lam)/sqrt(lam)

    Profit = revenue*sales - cost*Q + salvage*leftover.
    """
    if Q < 0:
        return -np.inf
    if lam <= 0:
        return Q * (salvage - cost) if Q > 0 else 0.0

    sigma = sqrt(lam)
    z = (Q - lam) / sigma
    cdf = Phi(z)
    pdf = phi(z)
    sales = lam * cdf - sigma * pdf + Q * (1.0 - cdf)
    leftover = (Q - lam) * cdf + sigma * pdf
    return revenue * sales - cost * Q + salvage * leftover


def expected_newsvendor_gradient(
    Q: float,
    lam: float,
    revenue: float,
    cost: float,
    salvage: float = 0.0,
) -> float: