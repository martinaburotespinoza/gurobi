from __future__ import annotations

import json
from pathlib import Path

from scripts.r9_end_to_end import main


def test_r9_end_to_end_reference_certification(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0

    artifact = json.loads(Path("r9_end_to_end.json").read_text(encoding="utf-8"))
    assert artifact["status"] == "PASS"
    assert artifact["total_cases"] == 400
    assert artifact["reference_failures"] == 0
    assert artifact["gurobi_failures"] == 0
    assert artifact["gurobi_gate"] in {"CHECKED", "NOT_AVAILABLE_IN_ENVIRONMENT"}


def test_r9_reference_covers_all_rounds():
    from scripts.r9_end_to_end import CASES, ROUNDS

    assert CASES == 100
    assert ROUNDS == (1, 2, 3, 4)
