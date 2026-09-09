from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def test_r2_cockpit_contains_editable_hot_cold_distribution_controls():
    text = (ROOT / "web" / "r2-cockpit.html").read_text(encoding="utf-8")
    assert "Café caliente" in text
    assert "Café frío" in text
    assert 'id="hot"' in text
    assert 'id="cold"' in text
    for preset in ('data-hot="75"', 'data-hot="50"', 'data-hot="25"', 'data-hot="100"'):
        assert preset in text
    assert "p_hot" in text
    assert "p_cold" in text
    assert "100 %" in text


def test_root_routes_to_r2_cockpit_and_api_allows_same_origin_embedding():
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    rewrites = config["rewrites"]
    assert {r["source"]: r["destination"] for r in rewrites}["/"] == "/web/r2-cockpit.html"
    headers = config["headers"]
    api_headers = next(item for item in headers if item["source"] == "/api/(.*)")["headers"]
    assert {h["key"]: h["value"] for h in api_headers}["X-Frame-Options"] == "SAMEORIGIN"


def test_r2_cockpit_preserves_7525_default_and_validates_total():
    text = (ROOT / "web" / "r2-cockpit.html").read_text(encoding="utf-8")
    assert 'value="75"' in text
    assert 'value="25"' in text
    assert "Math.abs(sum-100)<1e-9" in text
    assert "data.round_number)===2" in text
    assert "data.scenario.p_hot" in text
    assert "data.scenario.p_cold" in text


def test_live_cockpit_clarifies_r1_units_and_service_capacity():
    text = (ROOT / "web" / "r2-cockpit.html").read_text(encoding="utf-8")
    for marker in (
        "Gramos de café por café caliente",
        "Onzas de agua por café caliente",
        "Café disponible (gramos/hora)",
        "Agua disponible (onzas/hora)",
        "Capacidad de servicio (clientes/hora por barista)",
        "Demanda λ (clientes/hora)",
    ):
        assert marker in text
