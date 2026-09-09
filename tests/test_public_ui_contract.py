"""Regression tests for the current public HTML delivery layer."""

import inspect

from fastapi.testclient import TestClient

from api.ui import app
import api.ui as ui_module


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
    source = inspect.getsource(ui_module.ui)
    assert "fetch('/api/solve'" in source
    assert "fetch('/api/health'" in source
    assert "fetch('/api/evaluate'" in source
    assert "fetch('/api/ai/ask'" in source
    assert "gurobean-readable-ui" in html
