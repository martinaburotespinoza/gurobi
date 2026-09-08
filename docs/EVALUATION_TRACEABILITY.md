# Gurobean — Evaluation Traceability

This document maps the implementation to the academic evaluation requirements. It intentionally separates **mathematical certification**, **operational simulation**, and **real-game validation**.

## 1. What the product must demonstrate

The program must accept the parameters supplied for a Gurobean scenario, choose feasible production/pricing/service decisions, maximize expected benefit, expose relevant indicators, and allow the same architecture to be reused when the problem changes.

The supplied evaluation documents require: correct identification of the eight-round progression; explicit objective evolution; distinction between decisions and parameters; justified Monte Carlo use; working resolution of all eight rounds; and quantitative comparison with the real game. The live presentation additionally requires a configurable product that can be adapted to a new case without rewriting code, and fast enough to operate under presentation pressure. fileciteturn182file1L102-L124 fileciteturn182file5L393-L412

## 2. Current implementation map

| Requirement | Implementation / evidence | Gate |
|---|---|---|
| R1 analytical model | `gurobean/model.py` + closed-form/SciPy reference | Certified path |
| R2 cold coffee | shared-resource two-product model | Certified path |
| R3 preparation cost | objective adds per-unit production cost | Certified path |
| R4 coupled resources | shared beans/water constraints + globality tests | Certified path |
| R5 markup | configurable arrival response + simulation | Operational; evidence-gated |
| R6 balking | queue-dependent stay probability + simulation | Operational; evidence-gated |
| R7 multiple cups | configurable order-size sampler + inventory simulation | Operational; evidence-gated |
| R8 service speed | decision variable + configurable convex service cost | Operational; evidence-gated |
| 120-hour evaluation | simulator and repeated evaluation engine | Implemented |
| Reproducibility | deterministic NumPy seeds / CRN replication schedule | Implemented |
| Uncertainty reporting | repeated simulation mean, SD, SE and 95% CI | Implemented |
| API | `/solve`, `/evaluate`, `/metadata`, `/health`, `/ai/*` | Implemented |
| Regression | Python 3.10–3.13 CI, compile, pytest, validation scripts | Required gate |
| Real-game comparison | evidence gate and explicit certification manifest | **Pending evidence** |

## 3. Certification policy

R1–R4 may claim mathematical certification only when the analytical reference, feasibility checks, PWL/Gurobi result, and end-to-end audit all pass.

R5–R8 must not be labeled formally certified merely because a simulation is executable. Their exact game equations/parameters must be supported by real-game observations or authoritative evidence, then calibrated and revalidated. This prevents a plausible engineering model from being presented as a reverse-engineered game model.

## 4. Presentation readiness

The product surface should communicate four things immediately:

1. **Inputs:** demand, economics, resources, and enabled model features.
2. **Decision:** quantities, markup, and service rate when applicable.
3. **Business result:** expected profit plus service/risk indicators.
4. **Confidence/validation status:** certified analytical, operational simulation, or evidence-gated.

The presentation rubric explicitly expects a live new case, entered after the case is revealed, followed by comparison against the real values. fileciteturn182file6L465-L488 fileciteturn182file6L420-L435

## 5. Final release blockers

- Recover authoritative R5–R8 equations/parameters or collect reproducible real-game observations.
- Run calibration against those observations.
- Re-run all eight rounds with the calibrated model.
- Run licensed local Gurobi certification for the R1–R4 path.
- Produce quantitative real-game comparisons for each round with evidence.
- Freeze the final certification manifest only after every required gate is green.
