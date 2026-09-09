# Public console status

The public Vercel console uses the independent SciPy reference backend for R1-R4 and the operational Monte Carlo backend for R5-R8. The licensed Gurobi backend remains the local certification path and is not exposed as a browser dependency.

The public UI progressively exposes R1-R8 inputs and includes a custom-scenario mode. R9 remains a release gate, not a game round.

Public routing serves the interactive console through `api/ui.py` so the browser-safe backend selection and validation guardrails are applied consistently.
