# Gurobean Engine

Production-oriented mathematical, calibration and simulation engine for Gurobean Coffee.

## Current state

- **R1-R4:** implemented with analytical Normal-newsvendor reference solver and a Gurobi PWL validation backend.
- **R5-R8:** evidence-gated calibration framework plus runtime evaluators for promoted fits; no game rule is invented.
- **R8 mathematical certification:** independent differential, concavity, stationarity, resource-boundary and objective-decomposition checks over a seeded stress set; this harness does not modify the production model.
- **R9 end-to-end certification:** 100 seeded scenarios across R1-R4 (400 reference executions), deterministic replay, feasibility, exact objective consistency, edge cases and optional real-Gurobi/PWL parity.
- **R9 release certification:** strict licensed-Gurobi gate with adaptive PWL refinement, clean-commit enforcement and a complete JSON audit artifact.
- **Simulation:** reproducible M/M/1 baseline plus a configurable continuous-time coffee-shop simulator with inventory, balking, multi-cup orders and service-rate cost; later-round rules remain calibration-driven.
- **Experiments:** seeded batches, aggregation and cross-validation.
- **Validation:** analytical-vs-Monte-Carlo checks, deterministic self-audit and production validation commands.
- **API:** FastAPI `/health`, `/metadata`, `/solve`, with R5-R8 explicitly blocked.
- **CI:** Python 3.10-3.13 compile + test matrix plus reference/release-boundary audits.

## Validate everything available without a local Gurobi license

```bash
python -m pytest -q
python scripts/self_audit.py
python scripts/validate_all.py
python scripts/validate_production.py
python scripts/r8_math_validation.py
python scripts/r9_end_to_end.py
```

`check_gurobi.py` deliberately returns a non-zero status when `gurobipy` or a valid Gurobi license is unavailable; the engine never fakes a solver result.

## Strict R9 release gate

The final release must be executed from the exact clean commit being released, in an environment with a real licensed Gurobi installation:

```bash
git status --short
python scripts/check_gurobi.py
python scripts/r9_release.py
```

A release is accepted only when the command reports `GUROBI_GATE: CHECKED` and `R9 STATUS: PASS`. It creates `r9_release_certification.json`, which records the exact Git commit, seeded cases, round results, objective regrets, solver-objective errors, refinement events and failures. See `docs/R9_RELEASE_GATE.md` and `docs/MATHEMATICAL_SPEC.md` for the normative definitions.

## R5-R8 certification boundary

The official Gurobi Game Guide is the normative game source. It confirms the progressive mechanisms: markup-dependent arrivals, balking, multi-cup orders and service-rate/barista cost. The detailed response relationships are presented in the guide as figures; this repository does not invent numerical equations from generic queueing theory, synthetic calibration or visual guesses. Promotion requires real-game provenance plus independent validation through `gurobean/evidence_gate.py`.

## Run the API

Install API extras and start:

```bash
pip install -e '.[api,test]'
python scripts/run_api.py
```

Then use `/docs` locally.

## Gurobi backend

The Gurobi adapter is deliberately a validation layer around the exact analytical objective. Normal CDF/PDF are represented with dense solver-backed PWL constraints; the analytical objective remains the independent mathematical reference. No Gurobi result is treated as an exact continuous certificate merely because the optimizer reports `OPTIMAL`.
