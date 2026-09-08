import json
from pathlib import Path


def test_certification_manifest_cannot_claim_release_pass_without_final_gate():
    manifest = json.loads((Path(__file__).parents[1] / "certification_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] != "CERTIFIED_1000"
    assert manifest["anti_false_positive"]["missing_gurobi_is_pass"] is False
    assert manifest["anti_false_positive"]["synthetic_r5_r8_can_promote"] is False
    assert manifest["anti_false_positive"]["dirty_release_tree_can_certify"] is False
    assert manifest["anti_false_positive"]["pwl_only_can_certify"] is False
    assert manifest["gates"]["r9_release"] == "PENDING_LOCAL_LICENSED_RUN"
