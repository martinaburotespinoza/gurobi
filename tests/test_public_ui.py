import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec("fastapi") is None,
    reason="fastapi not installed",
)


def test_public_ui_is_rendered_with_current_cockpit_contract():
    from fastapi.testclient import TestClient
    from api.ui import app

    response = TestClient(app).get("/")
    assert response.status_code == 200
    html = response.text

    assert "Decision Cockpit" in html
    assert "R1" in html and "R8" in html
    assert 'option value="scipy">SciPy · referencia pública' in html
    assert "gurobean-readable-ui" in html
    assert "/capture" in html


def test_public_ui_does_not_expose_r9_as_a_game_round():
    from fastapi.testclient import TestClient
    from api.ui import app

    html = TestClient(app).get("/").text
    assert "R9" not in html
