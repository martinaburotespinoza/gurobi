# Operations Runbook

## Reference validation

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/self_audit.py
python scripts/validate_engine.py
python scripts/r8_math_validation.py
python scripts/r9_end_to_end.py
```

These commands validate the reference, simulation, invariants and R1-R4 parity paths. They do **not** certify a licensed Gurobi execution.

## Final R9 release certification

The final gate must run from the exact repository commit to be released, with a clean working tree and a real licensed Gurobi installation:

```bash
git status --short
python scripts/check_gurobi.py
python scripts/r9_release.py
```

`r9_release.py` refuses to certify a dirty working tree, a missing/invalid Gurobi license, a non-OPTIMAL result, an infeasible solver decision, excessive exact-objective regret, or excessive PWL-vs-exact objective error. The generated `r9_release_certification.json` records the exact commit and is ignored by Git as a generated audit artifact.

A valid final release must print:

```text
GUROBI_GATE: CHECKED
R9 STATUS: PASS
```

## Calibration and R5-R8

Collect observations from the real Gurobean application and run the calibration tooling. Do not promote a fitted family into the optimizer merely because it has the lowest AIC or because synthetic experiments fit well. Apply the gates in `docs/CALIBRATION_PROTOCOL.md` and `docs/R5_R8_EVIDENCE_BOUNDARY.md`, including provenance, repeated scenarios, out-of-sample validation and residual diagnostics.

The official Game Guide confirms the R5-R8 mechanisms, but detailed response relationships shown as figures are not reconstructed by guesswork in this repository. Until authoritative/reproducible evidence is available, the optimizer remains deliberately blocked for R5-R8.

## Deployment

The optimization engine is Python and requires a real Python runtime for Gurobi. A static/browser frontend must not be presented as a Gurobi execution backend. Production deployment should keep the solver service separate from any static Vercel UI unless a supported server-side Python/Gurobi runtime is explicitly provisioned.
