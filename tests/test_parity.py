from gurobean.parity import default_parity_cases, run_parity_suite


def test_default_parity_cases_are_deterministic_and_cover_all_rounds():
    a = default_parity_cases(seed=7, count=12)
    b = default_parity_cases(seed=7, count=12)
    assert a == b
    assert {c.round_number for c in a} == {1, 2, 3, 4}


def test_parity_suite_never_fakes_missing_gurobi():
    results = run_parity_suite(default_parity_cases(seed=9, count=4), pwl_points=101)
    assert len(results) == 4
    assert all(r.status == "skipped_gurobi_unavailable" for r in results) or all(r.passed for r in results)
