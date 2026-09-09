from fastapi.testclient import TestClient

from api.app import app


def test_status_exposes_truthful_readiness_without_r9_artifact(monkeypatch, tmp_path):
    import api.public_router as public_router

    monkeypatch.setattr(public_router, "ROOT", tmp_path)
    (tmp_path / "certification_manifest.json").write_text(
        '{"release_line":"r9-1000-certification","status":"POST_PATCH_VALIDATION_REQUIRED",'
        '"gates":{"r1_r4_reference":"PASS","r8_core_math_validation":"PASS",'
        '"r9_release":"PENDING"}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(public_router, "_git_head", lambda: "abc123")
    monkeypatch.setattr(public_router, "_git_dirty", lambda: [])
    monkeypatch.setattr(
        public_router,
        "_gurobi",
        lambda: {"available": False, "version": None, "licensed": False},
    )

    payload = TestClient(app).get("/status").json()
    assert payload["ok"] is True
    assert payload["readiness"]["approved_for_live_game_test"] is False
    assert payload["readiness"]["r9_release"] is False
    assert payload["certification"]["r9_artifact"]["status"] == "MISSING"
    assert payload["truth_policy"]["missing_gurobi_is_pass"] is False


def test_status_can_approve_only_with_current_400_case_r9_artifact(monkeypatch, tmp_path):
    import api.public_router as public_router

    monkeypatch.setattr(public_router, "ROOT", tmp_path)
    (tmp_path / "certification_manifest.json").write_text(
        '{"release_line":"r9-1000-certification","status":"PASS",'
        '"gates":{"r1_r4_reference":"PASS","r8_core_math_validation":"PASS",'
        '"r9_release":"PASS","r5_markup_published_relationship":"CALIBRATION_GATED",'
        '"r6_balking":"CALIBRATION_GATED","r7_multi_cup":"CALIBRATION_GATED",'
        '"r8_service_rate":"CALIBRATION_GATED"}}',
        encoding="utf-8",
    )
    (tmp_path / "r9_release_certification.json").write_text(
        '{"status":"PASS","git_commit":"abc123","gurobi_gate":"CHECKED",'
        '"cases_checked":400,"failures":0}',
        encoding="utf-8",
    )
    monkeypatch.setattr(public_router, "_git_head", lambda: "abc123")
    monkeypatch.setattr(public_router, "_git_dirty", lambda: [])
    monkeypatch.setattr(
        public_router,
        "_gurobi",
        lambda: {"available": True, "version": "13.0.0", "licensed": True},
    )

    payload = TestClient(app).get("/status").json()
    assert payload["readiness"]["approved_for_live_game_test"] is True
    assert payload["readiness"]["r9_release"] is True
    assert payload["readiness"]["r5_r8_calibration_gated"] is True
