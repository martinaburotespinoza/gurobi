from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gurobean.validation import monte_carlo_newsvendor_check
from gurobean.simulation import simulate_queue


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    checks = []
    checks.append(monte_carlo_newsvendor_check(25.0, 25.0, 1.0, 0.0, samples=100_000, seed=101).to_dict())
    checks.append(monte_carlo_newsvendor_check(42.0, 40.0, 4.0, 1.5, samples=100_000, seed=102).to_dict())
    sim = simulate_queue(10.0, 15.0, hours=120, warmup_hours=10, seed=103)
    checks.append({"simulation": sim.__dict__})
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=root, capture_output=True, text=True)
    report = {"monte_carlo": checks[:2], "simulation": checks[2], "pytest_returncode": result.returncode, "pytest_stdout": result.stdout.strip()}
    Path(root / "validation_report.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))
    return result.returncode if result.returncode else (0 if all(c["passed"] for c in checks[:2]) else 2)

if __name__ == "__main__":
    raise SystemExit(main())
