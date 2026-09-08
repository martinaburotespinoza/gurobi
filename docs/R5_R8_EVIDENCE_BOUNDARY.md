# R5-R8 evidence boundary

The official Gurobean Game Guide confirms the mechanisms introduced in R5-R8: markup affects arrival rate; R6 introduces balking; R7 introduces multi-cup orders; R8 makes service rate a decision and subtracts barista cost. The guide also defines the underlying Poisson/Normal newsvendor structure and the shared resource constraints. See the official source:

https://www.gurobi.com/academics/gurobean/game-guide

The public guide exposes several of the detailed response relationships as figures. This repository therefore does **not** infer missing numerical equations from generic queueing theory, synthetic experiments, or visual intuition.

## Promotion rule

A candidate R5-R8 response can enter production only after:

1. observations are captured from the real Gurobean game;
2. provenance is explicitly marked as `game`, `game_capture`, or `game_observation`;
3. the candidate passes the statistical validation protocol;
4. out-of-sample validation and residual diagnostics pass;
5. known domain and monotonicity constraints pass;
6. the resulting parameters are frozen into a reproducible artifact;
7. the promoted evaluator is covered by regression tests.

Synthetic observations may be useful for testing the calibration machinery, but they can never satisfy the production evidence gate.

## Current implementation boundary

- R1-R4: production mathematical core and Gurobi validation adapter.
- R5-R8: calibration infrastructure and isolated runtime evaluators only.
- `gurobean/evidence_gate.py`: strict provenance gate for promotion.
- `gurobean/model.py`: deliberately raises `NotImplementedError` for optimization rounds 5-8 until the corresponding game dynamics are evidenced.

This is a deliberate anti-false-positive boundary, not an incomplete fallback that is allowed to masquerade as certification.
