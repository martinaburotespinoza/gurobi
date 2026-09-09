# Gurobean Engine

Production-oriented mathematical, calibration and simulation engine for Gurobean Coffee.

## Current state

- **R1-R4:** implemented with analytical Normal-newsvendor reference solver and a Gurobi PWL validation backend.
- **R5-R8:** executable through a deterministic common-random-number Monte Carlo optimizer using explicit response parameters; formal parity with the real game remains evidence-gated.
- **R8 mathematical certification:** independent differential, concavity, stationarity, resource-boundary and objective-decomposition checks over a seeded stress set; this harness does not modify the production model.
- **R9 end-to-end certification:** 100 seeded scenarios across R1-R4 (400 reference executions), deterministic replay, feasibility, exact objective consistency, edge cases and optional real-Gurobi/PWL parity.
- **R9 release certification:** strict licensed-Gurobi gate with adaptive PWL refinement, clean-commit enforcement and a complete JSON audit artifact.
- **Simulation:** reproducible M/M/1 baseline plus a configurable continuous-time coffee-shop simulator with inventory, balking, multi-cup orders and service-rate cost.
- **Experiments:** seeded batches, aggregation and cross-validation.
- **Validation:** analytical-vs-Monte-Carlo checks, deterministic self-audit and production validation commands.
- **API:** FastAPI `/health`, `/metadata`, `/solve`, `/evaluate`, and assistant endpoints; all eight rounds are executable, with R5-R8 using the simulation backend.
- **CI:** Python 3.10-3.13 compile + test matrix plus reference/release-boundary audits.
- **Public web:** Vercel-ready public console with API routing and explicit certification-boundary messaging.

## Validate the engine

```bash
python -m pytest -q
python scripts/self_audit.py
python scripts/validate_all.py
python scripts/validate_production.py
python scripts/r8_math_validation.py
python scripts/r9_end_to_end.py
```

For the complete non-licensed pre-live gate, run:

```bash
python scripts/pre_live_game_check.py
```

That check deliberately cannot manufacture an R9 PASS: the final release requires a real licensed Gurobi environment, and R5-R8 formal game parity requires real observations and evidence validation.

`check_gurobi.py` deliberately returns a non-zero status when `gurobipy` or a valid Gurobi license is unavailable; the engine never fakes a solver result.

## Strict R9 release gate

The final release must be executed from the exact clean commit being released, in an environment with a real licensed Gurobi installation:

```bash
git status --short
python scripts/check_gurobi.py
python scripts/r9_release.py
```

A release is accepted only when the command reports `GUROBI_GATE: CHECKED` and `R9 STATUS: PASS`. It creates `r9_release_certification.json`, which records the exact Git commit, seeded cases, round results, objective regrets, solver-objective errors, refinement events and failures. See `docs/R9_RELEASE_GATE.md`, `docs/LIVE_TEST_READINESS.md` and `docs/MATHEMATICAL_SPEC.md` for the normative definitions.

## R5-R8 operational boundary

The official Gurobean Game Guide is the normative game source. It confirms the progressive mechanisms: markup-dependent arrivals, balking, multi-cup orders and service-rate/barista cost. The exact response relationships used by a real game scenario must come from real-game evidence/calibration. `gurobean/full_rounds.py` therefore makes every later round executable without hiding those relationships: arrival anchors, balking coefficients, multi-cup distribution and service-cost coefficients are explicit inputs. The engine reports R5-R8 as operational simulation results, never as formal game-parity certificates, until `gurobean/evidence_gate.py` is satisfied.

## Run the API

Install API extras and start:

```bash
pip install -e '.[api,test]'
python scripts/run_api.py
```

Then use `/docs` locally.

## Gurobi backend

The Gurobi adapter is deliberately a validation layer around the exact analytical objective. Normal CDF/PDF are represented with dense solver-backed PWL constraints; the analytical objective remains the independent mathematical reference. No Gurobi result is treated as an exact continuous certificate merely because the optimizer reports `OPTIMAL`.

<!-- production deploy trigger: 2026-09-09 -->
