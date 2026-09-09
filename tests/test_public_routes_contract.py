from pathlib import Path

from fastapi.testclient import TestClient

from api.ui import app as ui_app

ROOT = Path(__file__).resolve().parents[1]


def test_vercel_routes_expose_capture_and_pin_fastapi_entrypoint():
    text = (ROOT / "vercel.json").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'entrypoint = "api.index:app"' in pyproject
    assert '"source":"/capture"' in text
    assert '"destination":"/web/capture.html"' in text
    assert '"source":"/api/:path*"' not in text
    assert '"source":"/"' not in text


def test_public_ui_is_not_empty_and_has_eight_rounds():
    response = TestClient(ui_app).get("/")
    assert response.status_code == 200
    text = response.text
    assert len(text) > 10000
    assert "Decision Cockpit" in text
    assert "R1" in text and "R8" in text
    assert "R9" not in text
    assert "gurobean-readable-ui" in text


def test_capture_page_is_present():
    text = (ROOT / "web" / "capture.html").read_text(encoding="utf-8")
    assert len(text) > 5000
    assert "game_observation" in text
    assert "localStorage" in text
