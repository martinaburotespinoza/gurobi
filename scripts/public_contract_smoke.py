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


def check(client: TestClient, method: str, path: str, payload=None) -> None:
    response = client.request(method, path, json=payload)
    if response.status_code != 200:
        raise SystemExit(f"FAIL {method} {path}: {response.status_code} {response.text}")


def main() -> None:
    client = TestClient(app)
    check(client, "GET", "/health")
    metadata = client.get("/metadata")
    if metadata.status_code != 200:
        raise SystemExit(f"FAIL GET /metadata: {metadata.status_code} {metadata.text}")
    rounds = metadata.json()["rounds"]["implemented"]
    if rounds != list(range(1, 9)):
        raise SystemExit(f"FAIL metadata rounds: {rounds}")

    for round_number in range(1, 5):
        check(client, "POST", "/solve", solve_payload(round_number, "scipy"))
    for round_number in range(5, 9):
        check(client, "POST", "/solve", solve_payload(round_number, "simulation"))

    check(client, "POST", "/evaluate", {
        "round_number": 8,
        "scenario": scenario(),
        "q_hot": 5.0,
        "q_cold": 5.0,
        "markup": 1.0,
        "service_rate": 65.0,
        "replications": 1,
        "hours": 2,
    })
    print("PUBLIC CONTRACT: PASS (R1-R8 + evaluate)")


if __name__ == "__main__":
    main()
