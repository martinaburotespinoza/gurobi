# Gurobean mathematical specification

## Authority

The normative game definition is the official Gurobi Game Guide. It states that Gurobean uses Poisson arrivals, splits arrivals into hot/cold demand, approximates hourly demand by a Normal distribution with the same mean and variance for optimization, and builds the objective from a newsvendor formulation. It also states the progression of rounds 1–8: brewing, brewing cost, markup, balking, multi-cup orders, and service-rate/barista cost.

Source: https://www.gurobi.com/academics/gurobean/game-guide

## R1–R4 certified mathematical core

For drink type `i`, with arrival rate `lambda_i`, decision `Q_i`, unit revenue `r_i`, and unit brewing cost `c_i`:

- `D_i ~ Normal(lambda_i, lambda_i)` for the optimization approximation.
- `z_i = (Q_i - lambda_i) / sqrt(lambda_i)` when `lambda_i > 0`.
- `E[min(Q_i,D_i)] = lambda_i Phi(z_i) - sqrt(lambda_i) phi(z_i) + Q_i (1-Phi(z_i))`.
- `E[(Q_i-D_i)^+] = (Q_i-lambda_i) Phi(z_i) + sqrt(lambda_i) phi(z_i)`.
- `profit_i = r_i E[min(Q_i,D_i)] - c_i Q_i`.

The official game treats unused brewed coffee as waste, so the production R1-R4 certification uses zero salvage value. The model code retains a zero-default salvage field only as a generic mathematical extension; positive salvage is not part of the Gurobean certification scenarios.

The hot/cold probabilities form a complete partition: `p_hot + p_cold = 1`, and therefore `lambda_hot + lambda_cold = lambda_total`.

R1 uses only hot coffee and no brewing cost. R2 adds cold coffee. R3 adds hot brewing cost. R4 adds cold brewing cost. These round boundaries match the official guide.

Resource constraints are explicit linear constraints:

- `beans_hot Q_hot + beans_cold Q_cold <= beans_available`
- `water_hot Q_hot + water_cold Q_cold <= water_available`
- `Q_hot, Q_cold >= 0`

The independent reference implementation evaluates the exact Normal-newsboy objective; Gurobi is independently checked against that reference. The PWL solver representation is a numerical approximation and is therefore validated against the exact objective at the returned decision.

## R5–R8 provenance boundary

The official guide establishes the mechanisms:

- R5: markup `m` is a decision; increasing markup raises price and lowers arrival rate `lambda(m)`.
- R6: balking is introduced; the probability of leaving grows with queue congestion.
- R7: customers can order multiple cups, increasing effective demand.
- R8: service rate `mu` becomes a decision and a barista cost `B(mu)` is subtracted from profit.

The guide presents the detailed response relationships for these mechanisms in figures. This repository does **not** infer numerical coefficients, functional forms, or hidden constants from generic queueing theory, synthetic observations, or visual guesses. Such equations can enter production only when they are recovered from an authoritative game artifact or reproducible real-game observations and pass the evidence gate.

## Simulation contract

The simulator is a validation instrument, not an authority for hidden game equations. It supports explicit callables for balking and order-size behavior, deterministic seeds, configurable warm-up, inventory, queueing, service, and costs. It must not silently convert an unspecified R5–R8 rule into a production optimization equation.

## Certification policy

A green CI/reference result is not equivalent to a licensed-Gurobi release certification. The final R9 gate requires the real `gurobipy` binding, a valid license, OPTIMAL status for every release case, explicit feasibility, exact-objective regret within the release tolerance, and agreement between the solver's reported PWL objective and the exact analytical objective.

R5–R8 remain `CALIBRATION_GATED` until their numerical response relationships have authoritative provenance. No fallback, mock, synthetic calibration, or reference-only run may be presented as a Gurobi certification.
