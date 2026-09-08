from __future__ import annotations

import random

from scripts.r8_math_validation import _scenario, audit_case


def test_r8_seeded_mathematical_cases_pass():
    rng = random.Random(802026)
    results = [audit_case(i, _scenario(rng)) for i in range(12)]
    assert all(result.passed for result in results), [result.error or result.checks for result in results if not result.passed]
