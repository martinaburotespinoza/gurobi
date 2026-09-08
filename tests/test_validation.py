import math

from gurobean.validation import monte_carlo_newsvendor_check


def test_monte_carlo_matches_closed_form():
    r = monte_carlo_newsvendor_check(42.0, 40.0, 4.0, 1.5, samples=50_000, seed=9)
    assert r.passed
    assert r.z_score < 5.0


def test_monte_carlo_is_reproducible():
    a = monte_carlo_newsvendor_check(30.0, 25.0, 3.0, 1.0, samples=20_000, seed=77)
    b = monte_carlo_newsvendor_check(30.0, 25.0, 3.0, 1.0, samples=20_000, seed=77)
    assert a == b
