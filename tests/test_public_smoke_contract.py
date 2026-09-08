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


def _payload(round_number, backend):
    return {
        "round_number": round_number,
        "backend": backend,
        "scenario": _scenario(),
        "dynamic": {
            "arrival_reference_rate": 20.0,
            "hours": 2,
            "replications": 1,
            "coordinate_points": 3,
        },
    }


def test_public_health_contract():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json().get("status") == "ok"


def test_public_metadata_has_exactly_r1_to_r8():
    response = client.get("/metadata")
    assert response.status_code == 200
    rounds = response.json().get("rounds", {})
    assert rounds["implemented"] == list(range(1, 9))
    assert rounds["analytical_gurobi_certified"] == [1, 2, 3, 4]
    assert rounds["simulation_enabled"] == [5, 6, 7, 8]
    assert rounds["formal_game_certification_required"] == [5, 6, 7, 8]


def test_public_r1_reference_executes():
    response = client.post("/solve", json=_payload(1, "scipy"))
    assert response.status_code == 200, response.text
    assert response.json().get("round") == 1
    assert response.json().get("ok") is True


def test_public_r5_simulation_executes():
    response = client.post("/solve", json=_payload(5, "simulation"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("round") == 5
    assert body.get("result", {}).get("operational") is True


def test_public_r8_simulation_executes():
    response = client.post("/solve", json=_payload(8, "simulation"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("round") == 8
    assert body.get("result", {}).get("operational") is True
