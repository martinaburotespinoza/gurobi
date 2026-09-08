# Gurobean Engine v2_6 — readiness for the real test

## Purpose

This document is the final engineering boundary before using Gurobean Engine v2_6 against the real game. It separates what the repository can prove automatically from what must be observed in the real game or verified with a licensed local Gurobi environment.

## Verified engineering layers

### R1–R4 — mathematical core
- Independent Normal-Newsvendor analytical reference.
- Feasibility checks for non-negativity and shared beans/water constraints.
- SciPy reference validation.
- Gurobi-native PWL adapter and strict objective/regret checks.
- R8 mathematical validation exercises gradient, Hessian, concavity, stationarity/KKT and boundary behavior.
- R9 release harness covers 100 seeded scenarios × 4 rounds = 400 case/round checks.

### R5–R8 — operational engine
- R5: markup → arrivals.
- R6: congestion → balking/stay probability.
- R7: multi-cup demand.
- R8: service-rate decision with service cost.
- 120-hour deterministic common-random-number simulation.
- Reproducibility and saturation/load battery included in the test suite.
- Parameters are explicit inputs; the engine does not silently invent game calibration.

## Integrity boundary

R5–R8 must not be presented as formally equivalent to the game until real observations with valid provenance pass the calibration/evidence gate. Synthetic data is useful for testing the calibration machinery but is not evidence of the real game.

R9 must not be reported as PASS unless `scripts/r9_release.py` has been run on the exact release commit with a real licensed Gurobi environment and has produced `r9_release_certification.json` with `GUROBI_GATE: CHECKED` and `R9 STATUS: PASS`.

## Final preflight

Run the repository-wide non-licensed preflight:

```powershell
python scripts/pre_live_game_check.py
```

A successful preflight means the software gates that do not require proprietary credentials are green. It does **not** fabricate the two external gates below.

## Two remaining external gates

1. **Licensed Gurobi release gate**
   - Clean working tree.
   - Exact release commit recorded.
   - Real Gurobi environment starts.
   - 400/400 R1–R4 checks pass.
   - Release artifact is generated and tied to the exact commit.

2. **Real-game evidence gate for R5–R8**
   - Collect observations from the actual game.
   - Preserve capture/provenance.
   - Fit only relationships supported by observations.
   - Validate in-sample and out-of-sample.
   - Inspect residuals and enforce domain/monotonicity constraints.
   - Freeze promoted parameters into a reproducible artifact.
   - Add regression coverage before claiming formal game parity.

## Operational test protocol

When the real game is available, test in this order:

1. Freeze the exact Git commit and environment.
2. Execute the licensed R9 release gate.
3. Establish a baseline game run without engine intervention.
4. Capture R5–R8 observations with timestamps/round identifiers and provenance.
5. Calibrate one mechanism at a time: arrivals, balking, multi-cup demand, service rate/cost.
6. Hold out observations for out-of-sample validation.
7. Freeze only validated parameters.
8. Re-run the engine against the same observed scenarios.
9. Compare decisions and economic/operational outcomes.
10. Only then consider production promotion of R5–R8.

## Non-negotiable rule

No PASS is inferred from a simulation, synthetic calibration, CI fallback, or visual inspection when the corresponding authoritative evidence is missing.
