from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "web" / "index.html"
CAPTURE = ROOT / "web" / "capture.html"


def _read(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"PUBLIC UI SMOKE: FAIL — missing {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    app = _read(APP)
    capture = _read(CAPTURE)

    required_rounds = [f"{i}:{{" for i in range(1, 9)]
    missing_rounds = [token for token in required_rounds if token not in app]
    if missing_rounds:
        raise SystemExit(f"PUBLIC UI SMOKE: FAIL — missing round definitions: {missing_rounds}")

    required_ids = (
        "solve", "compare", "copy", "ask", "question", "fields", "roundGrid",
        "progressDots", "navHome", "compareNav", "monteNav", "customNav", "assistantNav",
        "assistantCard", "apiState", "apiRow", "gurobiState", "gurobiRow", "result",
        "releaseState", "note",
    )
    missing_ids = [f'id="{item}"' for item in required_ids if f'id="{item}"' not in app]
    if missing_ids:
        raise SystemExit(f"PUBLIC UI SMOKE: FAIL — missing app controls: {missing_ids}")

    required_handlers = (
        "$('solve').addEventListener('click',solve)",
        "$('compare').addEventListener('click',compare)",
        "$('copy').addEventListener('click'",
        "$('ask').addEventListener('click',ask)",
        "$('question').addEventListener('keydown'",
        "$('customNav').addEventListener('click',custom)",
        "$('assistantNav').addEventListener('click'",
        "$('compareNav').addEventListener('click',compare)",
        "$('monteNav').addEventListener('click'",
        "$('navHome').addEventListener('click'",
        "data-nav-round",
    )
    missing_handlers = [token for token in required_handlers if token not in app]
    if missing_handlers:
        raise SystemExit(f"PUBLIC UI SMOKE: FAIL — missing handlers: {missing_handlers}")

    for endpoint in ("api+'/health'", "api+'/solve'", "api+'/evaluate'", "api+'/ai/ask'"):
        if endpoint not in app:
            raise SystemExit(f"PUBLIC UI SMOKE: FAIL — app missing endpoint contract {endpoint}")

    for round_number in range(1, 9):
        if f"data-nav-round=\"{round_number}\"" not in app:
            raise SystemExit(f"PUBLIC UI SMOKE: FAIL — missing navigation for R{round_number}")

    capture_required = (
        "saveObs", "exportJSON", "exportCSV", "clearAll",
        "localStorage", "gurobean_live_game_observations_v1",
        "gurobean_game_observations.json", "gurobean_game_observations.csv",
    )
    missing_capture = [token for token in capture_required if token not in capture]
    if missing_capture:
        raise SystemExit(f"PUBLIC UI SMOKE: FAIL — capture contract incomplete: {missing_capture}")

    inline_buttons = re.findall(r"onclick=\"([^\"]+)\"", capture)
    for handler in ("saveObs()", "exportJSON()", "exportCSV()", "clearAll()"):
        if handler not in inline_buttons:
            raise SystemExit(f"PUBLIC UI SMOKE: FAIL — capture action not wired: {handler}")

    if "R5–R8: Monte Carlo operacional" not in (ROOT / "index.html").read_text(encoding="utf-8"):
        raise SystemExit("PUBLIC UI SMOKE: FAIL — root console certification boundary missing")

    print("PUBLIC UI SMOKE: PASS — controls, handlers, R1-R8 navigation, API contracts, and live-capture actions verified")


if __name__ == "__main__":
    main()
