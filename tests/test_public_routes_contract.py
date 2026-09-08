from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_routes_expose_app_and_capture():
    text = (ROOT / 'vercel.json').read_text(encoding='utf-8')
    assert '"/api/(.*)"' in text
    assert '"/app"' in text
    assert '"/"' in text
    assert '"/capture"' in text


def test_public_ui_is_not_empty_and_has_eight_rounds():
    text = (ROOT / 'web' / 'index.html').read_text(encoding='utf-8')
    assert len(text) > 10000
    assert 'R1' in text and 'R8' in text
    assert 'R9' not in text
    assert 'Modo Personalizado' in text or 'Personalizado' in text


def test_capture_page_is_present():
    text = (ROOT / 'web' / 'capture.html').read_text(encoding='utf-8')
    assert len(text) > 5000
    assert 'game_observation' in text
    assert 'localStorage' in text
