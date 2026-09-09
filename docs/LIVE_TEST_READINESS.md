# Gurobean Engine v2_6 — readiness for the real test

## Purpose

This document is the final engineering boundary before using Gurobean Engine v2_6 against the real game. It separates what the repository can prove automatically from what must be observed in the real game or verified with a licensed Gurobi environment.

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

A successful preflight means the software gates that do not require proprietary credentials are green. It does **not** fabricate the licensed solver gate or real-game evidence gate.

## Final live-test approval command

After the licensed R9 release run completes successfully, run:

```powershell
python scripts/final_live_test_gate.py
```

The command returns the exact approval string only when:

- `r9_release_certification.json` exists and says `R9 STATUS: PASS`.
- `GUROBI_GATE` is `CHECKED`.
- Exactly 400 R1–R4 case/round checks were executed.
- Zero release failures were recorded.
- The artifact's Git commit exactly matches the current `HEAD`.
- No source files changed after certification.

The generated R9 artifact is intentionally not committed to Git: committing it would change `HEAD` and invalidate its exact-commit attestation. Preserve it as release evidence or a CI artifact instead.

## External gates

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

The first gate is required for **approval to test with the live game**. The second gate is required for **formal promotion of R5–R8 as game-parity rules**.

## Operational test protocol

When the real game is available, test in this order:

1. Freeze the exact Git commit and environment.
2. Run `python scripts/check_gurobi.py`.
3. Run `python scripts/r9_release.py`.
4. Run `python scripts/final_live_test_gate.py`.
5. Establish a baseline game run without engine intervention.
6. Capture R5–R8 observations with timestamps/round identifiers and provenance.
7. Calibrate one mechanism at a time: arrivals, balking, multi-cup demand, service rate/cost.
8. Hold out observations for out-of-sample validation.
9. Freeze only validated parameters.
10. Re-run the engine against the same observed scenarios.
11. Compare decisions and economic/operational outcomes.
12. Only then consider production promotion of R5–R8.

## Non-negotiable rule

No PASS is inferred from a simulation, synthetic calibration, CI fallback, or visual inspection when the corresponding authoritative evidence is missing.
