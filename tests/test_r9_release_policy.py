from scripts import r9_release


def test_release_gate_is_stricter_than_exploratory_pwl_tolerance():
    assert r9_release.OBJ_TOL <= 1e-4
    assert r9_release.REFINE_POINTS == (5001, 10001, 20001)


def test_release_gate_is_explicitly_r5_r8_gated():
    assert r9_release.ARTIFACT.name == "r9_release_certification.json"
