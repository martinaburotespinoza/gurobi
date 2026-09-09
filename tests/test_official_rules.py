import math

import pytest

from gurobean.official_rules import arrival_rate_from_markup, validate_r5_anchor_points


def test_r5_published_relationship_hits_both_anchors() -> None:
    baseline = 100.0
    reference = 25.0
    m0 = 3.0

    validate_r5_anchor_points(baseline, reference, m0)
    assert arrival_rate_from_markup(0.0, baseline, reference, m0) == pytest.approx(baseline)
    assert arrival_rate_from_markup(m0, baseline, reference, m0) == pytest.approx(reference)


def test_r5_relationship_is_monotone_when_reference_rate_is_lower() -> None:
    values = [
        arrival_rate_from_markup(m, 100.0, 25.0, 3.0)
        for m in (0.0, 1.0, 2.0, 3.0, 4.0, 6.0)
    ]
    assert all(a > b for a, b in zip(values, values[1:]))
    assert all(math.isfinite(value) and value > 0 for value in values)


@pytest.mark.parametrize(
    "markup,baseline,reference,m0",
    [
        (-1.0, 100.0, 25.0, 3.0),
        (1.0, 0.0, 25.0, 3.0),
        (1.0, 100.0, 0.0, 3.0),
        (1.0, 100.0, 25.0, 0.0),
        (math.nan, 100.0, 25.0, 3.0),
        (1.0, math.inf, 25.0, 3.0),
        (1.0, 100.0, 100.0, 3.0),
    ],
)
def test_r5_rejects_invalid_parameters(markup, baseline, reference, m0) -> None:
    with pytest.raises(ValueError):
        arrival_rate_from_markup(markup, baseline, reference, m0)
