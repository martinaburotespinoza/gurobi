from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gurobean.validation import monte_carlo_newsvendor_check
from gurobean.simulation import simulate_queue

DEFAULT_PRODUCTION_URL = "https://gurobi-rho.vercel.app"


def _http_json(base_url: str, path: str, *, method: str = "GET", payload: dict | None = None, attempts: int = 5) -> dict:
    url = base_url.rstrip("/") + path
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = Request(
                url,
                data=body,
                method=method,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} for {path}")
                raw = response.read().decode("utf-8")
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise RuntimeError(f"non-object JSON response for {path}")
                return value
        except (HTTPError, URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(5)
    raise RuntimeError(f"production request failed: {path}: {last_error}")


def _production_smoke() -> dict:
    base_url = os.environ.get("GUROBEAN_PRODUCTION_URL", DEFAULT_PRODUCTION_URL)
    health = _http_json(base_url, "/api/health")
    if health.get("status") != "ok" or health.get("service") != "gurobean-engine":
        raise AssertionError(f"unexpected production health payload: {health}")

    metadata = _http_json(base_url, "/api/metadata")
    rounds = metadata.get("rounds", {})
    if rounds.get("implemented") != [1, 2, 3, 4, 5, 6, 7, 8]:
        raise AssertionError(f"production metadata has unexpected rounds: {rounds}")
    if rounds.get("formal_game_certification_required") != [5, 6, 7, 8]:
        raise AssertionError("production certification boundary changed unexpectedly")

    scenario = {
        "lambda_total": 30.0,
        "p_hot": 0.7,
        "p_cold": 0.3,
        "revenue_hot": 3.0,
        "revenue_cold": 3.5,
        "cost_hot": 1.2,
        "cost_cold": 1.5,
        "salvage_hot": 0.0,
        "salvage_cold": 0.0,
        "beans_available": 80.0,
        "water_available": 80.0,
        "beans_hot": 1.0,
        "beans_cold": 1.0,
        "water_hot": 1.0,
        "water_cold": 1.0,
    }
    dynamic = {
        "arrival_baseline_rate": 30.0,
        "arrival_reference_rate": 18.0,
        "reference_markup": 1.0,
        "markup_min": 0.0,
        "markup_max": 3.0,
        "balking_a": 2.0,
        "balking_b": -0.15,
        "multi_cup_theta": 0.5,
        "service_rate_base": 45.0,
        "service_rate_min": 35.0,
        "service_rate_max": 60.0,
        "service_cost_fixed": 0.0,
        "service_cost_linear": 1.0,
        "service_cost_quadratic": 0.0,
        "hours": 12,
        "warmup_hours": 0,
        "replications": 1,
        "seed": 123,
        "coordinate_points": 3,
    }
    solve_payload = {
        "round_number": 6,
        "scenario": scenario,
        "backend": "simulation",
        "dynamic": dynamic,
    }
    solved = _http_json(base_url, "/api/solve", method="POST", payload=solve_payload)
    result = solved.get("result")
    if solved.get("ok") is not True or not isinstance(result, dict):
        raise AssertionError(f"production R6 solve failed: {solved}")
    for key in ("Q_hot", "Q_cold", "markup", "service_rate", "objective", "expected_profit"):
        value = result.get(key)
        if not isinstance(value, (int, float)):
            raise AssertionError(f"production R6 result missing numeric {key}: {result}")

    evaluation_payload = {
        "round_number": 6,
        "scenario": scenario,
        "q_hot": result["Q_hot"],
        "q_cold": result["Q_cold"],
        "markup": result["markup"],
        "service_rate": result["service_rate"],
        "replications": 1,
        "seed": 123,
        "hours": 12,
        "warmup_hours": 0,
        "barista_cost_per_hour": 0.0,
        "dynamic": dynamic,
    }
    evaluated = _http_json(base_url, "/api/evaluate", method="POST", payload=evaluation_payload)
    evaluation = evaluated.get("evaluation")
    if evaluated.get("ok") is not True or not isinstance(evaluation, dict):
        raise AssertionError(f"production R6 evaluation failed: {evaluated}")
    if abs(float(evaluation["mean_profit"]) - float(result["expected_profit"])) > 1e-9:
        raise AssertionError(
            "production R6 solve/evaluate mismatch: "
            f"solve={result['expected_profit']} evaluate={evaluation['mean_profit']}"
        )

    return {
        "url": base_url,
        "health": health,
        "metadata_rounds": rounds,
        "r6_solve": {
            "Q_hot": result["Q_hot"],
            "Q_cold": result["Q_cold"],
            "markup": result["markup"],
            "service_rate": result["service_rate"],
            "expected_profit": result["expected_profit"],
        },
        "r6_solve_evaluate_parity": True,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    checks = []
    checks.append(monte_carlo_newsvendor_check(25.0, 25.0, 1.0, 0.0, samples=100_000, seed=101).to_dict())
    checks.append(monte_carlo_newsvendor_check(42.0, 40.0, 4.0, 1.5, samples=100_000, seed=102).to_dict())
    sim = simulate_queue(10.0, 15.0, hours=120, warmup_hours=10, seed=103)
    checks.append({"simulation": sim.__dict__})
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=root, capture_output=True, text=True)
    report = {
        "monte_carlo": checks[:2],
        "simulation": checks[2],
        "pytest_returncode": result.returncode,
        "pytest_stdout": result.stdout.strip(),
    }
    if result.returncode:
        Path(root / "validation_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return result.returncode

    report["production_http"] = _production_smoke()
    report["production_http_status"] = "PASS"
    Path(root / "validation_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(c["passed"] for c in checks[:2]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
