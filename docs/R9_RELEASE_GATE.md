# R9 release gate

R9 is the final engineering gate for the mathematically closed R1-R4 core. It is intentionally separate from the empirical calibration of R5-R8.

## Required conditions

A release certification is PASS only when all of the following hold:

1. `gurobipy` imports successfully.
2. A real Gurobi environment starts successfully, proving that the local license gate is available.
3. The repository working tree is clean and the exact Git HEAD is recorded in the artifact.
4. All 100 seeded scenarios are evaluated for rounds R1-R4 (400 checks).
5. The release scenarios obey the official complete hot/cold demand partition and use zero salvage because unused coffee is waste in the game.
6. The independent analytical reference is feasible and deterministic.
7. Every Gurobi solution is `OPTIMAL`.
8. Every returned decision satisfies non-negativity and both shared-resource constraints.
9. The exact analytical objective evaluated at the Gurobi decision is within the configured regret tolerance of the independent reference optimum.
10. Gurobi's reported PWL objective is within the same release tolerance of the exact analytical objective at its returned decision.
11. If a base PWL mesh misses the release tolerance, deterministic refinement is attempted at 5001, 10001 and 20001 points.
12. A JSON artifact records the complete certification run, including the exact commit, failures and maxima.
13. The certification scripts themselves pass the repository self-audit before the solver gate is considered reachable.

## Numerical release policy

The exploratory R9 harness may use a wider diagnostic tolerance, but the production release gate caps the accepted objective error at `1e-4`. The release artifact records the effective tolerance explicitly. This prevents a loose exploratory threshold from silently becoming a production certification threshold.

The PWL mesh is only a numerical encoding of the exact analytical Normal-newsvendor objective. Acceptance is based on the exact analytical objective evaluated at the solver's returned decision, not on the PWL value alone.

## Important mathematical boundary

The PWL model is a solver-validation encoding of the exact Normal-newsboy objective. It is not itself claimed to be an exact native representation of the Normal CDF/PDF. The independent analytical implementation remains the reference truth.

## R5-R8 boundary

R5 markup, R6 balking, R7 multi-cup orders and R8 service-rate economics remain calibration-gated. Their existence as round concepts is supported by the official game specification, but no empirical response equation is enabled without observed evidence. Synthetic calibration cannot promote a response family into a game rule.

The strict provenance gate is implemented in `gurobean/evidence_gate.py` and accepts only observations explicitly sourced from the real game.

## Release command

Run from a licensed local Gurobi environment on the exact clean commit being released:

```bash
python scripts/check_gurobi.py
python scripts/r9_release.py
```

A successful release must print:

```text
GUROBI_GATE: CHECKED
R9 STATUS: PASS
```

and create `r9_release_certification.json` containing the exact Git commit.
