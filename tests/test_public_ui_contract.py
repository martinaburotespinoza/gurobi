"""Regression tests for the public HTML adapter."""

from fastapi.testclient import TestClient

from api.ui import app


def test_public_ui_renders_and_keeps_release_gate_out_of_rounds():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    html = response.text
    assert "Modo Juego · R1 → R8" in html
    assert "Modo Personalizado" in html
    assert "Ronda 1 de 8" in html
    assert "R9 no es una ronda" not in html
    assert "R9 = release gate" not in html
    assert "certificación final = release gate" in html
    assert "Capturar juego en vivo" in html


def test_public_ui_routes_gurobi_to_reference_backend():
    html = TestClient(app).get("/").text
    assert "if(body.backend==='gurobi') body.backend='scipy'" in html
    assert "arrival_reference_rate:Math.min(36,v('lambda_total',60))" in html
