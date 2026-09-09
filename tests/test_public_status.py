from fastapi.testclient import TestClient

from api.index import app


client = TestClient(app)


def test_public_status_is_truthful_and_never_fabricates_release_pass():
    response = client.get("/status")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["service"] == "gurobean-engine"
    readiness = body["readiness"]
    assert readiness["r5_r8_calibration_gated"] is True
    assert body["truth_policy"]["missing_gurobi_is_pass"] is False
    assert body["truth_policy"]["synthetic_evidence_can_promote"] is False
    assert body["truth_policy"]["r9_artifact_must_match_current_head"] is True


def test_public_status_exposes_all_eight_rounds_via_metadata():
    response = client.get("/metadata")
    assert response.status_code == 200
    rounds = response.json()["rounds"]
    assert rounds["implemented"] == list(range(1, 9))
    assert rounds["analytical_gurobi_certified"] == [1, 2, 3, 4]
    assert rounds["simulation_enabled"] == [5, 6, 7, 8]
