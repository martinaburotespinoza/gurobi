import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("fastapi") is None,
    reason="fastapi not installed",
)


def test_public_ui_is_rendered_with_safe_backend_defaults():
    from fastapi.testclient import TestClient
    from api.ui import app

    response = TestClient(app).get("/")
    assert response.status_code == 200
    html = response.text

    assert "Modo Juego · R1 → R8" in html
    assert "Modo Personalizado" in html
    assert 'option value="scipy">SciPy · referencia pública' in html
    assert "Math.min(36,v('lambda_total',60))" in html
    assert "/capture" in html
    assert "/api/health" in html
    assert "body.backend==='gurobi'" in html
    assert "body.backend='scipy'" in html
    assert "body.backend==='simulation'&&body.round_number===4" in html
    assert "body.round_number=8" in html


def test_public_ui_does_not_expose_r9_as_a_game_round():
    from fastapi.testclient import TestClient
    from api.ui import app

    html = TestClient(app).get("/").text
    assert "R9" not in html
