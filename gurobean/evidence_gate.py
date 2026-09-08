from __future__ import annotations

"""Strict evidence gate for promoting calibrated R5-R8 behavior.

A fitted response is never sufficient by itself. Promotion requires observations
whose provenance is explicitly the real game. Synthetic, generated, demo, or
unspecified provenance is rejected before the existing statistical gate runs.
"""

from typing import Sequence

from .calibration import FitResult, Observation, PromotionDecision, calibration_gate

ALLOWED_GAME_SOURCES = frozenset({"game", "game_capture", "game_observation"})


def strict_calibration_gate(
    observations: Sequence[Observation],
    results: Sequence[FitResult],
    *,
    min_observations: int = 8,
    max_rmse: float | None = None,
    require_monotone: bool = False,
) -> PromotionDecision:
    """Apply provenance validation before statistical calibration promotion."""
    if not observations:
        return PromotionDecision(False, 0, None, "no_observations", {})

    rounds = {o.round_number for o in observations}
    if len(rounds) != 1 or next(iter(rounds)) not in (5, 6, 7, 8):
        return PromotionDecision(False, 0, None, "mixed_or_invalid_rounds", {})

    round_number = next(iter(rounds))
    invalid_sources = sorted({o.source for o in observations if o.source not in ALLOWED_GAME_SOURCES})
    if invalid_sources:
        return PromotionDecision(
            False,
            round_number,
            None,
            "non_game_observation_source",
            {"invalid_source_count": float(len(invalid_sources))},
        )

    if not results or any(r.round_number != round_number for r in results):
        return PromotionDecision(False, round_number, None, "fit_round_mismatch", {})

    return calibration_gate(
        observations,
        results,
        min_observations=min_observations,
        max_rmse=max_rmse,
        require_monotone=require_monotone,
    )
