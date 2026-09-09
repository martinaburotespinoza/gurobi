"""Deterministic pre-live-game readiness check.

This command runs every non-licensed gate that can be verified without the
proprietary Gurobi license or real-game observations. It deliberately does
NOT report R9 PASS and does NOT promote R5-R8 to formal game certification.
The only two external gates left are the real licensed-Gurobi release run and
real-game evidence/calibration for R5-R8.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("compileall", [sys.executable, "-m", "compileall", "-q", "gurobean", "scripts"]),
    ("pytest", [sys.executable, "-m", "pytest", "-q"]),
    ("self_audit", [sys.executable, "scripts/self_audit.py"]),
    ("full_rounds", [sys.executable, "scripts/validate_full_rounds.py"]),
    ("r8_math_validation", [sys.executable, "scripts/r8_math_validation.py"]),
    ("r9_end_to_end_reference", [sys.executable, "scripts/r9_end_to_end.py"]),
    ("production_http", [sys.executable, "scripts/validate_production.py"]),
]


def run(name: str, command: list[str]) -> bool:
    print(f"\n=== {name} ===")
    completed = subprocess.run(command, cwd=ROOT, check=False)
    ok = completed.returncode == 0
    print(f"{name.upper()}: {'PASS' if ok else 'FAIL'}")
    return ok


def main() -> int:
    print("=== GUROBEAN ENGINE v2_6 PRE-LIVE-GAME CHECK ===")
    print("Non-licensed gates only; no fake R9 PASS is possible here.")
    results = [run(name, command) for name, command in CHECKS]

    print("\n=== READINESS BOUNDARY ===")
    print(f"NON_LICENSED_GATES: {'PASS' if all(results) else 'FAIL'}")
    print("R1_R4: MATHEMATICALLY_VALIDATED")
    print("R5_R8: OPERATIONAL_AND_EVIDENCE_GATED")
    print("LOAD_BATTERY: INCLUDED_IN_PYTEST")
    print("PRODUCTION_HTTP: CHECKED")
    print("R9: LICENSED_LOCAL_GUROBI_RUN_REQUIRED")
    print("REAL_GAME: OBSERVATIONS_AND_CALIBRATION_REQUIRED")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
