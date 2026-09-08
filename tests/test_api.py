import importlib.util
import math

import pytest

fastapi_available = importlib.util.find_spec("fastapi") is not None
pytestmark = pytest.mark.skipif(not fastapi_available, reason="fastapi not installed")


def _payload(round_number=1):
    return {
        "round_number": round_number,
        "backend": "scipy",
        "scenario": {
            "lambda_total": 100, "p_hot": 1, "p_cold": 0,
            "revenue_hot": 2, "revenue_cold": 2,
            "cost_hot": 0, "cost_cold": 0,
            "beans_available": 120, "water_available": 120,
            "beans_hot": 1, "beans_cold": 1, "water_hot": 1, "water_cold": 1,
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
    assert metadata["rounds"]["implemented"] == [1, 2, 3, 4]
    assert metadata["rounds"]["calibration_required"] == [5, 6, 7, 8]
    assert metadata["gurobi_backend"] == "solver-backed-pwl"
    assert metadata["gurobi_license_required"] is True
    assert "license availability" in metadata["note"]


def test_calibration_gated_round_is_not_silently_fallback_solved():
    from fastapi.testclient import TestClient
    from api.app import app

    response = TestClient(app).post("/solve", json=_payload(round_number=5))
    assert response.status_code == 501
    assert "calibration-gated" in response.json()["detail"]


def test_invalid_drink_mix_is_rejected_at_api_boundary():
    from fastapi.testclient import TestClient
    from api.app import app

    payload = _payload()
    payload["scenario"]["p_hot"] = 0.8
    payload["scenario"]["p_cold"] = 0.3
    response = TestClient(app).post("/solve", json=payload)
    assert response.status_code == 422


def test_non_finite_scenario_value_is_rejected_at_api_boundary():
    from fastapi.testclient import TestClient
    from api.app import app

    for field, value in (("lambda_total", math.nan), ("revenue_hot", math.inf)):
        payload = _payload()
        payload["scenario"][field] = value
        response = TestClient(app).post("/solve", json=payload)
        assert response.status_code == 422
