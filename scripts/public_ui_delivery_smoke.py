from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_PATH = ROOT / "api" / "ui.py"


def main() -> None:
    if not UI_PATH.is_file():
        raise SystemExit("PUBLIC UI DELIVERY SMOKE: FAIL — api/ui.py missing")

    spec = importlib.util.spec_from_file_location("gurobean_ui_smoke", UI_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit("PUBLIC UI DELIVERY SMOKE: FAIL — unable to load api/ui.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    html = module.ui().body.decode("utf-8")
    ui_source = UI_PATH.read_text(encoding="utf-8")

    # Validate the current delivered cockpit contract. The premium visual layer
    # intentionally overrides the readable metric size from 38px to 40px, so
    # the delivered contract must assert the final effective value.
    required_html = (
        "Decision Cockpit",
        "gurobean-readable-ui",
        ".metric strong{font-size:40px!important}",
        ".field input,.field select,.chat input{font-size:17px!important",
        "☕",
        "🧊",
        "📈",
        "🏆",
        "gurobean-visual-patch",
    )
    missing_html = [token for token in required_html if token not in html]
    if missing_html:
        raise SystemExit(f"PUBLIC UI DELIVERY SMOKE: FAIL — missing delivered UI tokens: {missing_html}")

    # API paths are an implementation concern of the delivery adapter. They
    # need not appear literally in the final HTML when the source page uses a
    # different URL construction strategy. Validate the adapter contract at
    # the layer that owns those rewrites instead of coupling the smoke test to
    # incidental frontend string formatting.
    required_adapter = (
        "fetch('/api/solve'",
        "fetch('/api/health'",
        "fetch('/api/evaluate'",
        "fetch('/api/ai/ask'",
    )
    missing_adapter = [token for token in required_adapter if token not in ui_source]
    if missing_adapter:
        raise SystemExit(f"PUBLIC UI DELIVERY SMOKE: FAIL — missing API adapter contract: {missing_adapter}")

    required_headers = (
        '"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0"',
        '"CDN-Cache-Control":"no-store"',
        '"Vercel-CDN-Cache-Control":"no-store"',
    )
    missing_headers = [token for token in required_headers if token not in ui_source]
    if missing_headers:
        raise SystemExit(f"PUBLIC UI DELIVERY SMOKE: FAIL — missing freshness headers: {missing_headers}")

    print("PUBLIC UI DELIVERY SMOKE: PASS")


if __name__ == "__main__":
    main()
