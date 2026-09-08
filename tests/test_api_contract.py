"""API contract tests for the public Gurobean Engine surface.

These tests intentionally verify the HTTP contract without requiring a live
Vercel deployment or a licensed Gurobi environment. The real-Gurobi release
gate remains separate and must never be inferred from these tests.
"""

from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def _scenario():
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


def test_health_contract():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "gurobean-engine"
    assert body["version"]


def test_metadata_exposes_certification_boundary():
    response = client.get("/metadata")
    assert response.status_code == 200
    body = response.json()
    assert body["rounds"]["implemented"] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert body["rounds"]["analytical_gurobi_certified"] == [1, 2, 3, 4]
    assert body["rounds"]["formal_game_certification_required"] == [5, 6, 7, 8]
    assert body["gurobi_license_required"] is True


def test_solve_r1_reference_contract():
    response = client.post(
        "/solve",
        json={
            "round_number": 1,
            "backend": "scipy",
            "scenario": _scenario(),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["round"] == 1
    assert isinstance(body["result"], dict)


def test_r5_rejects_gurobi_backend():
    response = client.post(
        "/solve",
        json={
            "round_number": 5,
            "backend": "gurobi",
            "scenario": _scenario(),
        },
    )
    assert response.status_code == 400
    assert "R5-R8" in response.json()["detail"]


def test_r5_simulation_contract():
    response = client.post(
        "/solve",
        json={
            "round_number": 5,
            "backend": "simulation",
            "scenario": _scenario(),
            "dynamic": {
                "hours": 2,
                "replications": 1,
                "coordinate_points": 3,
            },
        },
    )
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["operational"] is True
    assert result["formal_game_certified"] is False
    assert result["simulation_hours"] == 2
    assert result["replications"] == 1
    assert result["objective"] == result["expected_profit"]


def test_evaluate_contract():
    response = client.post(
        "/evaluate",
        json={
            "round_number": 8,
            "scenario": _scenario(),
            "q_hot": 5.0,
            "q_cold": 5.0,
            "markup": 1.0,
            "service_rate": 65.0,
            "replications": 1,
            "hours": 2,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["formal_game_certified"] is False
    assert body["evaluation"]["replications"] == 1


def test_invalid_probability_partition_is_rejected():
    scenario = _scenario()
    scenario["p_cold"] = 0.4
    response = client.post(
        "/solve",
        json={"round_number": 1, "backend": "scipy", "scenario": scenario},
    )
    assert response.status_code == 422
    assert "p_hot + p_cold" in response.json()["detail"][0]["msg"]
