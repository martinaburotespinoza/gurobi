"""Run all eight operational rounds as one reproducible campaign.

The runner is useful for regression, demos and calibration preparation. It never
labels synthetic runs as real-game certification. R1-R4 use the reference
optimizer; R5-R8 use the explicit-parameter simulation optimizer.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gurobean.full_rounds import DynamicRoundParams, solve_dynamic_round
from gurobean.model import Scenario, solve_round


def build_scenario(args: argparse.Namespace) -> Scenario:
    return Scenario(
        lambda_total=args.lambda_total,
        p_hot=args.p_hot,
        p_cold=1.0 - args.p_hot,
        revenue_hot=args.revenue_hot,
        revenue_cold=args.revenue_cold,
        cost_hot=args.cost_hot,
        cost_cold=args.cost_cold,
        beans_available=args.beans_available,
        water_available=args.water_available,
        beans_hot=args.beans_hot,
        beans_cold=args.beans_cold,
        water_hot=args.water_hot,
        water_cold=args.water_cold,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lambda-total", type=float, default=20.0)
    parser.add_argument("--p-hot", type=float, default=0.7)
    parser.add_argument("--revenue-hot", type=float, default=5.0)
    parser.add_argument("--revenue-cold", type=float, default=4.0)
    parser.add_argument("--cost-hot", type=float, default=2.0)
    parser.add_argument("--cost-cold", type=float, default=1.5)
    parser.add_argument("--beans-available", type=float, default=100.0)
    parser.add_argument("--water-available", type=float, default=100.0)
    parser.add_argument("--beans-hot", type=float, default=1.0)
    parser.add_argument("--beans-cold", type=float, default=1.0)
    parser.add_argument("--water-hot", type=float, default=1.0)
    parser.add_argument("--water-cold", type=float, default=1.0)
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--replications", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--coordinate-points", type=int, default=5)
    parser.add_argument("--output", type=Path, default=ROOT / "campaign_report.json")
    args = parser.parse_args()

    scenario = build_scenario(args)
    dynamic = DynamicRoundParams(
        arrival_baseline_rate=max(args.lambda_total, 1e-9),
        arrival_reference_rate=max(min(args.lambda_total * 0.6, args.lambda_total), 1e-9),
        reference_markup=1.0,
        hours=args.hours,
        replications=args.replications,
        seed=args.seed,
        coordinate_points=args.coordinate_points,
        service_cost_linear=4.0,
    )

    rounds: list[dict] = []
    for round_number in range(1, 9):
        if round_number <= 4:
            result = solve_round(round_number, scenario, backend="scipy")
            result = dict(result)
            result["operational"] = True
            result["formal_game_certified"] = round_number in (1, 2, 3, 4)
            result["backend"] = "scipy-reference"
        else:
            result = solve_dynamic_round(scenario, round_number, dynamic)
            result = dict(result)
            result["backend"] = "simulation"
        result["round"] = round_number
        rounds.append(result)
        print(
            f"R{round_number}: Q_hot={result['Q_hot']:.6f} "
            f"Q_cold={result['Q_cold']:.6f} objective={result['objective']:.6f}"
        )

    report = {
        "schema": "gurobean.eight-round-campaign.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario.__dict__,
        "dynamic_parameters": dynamic.__dict__,
        "rounds": rounds,
        "rounds_completed": len(rounds),
        "synthetic_or_calibrated": "synthetic_defaults",
        "real_game_certified": False,
        "certification_note": "This campaign proves executable eight-round plumbing only. R5-R8 require real-game evidence and OOS validation for parity promotion.",
    }
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"REPORT: {args.output}")
    print("STATUS: PASS — EIGHT-ROUND EXECUTABLE CAMPAIGN")
    print("REAL_GAME_CERTIFIED: FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
