# R9 release gate

R9 is the final engineering gate for the mathematically closed R1-R4 core.
It is intentionally separate from the empirical calibration of R5-R8.

## Required conditions

A release certification is PASS only when all of the following hold:

1. `gurobipy` imports successfully.
2. A real Gurobi environment starts successfully, proving that the local license gate is available.
3. All 100 seeded scenarios are evaluated for rounds R1-R4 (400 checks).
4. The independent analytical reference is feasible and deterministic.
5. Every Gurobi solution is `OPTIMAL`.
6. Every returned decision satisfies non-negativity and both shared-resource constraints.
7. The exact analytical objective evaluated at the Gurobi decision is within the configured regret tolerance of the independent reference optimum.
8. Gurobi's reported PWL objective is within the same release tolerance of the exact analytical objective at its returned decision.
9. If a base PWL mesh misses the release tolerance, deterministic refinement is attempted at 5001, 10001 and 20001 points.
10. A JSON artifact records the complete certification run, including failures and maxima.

## Important mathematical boundary

The PWL model is a solver-validation encoding of the exact Normal-newsvendor objective. It is not itself claimed to be an exact native representation of the Normal CDF/PDF. The independent analytical implementation remains the reference truth.

## R5-R8 boundary

R5 markup, R6 balking, R7 multi-cup orders and R8 service-rate economics remain calibration-gated. Their existence as round concepts is supported by the game specification, but no empirical response equation is enabled without observed evidence. The release gate must never silently substitute synthetic equations for those rules.

## Release command

Run from a licensed local Gurobi environment:

```bash
python scripts/r9_release.py
```

A successful release must print:

```text
GUROBI_GATE: CHECKED
R9 STATUS: PASS
```

and create `r9_release_certification.json`.
