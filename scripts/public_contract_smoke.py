"""Fast public-contract smoke test runnable without a Gurobi license."""
from fastapi.testclient import TestClient

from api.app import app


def scenario() -> dict:
    return {
        "lambda_total": 20.0,
        "p_hot": 0.7,
        "p_cold": 0.3,
        "revenue_hot": 5.0,
        "revenue_cold": 4.0,
        "cost_hot": 2.0,
        "cost_cold": 1.5,
        "salvage_hot": 0.0,
        "salvage_cold": 0.0,
        "beans_available": 100.0,
        "water_available": 100.0,
        "beans_hot": 1.0,
        "beans_cold": 1.0,
        "water_hot": 1.0,
        "water_cold": 1.0,
    }


def solve_payload(round_number: int, backend: str) -> dict:
    return {
        "round_number": round_number,
        "backend": backend,
        "scenario": scenario(),
        "dynamic": {
            "arrival_reference_rate": 20.0,
            "hours": 2,
            "replications": 1,
            "coordinate_points": 3,
        },
    }


def main() -> None:
    client = TestClient(app)
    checks = [
        ("GET", "/health", None),
        ("GET", "/metadata", None),
        ("POST", "/solve", solve_payload(1, "scipy")),
        ("POST", "/solve", solve_payload(5, "simulation")),
        ("POST", "/solve", solve_payload(8, "simulation")),
        ("POST", "/evaluate", {
            "round_number": 8,
            "scenario": scenario(),
            "q_hot": 5.0,
            "q_cold": 5.0,
            "markup": 1.0,
            "service_rate": 65.0,
            "replications": 1,
            "hours": 2,
        }),
    ]
    for method, path, payload in checks:
        response = client.request(method, path, json=payload)
        if response.status_code != 200:
            raise SystemExit(f"FAIL {method} {path}: {response.status_code} {response.text}")
    print("PUBLIC CONTRACT: PASS")


if __name__ == "__main__":
    main()
