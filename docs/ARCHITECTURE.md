# Gurobean Engine Architecture

## Principle

The engine separates **authoritative mathematics**, **numerical validation**, **solver integration**, **dynamic simulation**, and **empirical calibration**. A calibrated or simulated behavior must never silently become an optimization assumption.

```text
Official Game Guide
      |
      v
Mathematical model R1-R4 ----> analytic reference
      |                         |
      |                         +--> SciPy validation
      |                         +--> Gurobi PWL validation
      |
      +--> R5-R8 calibration gate <---- observed game data
      |
      +--> event simulation
```

## Solver boundary

The Python reference implementation evaluates the Normal-newsboy expression directly. The Gurobi adapter validates the same objective using piecewise-linear constraints. This is deliberate: the reference formula is the mathematical oracle, while Gurobi is the production optimization backend when the licensed runtime is available.

## No-fabrication rule

R5-R8 remain disabled until empirical observations satisfy the calibration protocol. Missing equations are represented as explicit gates, not guesses.
