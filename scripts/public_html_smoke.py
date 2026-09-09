from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "web" / "index.html"


def main() -> None:
    text = HTML.read_text(encoding="utf-8")
    scripts = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", text, flags=re.DOTALL | re.IGNORECASE)
    if not scripts:
        raise SystemExit("PUBLIC HTML SMOKE: FAIL — no inline script found")
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
        raise SystemExit(f"PUBLIC HTML SMOKE: FAIL — JavaScript syntax error\n{result.stderr}")
    required = ("/api/health", "/api/solve", "/api/ai/ask", "addEventListener", "R1", "R8", "Decision Cockpit")
    missing = [token for token in required if token not in text]
    if missing:
        raise SystemExit(f"PUBLIC HTML SMOKE: FAIL — missing contract tokens: {missing}")
    print("PUBLIC HTML SMOKE: PASS")


if __name__ == "__main__":
    main()
