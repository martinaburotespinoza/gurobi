"""Repository-wide deterministic self-audit for Gurobean.

This gate is solver-independent. It checks the mathematical reference layer,
public API boundaries, deterministic simulation behavior, finite-input
invariants, R9 scenario contracts, and the certification boundary. It must
never report licensed-Gurobi certification; that remains the explicit R9
release gate.
"""
from __future__ import annotations

import ast
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from gurobean.model import Scenario, expected_newsvendor_profit, solve_round_scipy
from gurobean.simulation import GurobeanSimulationConfig, simulate_gurobean, simulate_queue
import r9_end_to_end as r9


def _assert_close(a: float, b: float, tol: float = 1e-8) -> None:
    if not math.isfinite(a) or not math.isfinite(b) or abs(a - b) > tol:
        raise AssertionError(f"values differ: {a!r} vs {b!r}")


def audit_reference_layer() -> None:
    base = dict(
        lambda_total=40.0,
        p_hot=0.7,
        p_cold=0.3,
        revenue_hot=3.0,
        revenue_cold=4.0,
        cost_hot=0.8,
        cost_cold=1.0,
        beans_available=100.0,
        water_available=100.0,
        beans_hot=1.0,
        beans_cold=1.2,
        water_hot=1.0,
        water_cold=0.8,
    )
    sc = Scenario(**base)
    for rn in (1, 2, 3, 4):
        result = solve_round_scipy(sc, rn)
        qh = float(result["Q_hot"])
        qc = float(result["Q_cold"])
        assert qh >= -1e-9 and qc >= -1e-9
        assert sc.beans_hot * qh + sc.beans_cold * qc <= sc.beans_available + 1e-7
        assert sc.water_hot * qh + sc.water_cold * qc <= sc.water_available + 1e-7
        assert math.isfinite(float(result["objective"]))

    zero = Scenario(
        lambda_total=0.0,
        p_hot=1.0,
        p_cold=0.0,
        revenue_hot=3.0,
        cost_hot=1.0,
        beans_available=10.0,
        water_available=10.0,
        beans_hot=1.0,
        water_hot=1.0,
    )
    r1 = solve_round_scipy(zero, 1)
    assert r1["Q_hot"] >= 0.0
    assert math.isfinite(float(r1["objective"]))
    _assert_close(expected_newsvendor_profit(0.0, 0.0, 3.0, 1.0), 0.0)


def audit_r9_scenario_contract() -> None:
    rng = random.Random(r9.SEED)
    for i in range(r9.CASES):
        sc = r9._scenario(rng, i % 4)
        assert abs(sc.p_hot + sc.p_cold - 1.0) <= 1e-12
        assert sc.salvage_hot == 0.0 and sc.salvage_cold == 0.0
        assert sc.lambda_hot + sc.lambda_cold == sc.lambda_total


def audit_simulation_layer() -> None:
    a = simulate_queue(12.0, 20.0, hours=120, seed=24680, warmup_hours=10)
    b = simulate_queue(12.0, 20.0, hours=120, seed=24680, warmup_hours=10)
    assert a == b
    assert 0.0 <= a.utilization <= 1.0
    assert a.arrivals >= a.served >= 0

    cfg = GurobeanSimulationConfig(
        hours=120,
        warmup_hours=10,
        seed=24680,
        lambda_rate=12.0,
        p_hot=0.7,
        p_cold=0.3,
        mu_rate=20.0,
        brew_hot_per_hour=20.0,
        brew_cold_per_hour=12.0,
        revenue_hot=3.0,
        revenue_cold=4.0,
        brew_cost_hot=0.8,
        brew_cost_cold=1.0,
        barista_cost_per_hour=2.0,
    )
    r1, e1 = simulate_gurobean(cfg)
    r2, e2 = simulate_gurobean(cfg)
    assert r1 == r2 and e1 == e2
    assert e1["served_cups"] >= 0 and e1["lost_customers"] >= 0
    assert 0.0 <= r1.utilization <= 1.0


def audit_source_contract() -> None:
    forbidden = ("TODO", "FIXME")
    intentional_boundary = {"evidence_gate.py", "model.py"}
    scan_roots = (ROOT / "gurobean", ROOT / "scripts")
    hits: list[str] = []
    for root in scan_roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
            compile(tree, str(path), "exec")
            if any(token in text for token in forbidden):
                hits.append(str(path.relative_to(ROOT)))
            if "NotImplementedError" in text and path.name not in intentional_boundary:
                hits.append(str(path.relative_to(ROOT)) + ":unexpected_NotImplementedError")
    if hits:
        raise AssertionError(f"unexpected unfinished markers: {hits}")

    evidence = (ROOT / "gurobean" / "evidence_gate.py").read_text(encoding="utf-8")
    assert "synthetic" in evidence.lower()
    model = (ROOT / "gurobean" / "model.py").read_text(encoding="utf-8")
    assert "NotImplementedError" in model


def main() -> int:
    audit_source_contract()
    audit_reference_layer()
    audit_r9_scenario_contract()
    audit_simulation_layer()
    print("SELF_AUDIT: PASS")
    print("REFERENCE_LAYER: PASS")
    print("R9_SCENARIO_CONTRACT: PASS")
    print("SIMULATION_LAYER: PASS")
    print("SOURCE_CONTRACT: PASS")
    print("GUROBI_CERTIFICATION: NOT_CLAIMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
