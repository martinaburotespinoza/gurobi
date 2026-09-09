import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.index import app as ui_app

ROOT = Path(__file__).resolve().parents[1]


def test_vercel_routes_expose_capture_without_root_framework_rewrite():
    text = (ROOT / "vercel.json").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'entrypoint = "api.index:app"' in pyproject
    assert '"source":"/capture"' in text
    assert '"destination":"/web/capture.html"' in text
    assert '"source":"/api/:path*"' not in text

    config = json.loads(text)
    rewrites = {item["source"]: item["destination"] for item in config["rewrites"]}
    assert rewrites["/capture"] == "/web/capture.html"
    assert rewrites["/capture/"] == "/web/capture.html"
    assert "/" not in rewrites


def test_static_root_is_the_decision_cockpit_entrypoint():
    root = ROOT / "index.html"
    assert root.is_file()
    text = root.read_text(encoding="utf-8")
    required = [
        "Decision Cockpit",
        "ROUND 2 · DISTRIBUCIÓN DE DEMANDA",
        'src=\"/api/\"',
        "Café caliente",
        "Café frío",
        "p_hot",
        "p_cold",
        "75 / 25",
        "50 / 50",
        "25 / 75",
        "100 / 0",
    ]
    missing = [marker for marker in required if marker not in text]
    assert not missing, missing


def test_r2_cockpit_is_served_by_fastapi_entrypoint():
    response = TestClient(ui_app).get("/r2-cockpit")
    assert response.status_code == 200
    text = response.text
    required = [
        "ROUND 2 · DISTRIBUCIÓN DE DEMANDA",
        "Café caliente",
        "Café frío",
        "p_hot",
        "p_cold",
        "75 / 25",
        "50 / 50",
        "25 / 75",
        "100 / 0",
    ]
    missing = [marker for marker in required if marker not in text]
    assert not missing, missing


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
