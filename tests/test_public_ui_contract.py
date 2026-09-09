"""Regression tests for the current public HTML delivery layer."""

from fastapi.testclient import TestClient

from api.ui import app


def test_public_ui_renders_current_cockpit_without_r9_round():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    html = response.text
    assert "Decision Cockpit" in html
    assert "R1" in html and "R8" in html
    assert "gurobean-readable-ui" in html
    assert "Q hot" in html and "Q cold" in html
    assert "R9" not in html


def test_public_ui_exposes_safe_reference_backend_contract():
    html = TestClient(app).get("/").text
    assert "/api/solve" in html
    assert "/api/health" in html
    assert "/api/ai/ask" in html
