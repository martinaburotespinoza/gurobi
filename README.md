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
- **API:** FastAPI `/health`, `/metadata`, `/solve`, `/evaluate`, `/status`, and assistant endpoints; all eight rounds are executable, with R5-R8 using the simulation backend.
- **CI:** Python 3.10-3.13 compile + test matrix plus reference/release-boundary audits.
- **Public web:** Vercel-ready public console with API routing and explicit certification-boundary messaging.

## Validate the engine

```bash
python -m pytest -q
python scripts/system_audit.py
python scripts/self_audit.py
python scripts/validate_all.py
python scripts/validate_production.py
python scripts/r8_math_validation.py
python scripts/r9_end_to_end.py
```

`system_audit.py` is a conservative non-licensed integration gate. It verifies required modules/scripts, compiles the application surface, executes the full test suite and validates the certification manifest. It deliberately reports the licensed Gurobi and real-game gates as external rather than fabricating them.

For the complete non-licensed pre-live gate, run:

```bash
python scripts/pre_live_game_check.py
```

That check deliberately cannot manufacture an R9 PASS: the final release requires a real licensed Gurobi environment, and R5-R8 formal game parity requires real observations and evidence validation.

`check_gurobi.py` deliberately returns a non-zero status when `gurobipy` or a valid Gurobi license is unavailable; the engine never fakes a solver result.

## Public certification status

The Vercel/API surface exposes `/status`. It cross-checks the certification manifest, current Git HEAD, source-tree cleanliness, Gurobi license state and the R9 JSON artifact. The public status can report the engine as healthy while still reporting the release as `NOT_READY`; an R9 artifact from an older commit cannot produce a current release PASS.

## Strict R9 release gate

The final release must be executed from the exact clean commit being released, in an environment with a real licensed Gurobi installation:

```bash
git status --short
python scripts/check_gurobi.py
python scripts/r9_release.py
python scripts/final_live_test_gate.py
```

A release is accepted only when the final gate reports `GUROBI_GATE: CHECKED`, `R9 STATUS: PASS`, exactly 400 checked cases, zero failures, exact commit match and a clean source tree. It creates `r9_release_certification.json`, which records the exact Git commit, seeded cases, round results, objective regrets, solver-objective errors, refinement events and failures. See `docs/R9_RELEASE_GATE.md`, `docs/LIVE_TEST_READINESS.md` and `docs/MATHEMATICAL_SPEC.md` for the normative definitions.

The generated R9 artifact is intentionally not committed: committing it changes `HEAD` and invalidates its exact-commit attestation.

## R5-R8 operational boundary

The official Gurobean Game Guide is the normative game source. It confirms the progressive mechanisms: markup-dependent arrivals, balking, multi-cup orders and service-rate/barista cost. The exact response relationships used by a real game scenario must come from real-game evidence/calibration. `gurobean/full_rounds.py` therefore makes every later round executable without hiding those relationships: arrival anchors, balking coefficients, multi-cup distribution and service-cost coefficients are explicit inputs. The engine reports R5-R8 as operational simulation results, never as formal game-parity certificates, until `gurobean/evidence_gate.py` is satisfied.

## Run the API

Install API extras and start:

```bash
pip install -e '.[api,test]'
python scripts/run_api.py
```

Then use `/docs` locally and `/status` for the deterministic certification/readiness state.

## Gurobi backend

The Gurobi adapter is deliberately a validation layer around the exact analytical objective. Normal CDF/PDF are represented with dense solver-backed PWL constraints; the analytical objective remains the independent mathematical reference. No Gurobi result is treated as an exact continuous certificate merely because the optimizer reports `OPTIMAL`.

<!-- production deploy trigger: 2026-09-09 -->
<!-- production deploy retry: 2026-09-09 -->
