from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gurobean.calibration import (
    CalibrationDataset,
    Observation,
    best_fit,
    fit_r5_arrival_rate,
    fit_r6_balking,
    fit_r7_order_size,
    fit_r8_service_cost,
)


def load_csv(path: Path) -> CalibrationDataset:
    ds = CalibrationDataset()
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row.get("round_number"):
                continue
            r = int(row["round_number"])
            variables = {}
            outputs = {}
            for key in ("markup", "queue", "wait_minutes", "service_rate"):
                if row.get(key, "").strip():
                    variables[key] = float(row[key])
            for key in ("arrival_rate", "stay_probability", "order_size", "barista_cost_per_hour"):
                if row.get(key, "").strip():
                    outputs[key] = float(row[key])
            required = {
                5: (("markup",), ("arrival_rate",)),
                6: (("queue", "wait_minutes"), ("stay_probability",)),
                7: ((), ("order_size",)),
                8: (("service_rate",), ("barista_cost_per_hour",)),
            }
            var_req, out_req = required[r]
            if var_req and not any(k in variables for k in var_req):
                continue
            if not all(k in outputs for k in out_req):
                continue
            ds.add(Observation(r, variables, outputs, source=row.get("source") or "game"))
    return ds


def main() -> None:
    ap = argparse.ArgumentParser(description="Fit Gurobean R5-R8 calibration candidates")
    ap.add_argument("csv", type=Path)
    args = ap.parse_args()
    ds = load_csv(args.csv)

    fitters = {
        5: fit_r5_arrival_rate,
        6: fit_r6_balking,
        7: fit_r7_order_size,
        8: fit_r8_service_cost,
    }
    for r, fitter in fitters.items():
        obs = ds.for_round(r)
        if not obs:
            continue
        results = fitter(obs)
        best = best_fit(results)
        print(f"R{r}: best={best.family} score={best.score:.6g} rmse={best.rmse:.6g}")
        print(f"  parameters={best.parameters}")
        for candidate in results:
            print(f"  candidate={candidate.family:16s} score={candidate.score:.6g} rmse={candidate.rmse:.6g}")


if __name__ == "__main__":
    main()
