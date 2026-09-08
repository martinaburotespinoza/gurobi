# Gurobean Engine — 1000% certification status

This document is the release truth for the `r9-1000-certification` line.

## Normative source

The primary external normative source is the official Gurobi Gurobean Game Guide:

https://www.gurobi.com/academics/gurobean/game-guide

The guide defines the eight-round progression, Poisson arrivals, the complete hot/cold demand split, the Normal approximation used for optimization, the newsvendor/waste structure, resource constraints, markup, balking, multi-cup orders, and service-rate decisions.

## Gate policy

A release is **1000% CERTIFIED** only when every mandatory gate below is green.

| Gate | Status | Rule |
|---|---|---|
| R1 mathematical reference | IMPLEMENTED | Independent Normal-newsvendor reference + solver adapter |
| R2 mathematical reference | IMPLEMENTED | Two-product reference + shared resource constraints |
| R3 mathematical reference | IMPLEMENTED | Cost-aware single-product reference |
| R4 mathematical reference | IMPLEMENTED | Cost-aware two-product constrained reference |
| R1-R4 automated validation | IMPLEMENTED | Regression, parity, stress and end-to-end checks |
| R1-R4 official demand contract | IMPLEMENTED | `p_hot + p_cold = 1`; release scenarios use zero salvage/waste economics |
| Real Gurobi binding | REQUIRED | `gurobipy` must import from the real installation |
| Valid Gurobi license | REQUIRED | Release certification must solve with `OPTIMAL` status |
| R9 release audit | REQUIRED | `scripts/r9_release.py` must finish with `R9 STATUS: PASS` |
| Exact release commit | IMPLEMENTED | Dirty working trees are rejected; artifact records Git HEAD |
| R5 markup dynamics | CALIBRATION-GATED | Real-game observations + independent validation required |
| R6 balking | CALIBRATION-GATED | Real-game queue/wait observations + independent validation required |
| R7 order-size mechanism | CALIBRATION-GATED | Real-game order-size observations + independent validation required |
| R8 service-cost curve | CALIBRATION-GATED | Real-game service-rate/cost observations + independent validation required |
| Evidence provenance gate | IMPLEMENTED | Synthetic/unspecified observations cannot be promoted |
| Production promotion R5-R8 | BLOCKED UNTIL EVIDENCE | No fitted family becomes a game rule merely because it fits synthetic data |

## Non-negotiable anti-false-positive rules

1. Missing Gurobi is **FAIL**, not PASS.
2. An unlicensed CI runner is **not** evidence of a Gurobi PASS.
3. A statistical fit is not an official game equation by itself.
4. Synthetic calibration data cannot promote R5-R8 into production.
5. Only observations explicitly sourced from the real game may enter the strict promotion gate.
6. A stale certification artifact cannot certify a newer code revision.
7. A PWL objective is accepted only after comparison with the exact analytic objective within the release tolerance.
8. Every reported Gurobi solution must be explicitly feasible and `OPTIMAL`.
9. R5-R8 optimization must not silently fall back to generic queueing or guessed response functions.
10. R9 certification scenarios must obey the official hot/cold partition and waste economics rather than an unconstrained synthetic extension.

## Current release boundary

R1-R4 are the mathematically promotable core. R5-R8 are deliberately isolated behind an evidence gate until the official game behavior has sufficient empirical observations and reproducible validation for each mechanism.

The official Game Guide confirms the mechanisms, but the detailed response relationships are presented in the guide as figures. The repository therefore does not manufacture numerical equations from generic theory or synthetic experiments.

The final local release step must execute the real-Gurobi release audit against the exact commit being released and preserve its generated certification artifact with the release evidence.
