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
    assert "R9" not in html


def test_public_ui_exposes_safe_reference_backend_contract():
    html = TestClient(app).get("/").text
    assert 'option value="scipy">SciPy · referencia pública' in html
    assert "La comparación formal Gurobi ↔ SciPy requiere" in html
