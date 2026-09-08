# Gurobean R5-R8 calibration protocol

The engine will not invent the unknown game functions. Calibration is driven by observations collected from the real game.

## R5 — markup → arrival rate

For fixed non-price conditions, collect multiple observations of:

- markup `m`
- observed customer arrival rate `lambda`
- hot/cold split
- run identifier and scenario/day

Candidate families currently implemented: linear and exponential. The winning family is selected by information criterion; it is not assumed beforehand.

## R6 — congestion → balking

Collect observations of queue length or waiting time and the fraction of arriving customers who stay.

Current candidate: logistic response. More families can be added if the residuals show systematic misspecification.

## R7 — order size

Record every observed customer order size. The calibration layer compares shifted-Poisson and positive-geometric distributions using likelihood/AIC. Empirical frequencies remain available for a nonparametric fallback.

## R8 — service rate → hourly barista cost

For fixed conditions, collect service rate `mu` and observed hourly barista cost. Compare linear and quadratic curves. Do not hard-code a cost function until observations support it.

## Data quality gates

A fitted function may only enter the optimizer after:

1. minimum sample size is reached;
2. repeated runs/scenarios are present;
3. out-of-sample error is acceptable;
4. residuals show no material systematic pattern;
5. the fitted function respects known monotonicity/domain constraints;
6. the calibrated function reproduces observed game outputs within tolerance.

Calibration is therefore a controlled identification stage, not a license to guess equations.
