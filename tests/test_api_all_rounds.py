import math

from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


BASE_SCENARIO = {
    "lambda_total": 20.0,
    "p_hot": 0.7,
    "p_cold": 0.3,
    "revenue_hot": 3.0,
    "revenue_cold": 3.5,
    "cost_hot": 1.2,
    "cost_cold": 1.5,
    "salvage_hot": 0.0,
    "salvage_cold": 0.0,
    "beans_available": 60.0,
    "water_available": 60.0,
    "beans_hot": 1.0,
    "beans_cold": 1.0,
    "water_hot": 1.0,
    "water_cold": 1.0,
}


DYNAMIC = {
    "arrival_baseline_rate": 20.0,
    "arrival_reference_rate": 12.0,
    "reference_markup": 1.0,
    "markup_min": 0.0,
    "markup_max": 3.0,
    "balking_a": 2.0,
    "balking_b": -0.15,
    "multi_cup_theta": 0.5,
    "service_rate_base": 35.0,
    "service_rate_min": 30.0,
    "service_rate_max": 50.0,
    "service_cost_linear": 1.0,
    "hours": 6,
    "warmup_hours": 0,
    "replications": 1,
    "seed": 77,
    "coordinate_points": 3,
}


def test_health_and_metadata_expose_all_rounds():
    health = client.get("/health")
    assert health.status_code == 200
    metadata = client.get("/metadata").json()
    assert metadata["rounds"]["implemented"] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_api_solves_all_rounds_without_fake_calibration_pass():
    for round_number in range(1, 9):
        backend = "scipy" if round_number <= 4 else "simulation"
        response = client.post(
            "/solve",
            json={
                "round_number": round_number,
                "backend": backend,
                "scenario": BASE_SCENARIO,
                "dynamic": DYNAMIC,
            },
        )
        assert response.status_code == 200, response.text
        result = response.json()["result"]
        assert math.isfinite(float(result["objective"]))
        if round_number >= 5:
            assert result["operational"] is True
            assert result["formal_game_certified"] is False
