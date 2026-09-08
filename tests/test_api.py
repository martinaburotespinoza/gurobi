import importlib.util
import pytest

fastapi_available = importlib.util.find_spec("fastapi") is not None
pytestmark = pytest.mark.skipif(not fastapi_available, reason="fastapi not installed")


def test_health_and_solve():
    from fastapi.testclient import TestClient
    from api.app import app

    client = TestClient(app)
    assert client.get("/health").status_code == 200
    payload = {
        "round_number": 1,
        "backend": "scipy",
        "scenario": {
            "lambda_total": 100, "p_hot": 1, "p_cold": 0,
            "revenue_hot": 2, "revenue_cold": 2,
            "cost_hot": 0, "cost_cold": 0,
            "beans_available": 120, "water_available": 120,
            "beans_hot": 1, "beans_cold": 1, "water_hot": 1, "water_cold": 1,
        },
    }
    r = client.post("/solve", json=payload)
    assert r.status_code == 200
    assert r.json()["ok"] is True
