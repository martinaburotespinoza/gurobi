import importlib.util
import math

import pytest

fastapi_available = importlib.util.find_spec("fastapi") is not None
pytestmark = pytest.mark.skipif(not fastapi_available, reason="fastapi not installed")


def _payload(round_number=1):
    return {
        "round_number": round_number,
        "backend": "scipy" if round_number <= 4 else "simulation",
        "scenario": {
            "lambda_total": 100, "p_hot": 1, "p_cold": 0,
            "revenue_hot": 2, "revenue_cold": 2,
            "cost_hot": 0, "cost_cold": 0,
            "beans_available": 120, "water_available": 120,
            "beans_hot": 1, "beans_cold": 1, "water_hot": 1, "water_cold": 1,
        },
        "dynamic": {
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
            "hours": 2,
            "warmup_hours": 0,
            "replications": 1,
            "seed": 77,
            "coordinate_points": 3,
        },
    }


def test_health_and_solve():
    from fastapi.testclient import TestClient
    from api.app import app

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    r = client.post("/solve", json=_payload())
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_metadata_does_not_claim_license_availability():
    from fastapi.testclient import TestClient
    from api.app import app

    metadata = TestClient(app).get("/metadata").json()
    assert metadata["rounds"]["implemented"] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert metadata["rounds"]["formal_game_certification_required"] == [5, 6, 7, 8]
    assert metadata["gurobi_backend"] == "solver-backed-pwl-for-r1-r4"
    assert metadata["gurobi_license_required"] is True
    assert "formal game parity" in metadata["note"]


def test_dynamic_rounds_execute_operationally_without_fake_certification():
    from fastapi.testclient import TestClient
    from api.app import app

    for round_number in range(5, 9):
        response = TestClient(app).post("/solve", json=_payload(round_number=round_number))
        assert response.status_code == 200, response.text
        result = response.json()["result"]
        assert result["operational"] is True
        assert result["formal_game_certified"] is False
        assert math.isfinite(float(result["objective"]))


def test_invalid_drink_mix_is_rejected_at_api_boundary():
    from fastapi.testclient import TestClient
    from api.app import app

    payload = _payload()
    payload["scenario"]["p_hot"] = 0.8
    payload["scenario"]["p_cold"] = 0.3
    response = TestClient(app).post("/solve", json=payload)
    assert response.status_code == 422


def test_non_finite_scenario_value_is_rejected_by_api_schema():
    from api.app import ScenarioInput
    from pydantic import ValidationError

    for field, value in (("lambda_total", math.nan), ("revenue_hot", math.inf)):
        scenario = _payload()["scenario"]
        scenario[field] = value
        with pytest.raises(ValidationError):
            ScenarioInput.model_validate(scenario)
