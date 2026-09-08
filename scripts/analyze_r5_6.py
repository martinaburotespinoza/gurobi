from pathlib import Path
import json

INPUT = Path("r5_adaptive_pwl_experiment.json")
OUTPUT = Path("r5_6_selection_analysis.json")

data = json.loads(INPUT.read_text(encoding="utf-8"))

results = data["results"]
points = data["points"]

analysis = {
    "schema": "gurobean.r5.selection_analysis.v1",
    "seed": data["seed"],
    "targets": data["targets"],
    "points": points,
    "strategies": {}
}

for strategy_name, strategy_data in results.items():
    cases = {}
    all_rows = []

    for case_name, case_data in strategy_data.items():
        reference = case_data["reference"]
        rows = case_data["results"]

        best = min(rows, key=lambda r: r["objective_error"])

        cases[case_name] = {
            "round": case_data["round"],
            "reference": reference,
            "best": {
                "points": best["points"],
                "objective_error": best["objective_error"],
                "Q_hot_error": best["Q_hot_error"],
                "Q_cold_error": best["Q_cold_error"],
                "seconds": best["seconds"]
            },
            "runs": [
                {
                    "points": r["points"],
                    "objective_error": r["objective_error"],
                    "Q_hot_error": r["Q_hot_error"],
                    "Q_cold_error": r["Q_cold_error"],
                    "seconds": r["seconds"]
                }
                for r in rows
            ]
        }

        all_rows.extend(
            {**r, "case": case_name}
            for r in rows
        )

    best_global = min(all_rows, key=lambda r: r["objective_error"])

    by_points = {}
    for p in points:
        subset = [r for r in all_rows if r["points"] == p]
        by_points[str(p)] = {
            "cases": len(subset),
            "max_objective_error": max(r["objective_error"] for r in subset),
            "mean_objective_error": sum(r["objective_error"] for r in subset) / len(subset),
            "max_Q_hot_error": max(r["Q_hot_error"] for r in subset),
            "max_Q_cold_error": max(r["Q_cold_error"] for r in subset),
            "mean_seconds": sum(r["seconds"] for r in subset) / len(subset)
        }

    analysis["strategies"][strategy_name] = {
        "case_count": len(cases),
        "cases": cases,
        "best_single_run": {
            "case": best_global["case"],
            "points": best_global["points"],
            "objective_error": best_global["objective_error"],
            "Q_hot_error": best_global["Q_hot_error"],
            "Q_cold_error": best_global["Q_cold_error"],
            "seconds": best_global["seconds"]
        },
        "by_points": by_points
    }

# Comparación directa entre estrategias.
uniform = analysis["strategies"].get("uniform")
adaptive = analysis["strategies"].get("adaptive")

if uniform and adaptive:
    comparison = {}

    for case_name in data["targets"]:
        u = uniform["cases"][case_name]["best"]
        a = adaptive["cases"][case_name]["best"]

        comparison[case_name] = {
            "uniform_best_points": u["points"],
            "uniform_best_objective_error": u["objective_error"],
            "adaptive_best_points": a["points"],
            "adaptive_best_objective_error": a["objective_error"],
            "adaptive_improves": a["objective_error"] < u["objective_error"],
            "objective_error_delta_adaptive_minus_uniform":
                a["objective_error"] - u["objective_error"]
        }

    analysis["strategy_comparison"] = comparison

OUTPUT.write_text(
    json.dumps(analysis, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("R5.6 ANALYSIS COMPLETE")
print("cases per strategy:", uniform["case_count"] if uniform else 0)

for strategy_name, strategy in analysis["strategies"].items():
    print()
    print("STRATEGY:", strategy_name.upper())
    print("CASES:", strategy["case_count"])

    for p, summary in strategy["by_points"].items():
        print(
            f"  {p:>6} points | "
            f"max_obj={summary['max_objective_error']:.12g} | "
            f"mean_obj={summary['mean_objective_error']:.12g} | "
            f"max_qh={summary['max_Q_hot_error']:.12g} | "
            f"max_qc={summary['max_Q_cold_error']:.12g} | "
            f"mean_s={summary['mean_seconds']:.4f}"
        )

print()
print("BEST SINGLE RUNS")
for strategy_name, strategy in analysis["strategies"].items():
    b = strategy["best_single_run"]
    print(
        strategy_name.upper(),
        "|",
        b["case"],
        "| points=", b["points"],
        "| objective_error=", b["objective_error"],
        "| seconds=", b["seconds"]
    )

if "strategy_comparison" in analysis:
    print()
    print("ADAPTIVE VS UNIFORM")
    for case, c in analysis["strategy_comparison"].items():
        print(
            case,
            "| uniform=", c["uniform_best_objective_error"],
            "| adaptive=", c["adaptive_best_objective_error"],
            "| adaptive_improves=", c["adaptive_improves"]
        )

print()
print("Artifact:", OUTPUT)
