# Architecture

The engine is intentionally split into independent mathematical, solver, simulation, calibration and API layers.

- `gurobean/model.py`: authoritative R1-R4 analytical reference and solver adapter. R5-R8 optimization is explicitly blocked.
- `gurobean/simulation.py`: deterministic validation simulator; it is not an authority for hidden game equations.
- `gurobean/calibration.py`: statistical fitting infrastructure for R5-R8.
- `gurobean/evidence_gate.py`: provenance gate preventing synthetic/unspecified observations from promotion.
- `gurobean/calibrated.py`: isolated evaluators for promoted fits; promotion remains external to these functions.
- `scripts/r9_end_to_end.py`: independent seeded mathematical reference and optional Gurobi/PWL parity harness.
- `scripts/r9_release.py`: strict licensed-Gurobi release gate bound to a clean exact Git commit.
- `scripts/self_audit.py`: deterministic solver-independent repository contract audit.
- `api/app.py`: HTTP boundary; R1-R4 solving only, R5-R8 return an explicit calibration-gated response.

The official Gurobi Game Guide is the normative external source. R5-R8 response equations are not guessed from generic queueing theory or synthetic calibration.
