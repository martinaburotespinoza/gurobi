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

    # The artifact schema evolved from an implicit gate state to an explicit
    # `gurobi_gate` field.  Accept the legacy representation only when it is
    # unambiguously derivable from the recorded solver-case count; never infer
    # a Gurobi PASS from the overall R9 status alone.
    gate = artifact.get("gurobi_gate")
    if gate is None:
        gate = (
            "CHECKED"
            if artifact["gurobi_cases_checked"] > 0
            else "NOT_AVAILABLE_IN_ENVIRONMENT"
        )
    assert gate in {"CHECKED", "NOT_AVAILABLE_IN_ENVIRONMENT"}

    if artifact.get("require_gurobi", False):
        assert artifact["gurobi_cases_checked"] == 400
        assert gate == "CHECKED"
