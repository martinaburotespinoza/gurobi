# Gurobean Engine

Production-oriented mathematical, calibration and simulation engine for Gurobean Coffee.

## Current state

- **R1-R4:** implemented with analytical Normal-newsvendor reference solver and a Gurobi PWL validation backend.
- **R5-R8:** evidence-gated calibration framework plus runtime evaluators for promoted fits; no game rule is invented.
- **R8 mathematical certification:** independent differential, concavity, stationarity, resource-boundary and objective-decomposition checks over a seeded stress set; this harness does not modify the production model.
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
```

`check_gurobi.py` deliberately returns a non-zero status when `gurobipy` or a valid Gurobi license is unavailable; the engine never fakes a solver result.

## Run the API

Install API extras and start:

```bash
pip install -e '.[api,test]'
python scripts/run_api.py
```

Then use `/docs` locally.

## Gurobi backend

Install the optional dependency and provide a valid Gurobi environment/license. The current R1-R4 adapter uses dense PWL representations of the analytical Normal-newsboy objective. This is intentional: current Gurobi nonlinear constraints support broad nonlinear expressions, but the standard nonlinear function catalogue does not provide the Normal CDF/PDF/erf needed to encode the closed-form objective directly. Gurobi 13 documents nonlinear constraints and PWL approximations as the supported approaches.

## Production packaging smoke test

```bash
python -m pip wheel . --no-deps --no-build-isolation -w /tmp/gurobean-wheel
```

The wheel is then imported in an isolated target directory before release.

## Later-round simulation boundary

`simulate_gurobean()` is intentionally a validation harness. It accepts explicit calibrated callables for R6 balking and R7 order size instead of embedding unverified game equations. This keeps the engine auditable while allowing observed Gurobean runs to be promoted into the runtime through the evidence gate.

### Solver parity harness

`gurobean.parity` provides a deterministic R1-R4 parity suite. It generates stress scenarios, solves each with the analytic/SciPy reference, and—when a real `gurobipy` runtime and license are available—compares the Gurobi PWL solution on objective and decision tolerances. When Gurobi is unavailable, the suite explicitly reports `skipped_gurobi_unavailable` and never fabricates a solver result.

Run it with:

```bash
python -c "from gurobean.parity import run_parity_suite; print([r.to_dict() for r in run_parity_suite()])"
```
