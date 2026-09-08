# Gurobean Engine v2 — mathematical status

## Authoritative structure recovered

The official Gurobean Game Guide establishes:

- 24/5 operation and a 120-hour score horizon.
- Poisson customer arrivals.
- Hot/cold type probabilities splitting the total arrival rate.
- Hourly Poisson demand approximated by a Normal distribution with the same mean and variance for the optimization model.
- A newsvendor objective based on expected sales and overage/waste.
- Beans and water as resource constraints.
- Rounds 1–2: brewing quantities only; R2 adds cold coffee.
- Rounds 3–4: per-cup brewing cost; R4 keeps both coffee types.
- R5: markup decision.
- R6: balking.
- R7: multi-cup orders.
- R8: service rate decision and barista cost.

## Completed in v2.1

### R1
Analytic reference, numerical validation, and solver adapter.

### R2
Complete two-product newsvendor model:

- decisions: Q_h, Q_c
- demand means: λ_h = λ ψ_h, λ_c = λ ψ_c
- objective: P_h(Q_h) + P_c(Q_c)
- shared beans constraint
- shared water constraint
- non-negativity

### R3
Complete single-product cost-aware newsvendor model:

- decision: Q_h
- objective includes per-cup brewing cost
- exact continuous Normal-newsboy critical-fractile structure
- numerical validation
- Gurobi PWL solver adapter

### R4
Complete two-product cost-aware model:

- decisions: Q_h, Q_c
- additive expected profit
- per-cup hot/cold brewing costs
- shared beans and water constraints
- numerical constrained reference solve
- Gurobi PWL solver adapter

## Important solver boundary

Gurobi's current nonlinear helper catalogue does not expose Normal CDF/PDF/erf as native nonlinear functions. The Gurobi adapter therefore uses the exact analytic objective evaluated at dense breakpoints and a PWL general constraint. This is explicitly a solver-validation layer; the analytic Python formula remains the mathematical reference. No fake `gurobipy` execution is reported when the binding/license is absent.

## Still calibration-gated

No equations are invented for:

- R5 markup → arrival-rate response
- R6 balking response to congestion/waiting
- R7 multi-cup order-size mechanism
- R8 service-rate → wage/cost relationship

Those are isolated as calibration targets. The next stage is to recover observations from the real game/newsfeed and fit/validate those functions before enabling optimization for R5–R8.

## Legacy defects explicitly retired

1. Normal random sampling is not used as a substitute for the stated Poisson→Normal optimization approximation.
2. Grid search is not the official optimizer architecture for R1–R4.
3. Arbitrary ±3σ decision bounds are not used when an economic/resource bound can be derived.
4. Markup is not modeled as a percentage in the authoritative layer; the guide describes a shared absolute markup added to cost.
5. Balking, multi-cup, and service-cost equations are not fabricated.
6. Synthetic capacity defaults are not treated as game facts.
7. The leftover term is represented consistently as an explicit salvage extension with default zero.
