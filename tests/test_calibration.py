import math

from gurobean.calibration import (
    CalibrationDataset,
    Observation,
    best_fit,
    fit_r5_arrival_rate,
    fit_r6_balking,
    fit_r7_order_size,
    fit_r8_service_cost,
)


def test_r5_fit_recovers_monotone_exponential_candidate():
    ds = CalibrationDataset()
    for m in [0, 1, 2, 3, 4]:
        ds.add(Observation(5, {"markup": m}, {"arrival_rate": 100 * math.exp(-0.2 * m)}))
    best = best_fit(fit_r5_arrival_rate(ds.for_round(5)))
    assert best.family == "exponential"


def test_r6_fit_is_data_driven():
    ds = CalibrationDataset()
    for q in [0, 1, 2, 3, 4]:
        p = 1 / (1 + math.exp(-1.5 + 0.7 * q))
        ds.add(Observation(6, {"queue": q}, {"stay_probability": p}))
    result = fit_r6_balking(ds.for_round(6))[0]
    assert result.family == "logistic"
    assert result.parameters["b"] < 0


def test_r7_candidates_are_ranked_without_hardcoding_a_distribution():
    ds = CalibrationDataset()
    for k in [1, 1, 2, 2, 2, 3, 3, 4]:
        ds.add(Observation(7, {}, {"order_size": k}))
    results = fit_r7_order_size(ds.for_round(7))
    assert {r.family for r in results} == {"shifted_poisson", "geometric"}


def test_r8_compares_cost_families():
    ds = CalibrationDataset()
    for mu in [50, 60, 70, 80]:
        ds.add(Observation(8, {"service_rate": mu}, {"barista_cost_per_hour": 10 + 0.02 * mu * mu}))
    results = fit_r8_service_cost(ds.for_round(8))
    assert results[0].family == "quadratic"
