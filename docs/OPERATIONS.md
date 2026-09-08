# Operations Runbook

## Local validation

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/validate_engine.py
```

## Gurobi validation

Install a compatible licensed `gurobipy` runtime in the execution environment, then run the same test suite. The adapter must report an actual Gurobi status and objective; it never fabricates a solver result.

## Calibration

Collect observations from the real Gurobean application and run:

```bash
python scripts/calibrate.py data.csv
```

Do not promote a fitted family into the optimizer merely because it has the lowest AIC. Apply the gates in `docs/CALIBRATION_PROTOCOL.md`, including repeated scenarios and out-of-sample validation.

## Deployment

The optimization engine is Python and requires a real Python runtime for Gurobi. A static/browser frontend must not be presented as a Gurobi execution backend. Production deployment should therefore keep the solver service separate from any static Vercel UI unless a supported server-side Python/Gurobi runtime is explicitly provisioned.
