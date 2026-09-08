# Gurobean Engine

Production-oriented mathematical, calibration and simulation engine for Gurobean Coffee.

## Current state

- **R1-R4:** implemented with analytical Normal-newsvendor reference solver and a Gurobi PWL validation backend.
- **R5-R8:** evidence-gated calibration framework plus runtime evaluators for promoted fits; no game rule is invented.
- **R8 mathematical certification:** independent differential, concavity, stationarity, resource-boundary and objective-decomposition checks over a seeded stress set; this harness does not modify the production model.
- **R9 end-to-end certification:** 100 seeded scenarios across R1-R4 (400 reference executions), deterministic replay, feasibility, exact objective consistency, edge cases and optional real-Gurobi/PWL parity.
- **Simulation:** reproducible M/M/1 baseline plus a configurable continuous-time coffee-shop simulator with inventory, balking, multi-cup orders and service-rate cost; later-round rules remain calibration-driven.
- **Experiments:** seeded batches, aggregation and cross-validation.
- **Validation:** analytical-vs-Monte-Carlo checks and a single production validation command.
- **API:** FastAPI `/health`, `/metadata`, `/solve`.
- **CI:** Python 3.10-3.13 compile + test matrix.

## Validate everything

```bash
python -m pytest -q
python scripts/validate_all.py
python scripts/validate_production.py
python scripts/check_gurobi.py
python scripts/r8_math_validation.py
python scripts/r9_end_to_end.py
```

`check_gurobi.py` deliberately returns a non-zero status when `gurobipy` or a valid Gurobi license is unavailable; the engine never fakes a solver result.

**R9 release gate:** in the licensed local Gurobi environment run:

```bash
python scripts/r9_end_to_end.py --require-gurobi
```

The generated artifact must report `R9 STATUS: PASS` and `GUROBI_GATE: CHECKED`. CI certifies the reference path but cannot substitute for the licensed Gurobi gate.

## Run the API

Install API extras and start:

```bash
pip install -e '.[api,test]'
python scripts/run_api.py
```

Then use `/docs` locally.

## Gurobi backend

The Gurobi adapter is deliberately a validation layer around the exact analytical objective. Normal CDF/PDF are represented with dense solver-backed PWL constraints; the analytical objective remains the independent mathematical reference. No Gurobi result is treated as an exact continuous certificate merely because the optimizer reports `OPTIMAL`.
