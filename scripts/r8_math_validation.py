"""R8 advanced mathematical certification for the Gurobean core model.

R8 is a certification harness only. It does not modify the production model.
It checks differential identities, concavity, economic stationarity,
resource-bound behavior, objective decomposition and deterministic stress
coverage for the exact Normal-newsvendor formulation used by R1-R4.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from gurobean.model import (
    Scenario,
    _economic_unconstrained_q,
    _feasible,
    _resource_caps,
    _round_bounds,
    _round_objective,
    expected_newsvendor_gradient,
    expected_newsvendor_profit,
    solve_round1_closed_form,
)

SEED = 802026
CASES = 250
FD_STEP = 1e-5
GRAD_TOL = 2e-6
HESS_TOL = 2e-5
CONCAVITY_TOL = 1e-10
STATIONARITY_TOL = 3e-6


@dataclass(frozen=True)
class CaseResult:
    case: int
    checks: dict
    passed: bool
    error: str | None = None


def _scenario(rng: random.Random) -> Scenario:
    lam = rng.uniform(0.05, 80.0)
    p_hot = rng.uniform(0.05, 0.95)
    p_cold = 1.0 - p_hot
    rev_h = rng.uniform(0.5, 8.0)
    rev_c = rng.uniform(0.5, 8.0)
    cost_h = rng.uniform(0.0, rev_h * 0.9)
    cost_c = rng.uniform(0.0, rev_c * 0.9)
    salvage_h = rng.uniform(0.0, max(cost_h, 1e-12))
    salvage_c = rng.uniform(0.0, max(cost_c, 1e-12))

    beans_hot = rng.uniform(0.05, 2.0)
    beans_cold = rng.uniform(0.05, 2.0)
    water_hot = rng.uniform(0.1, 3.0)
    water_cold = rng.uniform(0.1, 3.0)
    demand_scale = lam * rng.uniform(0.45, 2.0)
    beans_available = demand_scale * rng.uniform(0.7, 2.2) * max(beans_hot, beans_cold)
    water_available = demand_scale * rng.uniform(0.7, 2.2) * max(water_hot, water_cold)

    return Scenario(
        lambda_total=lam,
        p_hot=p_hot,
        p_cold=p_cold,
        revenue_hot=rev_h,
        revenue_cold=rev_c,
        cost_hot=cost_h,
        cost_cold=cost_c,
        salvage_hot=salvage_h,
        salvage_cold=salvage_c,
        beans_available=beans_available,
        water_available=water_available,
        beans_hot=beans_hot,
        beans_cold=beans_cold,
        water_hot=water_hot,
        water_cold=water_cold,
    )


def _central_difference(fun, x: float, h: float) -> float:
    return (float(fun(x + h)) - float(fun(x - h))) / (2.0 * h)


def _check_single_product(lam: float, revenue: float, cost: float, salvage: float, q: float) -> dict:
    def f(x: float) -> float:
        return expected_newsvendor_profit(x, lam, revenue, cost, salvage)
    analytic_g = expected_newsvendor_gradient(q, lam, revenue, cost, salvage)
    h = FD_STEP * max(1.0, abs(q))
    numeric_g = _central_difference(f, q, h)
    z = (q - lam) / math.sqrt(lam)
    analytic_h = -(revenue - salvage) * math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi * lam)
    numeric_h = _central_difference(lambda x: expected_newsvendor_gradient(x, lam, revenue, cost, salvage), q, h)
    return {"gradient_abs_error": abs(analytic_g - numeric_g), "hessian_abs_error": abs(analytic_h - numeric_h),
            "hessian_value": analytic_h, "concave": analytic_h <= CONCAVITY_TOL}


def _check_closed_form(lam: float, revenue: float, cost: float, salvage: float) -> dict:
    q = _economic_unconstrained_q(lam, revenue, cost, salvage)
    g = expected_newsvendor_gradient(q, lam, revenue, cost, salvage)
    return {"q": float(q), "gradient_abs": abs(float(g)), "stationary": bool(np.isfinite(q) and abs(float(g)) <= STATIONARITY_TOL)}


def _check_round_decomposition(sc: Scenario) -> dict:
    hot_hi, cold_hi = _round_bounds(sc, True, True)
    qh = min(hot_hi, sc.lambda_hot + math.sqrt(sc.lambda_hot))
    qc = min(cold_hi, sc.lambda_cold + math.sqrt(sc.lambda_cold))
    if not _feasible(qh, qc, sc):
        for _ in range(80):
            qh *= 0.5
            qc *= 0.5
            if _feasible(qh, qc, sc):
                break
    total = _round_objective(sc, True, True, qh, qc)
    hot = expected_newsvendor_profit(qh, sc.lambda_hot, sc.revenue_hot, sc.cost_hot, sc.salvage_hot)
    cold = expected_newsvendor_profit(qc, sc.lambda_cold, sc.revenue_cold, sc.cost_cold, sc.salvage_cold)
    return {"decomposition_abs_error": abs(total - (hot + cold)), "finite": bool(np.isfinite(total)),
            "feasible": _feasible(qh, qc, sc), "probe_q_hot": float(qh), "probe_q_cold": float(qc)}


def _check_boundary(sc: Scenario) -> dict:
    hot_cap, _ = _resource_caps(sc, False)
    if not np.isfinite(hot_cap):
        return {"skipped": True}
    result = solve_round1_closed_form(sc)
    q = float(result["Q_hot"])
    economic = _economic_unconstrained_q(sc.lambda_hot, sc.revenue_hot, 0.0, sc.salvage_hot)
    feasible = _feasible(q, 0.0, sc)
    within = -1e-10 <= q <= hot_cap + 1e-10
    expected = hot_cap if not np.isfinite(economic) else min(hot_cap, economic)
    clipping_error = abs(q - max(0.0, float(expected)))
    return {"skipped": False, "q": q, "cap": float(hot_cap), "feasible": feasible, "within_cap": within, "clipping_abs_error": clipping_error}


def audit_case(index: int, sc: Scenario) -> CaseResult:
    try:
        points = []
        for lam, rev, cost, salvage in ((sc.lambda_hot, sc.revenue_hot, sc.cost_hot, sc.salvage_hot),
                                        (sc.lambda_cold, sc.revenue_cold, sc.cost_cold, sc.salvage_cold)):
            if lam > 1e-8:
                q = max(1e-4, lam + math.sqrt(lam) * 0.35)
                points.append(_check_single_product(lam, rev, cost, salvage, q))
        grad_err = max((p["gradient_abs_error"] for p in points), default=0.0)
        hess_err = max((p["hessian_abs_error"] for p in points), default=0.0)
        concave = all(p["concave"] for p in points)
        closed = _check_closed_form(sc.lambda_hot, sc.revenue_hot, sc.cost_hot, sc.salvage_hot)
        decomp = _check_round_decomposition(sc)
        boundary = _check_boundary(sc)
        checks = {"max_gradient_abs_error": grad_err, "max_hessian_abs_error": hess_err,
                  "all_single_product_objectives_concave": concave, "closed_form_stationarity": closed,
                  "round_objective_decomposition": decomp, "resource_boundary": boundary}
        passed = bool(grad_err <= GRAD_TOL and hess_err <= HESS_TOL and concave and closed["stationary"]
                      and decomp["decomposition_abs_error"] <= 1e-10 and decomp["finite"] and decomp["feasible"]
                      and (boundary.get("skipped") or (boundary["feasible"] and boundary["within_cap"] and boundary["clipping_abs_error"] <= 1e-10)))
        return CaseResult(index, checks, passed)
    except Exception as exc:
        return CaseResult(index, {}, False, repr(exc))


def main() -> int:
    rng = random.Random(SEED)
    results = [audit_case(i, _scenario(rng)) for i in range(CASES)]
    failures = [r for r in results if not r.passed]
    max_grad = max((r.checks.get("max_gradient_abs_error", 0.0) for r in results), default=0.0)
    max_hess = max((r.checks.get("max_hessian_abs_error", 0.0) for r in results), default=0.0)
    out = {"schema": "gurobean.r8.math_validation.v3", "seed": SEED, "cases": CASES, "failures": len(failures),
           "max_gradient_abs_error": max_grad, "max_hessian_abs_error": max_hess,
           "status": "PASS" if not failures else "FAIL", "results": [asdict(r) for r in results]}
    Path("r8_math_validation.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("=== R8 ADVANCED MATHEMATICAL VALIDATION ===")
    print(f"CASES: {CASES}")
    print(f"FAILURES: {len(failures)}")
    print(f"MAX_GRADIENT_ABS_ERROR: {max_grad:.12g}")
    print(f"MAX_HESSIAN_ABS_ERROR: {max_hess:.12g}")
    if failures:
        print("FAILED_CASES:")
        for failure in failures:
            print(json.dumps(asdict(failure), sort_keys=True))
    print(f"R8 STATUS: {out['status']}")
    print("ARTIFACT: r8_math_validation.json")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
