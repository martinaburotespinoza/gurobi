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
    required = (
        "Decision Cockpit",
        "gurobean-readable-ui",
        ".metric strong{font-size:24px!important}",
        ".field input,.field select,.chat input{font-size:13px!important",
        "/api/solve",
        "/api/health",
    )
    missing = [token for token in required if token not in html]
    if missing:
        raise SystemExit(f"PUBLIC UI DELIVERY SMOKE: FAIL — missing delivered UI tokens: {missing}")

    print("PUBLIC UI DELIVERY SMOKE: PASS")


if __name__ == "__main__":
    main()
