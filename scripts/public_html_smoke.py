from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "web" / "index.html"
ROOT_HTML = ROOT / "index.html"
UI = ROOT / "api" / "ui.py"


def check_js(text: str, label: str) -> None:
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", text, flags=re.DOTALL | re.IGNORECASE)
    if not scripts:
        raise SystemExit(f"PUBLIC HTML SMOKE: FAIL — no inline script found in {label}")
    node = shutil.which("node")
    if not node:
        raise SystemExit("PUBLIC HTML SMOKE: FAIL — Node.js is required")
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
        handle.write("\n".join(scripts))
        script_path = handle.name
    try:
        result = subprocess.run([node, "--check", script_path], capture_output=True, text=True)
    finally:
        Path(script_path).unlink(missing_ok=True)
    if result.returncode != 0:
        raise SystemExit(f"PUBLIC HTML SMOKE: FAIL — JavaScript syntax error in {label}\n{result.stderr}")


def main() -> None:
    text = HTML.read_text(encoding="utf-8")
    root_text = ROOT_HTML.read_text(encoding="utf-8")
    ui_text = UI.read_text(encoding="utf-8")
    check_js(text, "web/index.html")
    check_js(root_text, "index.html")

    required_html = ("addEventListener", "R1", "R8", "Decision Cockpit")
    missing_html = [token for token in required_html if token not in text]
    if missing_html:
        raise SystemExit(f"PUBLIC HTML SMOKE: FAIL — missing HTML tokens: {missing_html}")

    required_root = (
        "Decision Cockpit",
        "ROUND 2 · DISTRIBUCIÓN DE DEMANDA",
        'src=\"/api/\"',
        'id=\"hot\"',
        'id=\"cold\"',
        "p_hot",
        "p_cold",
        "75 / 25",
        "50 / 50",
        "25 / 75",
        "100 / 0",
        "Math.abs(sum-100)<1e-9",
        "data.round_number)===2",
    )
    missing_root = [token for token in required_root if token not in root_text]
    if missing_root:
        raise SystemExit(f"PUBLIC HTML SMOKE: FAIL — missing static root cockpit tokens: {missing_root}")

    required_ui = (
        "READABLE_UI",
        "gurobean-readable-ui",
        "font-size:16px!important",
        "@app.get(\"/\")",
        "HTMLResponse",
    )
    missing_ui = [token for token in required_ui if token not in ui_text]
    if missing_ui:
        raise SystemExit(f"PUBLIC HTML SMOKE: FAIL — missing UI delivery tokens: {missing_ui}")

    api_contract = (ROOT / "api" / "app.py").read_text(encoding="utf-8")
    required_api = ("/health", "/solve", "/ai/ask")
    missing_api = [token for token in required_api if token not in api_contract]
    if missing_api:
        raise SystemExit(f"PUBLIC HTML SMOKE: FAIL — missing API contract tokens: {missing_api}")

    print("PUBLIC HTML SMOKE: PASS")


if __name__ == "__main__":
    main()
