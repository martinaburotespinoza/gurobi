"""Deterministic local audit for Gurobean Engine v2_6.

Runs only checks that do not require a licensed Gurobi installation or real-game
observations. It is intentionally conservative: a successful audit means the
software surface is internally coherent, never that live-game parity is proven.
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_MODULES = (
    "gurobean.model",
    "gurobean.validation",
    "gurobean.simulation",
    "gurobean.evaluation",
    "gurobean.full_rounds",
    "gurobean.calibration",
    "gurobean.evidence_gate",
    "gurobean.assistant",
    "api.app",
)
REQUIRED_SCRIPTS = (
    "scripts/self_audit.py",
    "scripts/validate_all.py",
    "scripts/r8_math_validation.py",
    "scripts/r9_end_to_end.py",
    "scripts/pre_live_game_check.py",
    "scripts/check_gurobi.py",
    "scripts/r9_release.py",
    "scripts/final_live_test_gate.py",
)


def run(cmd: list[str]) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def main() -> int:
    failures: list[str] = []
    print("=== GUROBEAN ENGINE v2_6 — SYSTEM AUDIT ===")
    print(f"PYTHON: {sys.version.split()[0]}")

    for module in REQUIRED_MODULES:
        try:
            importlib.import_module(module)
            print(f"MODULE: PASS {module}")
        except Exception as exc:  # pragma: no cover - diagnostic boundary
            failures.append(f"module {module}: {type(exc).__name__}: {exc}")
            print(f"MODULE: FAIL {module}: {type(exc).__name__}: {exc}")

    for relative in REQUIRED_SCRIPTS:
        path = ROOT / relative
        if path.is_file():
            print(f"SCRIPT: PASS {relative}")
        else:
            failures.append(f"missing script {relative}")
            print(f"SCRIPT: FAIL {relative}")

    rc, output = run([sys.executable, "-m", "compileall", "-q", "gurobean", "api", "scripts"])
    if rc == 0:
        print("COMPILEALL: PASS")
    else:
        failures.append("compileall failed")
        print("COMPILEALL: FAIL")
        print(output)

    rc, output = run([sys.executable, "-m", "pytest", "-q", "tests"])
    if rc == 0:
        print("PYTEST: PASS")
        print(output.splitlines()[-1] if output else "")
    else:
        failures.append("pytest failed")
        print("PYTEST: FAIL")
        print(output[-4000:])

    manifest = ROOT / "certification_manifest.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("manifest root must be an object")
            print("MANIFEST: PASS")
        except Exception as exc:
            failures.append(f"manifest invalid: {exc}")
            print(f"MANIFEST: FAIL {exc}")
    else:
        failures.append("certification manifest missing")
        print("MANIFEST: FAIL")

    print("R9_LICENSED_GATE: EXTERNAL")
    print("R5_R8_GAME_PARITY: EVIDENCE_GATED")
    if failures:
        print(f"STATUS: FAIL ({len(failures)} blockers)")
        for failure in failures:
            print(f"BLOCKER: {failure}")
        return 1
    print("STATUS: PASS — NON-LICENSED SOFTWARE AUDIT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
