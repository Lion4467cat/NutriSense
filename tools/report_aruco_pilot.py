"""One-time exploratory mass report for the six user-labeled ArUco meals.

Input predictions must be produced from a frozen candidate after all model
selection and threshold tuning. This tool never trains or tunes a model.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]

GROUND_TRUTH = {
    "Dish 1": {"tare_g": {"plate": 127.0, "bowl": 109.0},
               "net_food_g": {"rice": 250.0, "keerai_sambar": 200.0}},
    "Dish 2": {"tare_g": {"plate": 255.0, "bowl": 66.0},
               "net_food_g": {"rice": 211.0, "tomato_rasam": 127.0}},
    "Dish 3": {"tare_g": {"plate": 127.0, "bowl": 47.0},
               "net_food_g": {"coconut_chutney": 70.0, "chapati": 121.0},
               "quantities": {"chapati": 2}},
    "Dish 4": {"tare_g": {"plate": 127.0},
               "net_food_g": {"dum_biryani": 206.0, "egg": 44.0},
               "quantities": {"egg": 1}},
    "Dish 5": {"tare_g": {"plate": 127.0},
               "net_food_g": {"dum_biryani": 150.0}},
    "Dish 6": {"tare_g": {"plate": 127.0},
               "net_food_g": {"dum_biryani": 257.0, "egg": 94.0},
               "quantities": {"egg": 2}},
}


def build_report(candidate: dict, predictions: dict) -> dict:
    if candidate.get("frozen") is not True or not candidate.get("candidate_id"):
        raise ValueError("Candidate must have frozen=true and a candidate_id")
    pred_groups = predictions.get("groups", {})
    if predictions.get("candidate_id") != candidate["candidate_id"]:
        raise ValueError("Prediction candidate_id does not match the frozen candidate")
    if set(pred_groups) != set(GROUND_TRUTH):
        raise ValueError("Predictions must include exactly Dish 1 through Dish 6")
    if any(int(pred_groups[group].get("frame_count", 0)) < 1 for group in GROUND_TRUTH):
        raise ValueError("Each labeled meal group must include at least one evaluated frame")
    frame_count = sum(int(pred_groups[group].get("frame_count", 0)) for group in GROUND_TRUTH)
    if frame_count != 23:
        raise ValueError("Predictions must cover all 23 frames across the six fixed meal groups")
    errors = []
    output_groups = {}
    for group, truth in GROUND_TRUTH.items():
        pred = pred_groups[group]
        group_report = {"tare_g": {}, "net_food_g": {}, "ground_truth_net_total_g":
                        sum(truth["net_food_g"].values()),
                        "predicted_net_total_g": None,
                        "tare_ground_truth_g": dict(truth["tare_g"]),
                        "quantities": truth.get("quantities", {})}
        for kind in ("tare_g", "net_food_g"):
            predicted = pred.get(kind, {})
            for item, actual in truth[kind].items():
                if item not in predicted:
                    raise ValueError(f"Missing {group} {kind} prediction for {item}")
                value = float(predicted[item])
                if value < 0:
                    raise ValueError(f"Predicted mass cannot be negative: {group}/{item}")
                delta = value - actual
                group_report[kind][item] = {"ground_truth_g": actual,
                                            "predicted_g": value,
                                            "error_g": delta}
                errors.append({"group": group, "kind": kind, "item": item,
                               "ground_truth_g": actual, "predicted_g": value,
                               "absolute_error_g": abs(delta)})
        group_report["predicted_net_total_g"] = sum(
            float(pred["net_food_g"][item]) for item in truth["net_food_g"])
        output_groups[group] = group_report
    food_errors = [row["absolute_error_g"] for row in errors if row["kind"] == "net_food_g"]
    tare_errors = [row["absolute_error_g"] for row in errors if row["kind"] == "tare_g"]
    total_errors = [abs(output_groups[group]["predicted_net_total_g"] -
                        output_groups[group]["ground_truth_net_total_g"])
                    for group in GROUND_TRUTH]
    return {
        "report_kind": "one_time_exploratory_aruco_mass_report",
        "candidate_id": candidate["candidate_id"],
        "created_at": datetime.now(UTC).isoformat(),
        "physical_group_count": 6,
        "source_frame_count": frame_count,
        "training_or_tuning_use": False,
        "generalization_claim": False,
        "tare_and_net_food_reported_separately": True,
        "net_component_mae_g": statistics.mean(food_errors),
        "meal_net_total_mae_g": statistics.mean(total_errors),
        "tare_mae_g": statistics.mean(tare_errors),
        "groups": output_groups,
        "limitations": ["six physical meals only", "exploratory, not a generalization estimate",
                        "no real depth accuracy claim"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True,
                        help="Frozen candidate JSON with frozen=true and candidate_id")
    parser.add_argument("--predictions", type=Path, required=True,
                        help="One-time frozen-candidate predictions JSON for six groups")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "data/reports/aruco_synthetic_pilot.json")
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f"The one-time report already exists and will not be overwritten: {args.out}")
    report = build_report(json.loads(args.candidate.read_text(encoding="utf-8")),
                          json.loads(args.predictions.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote exploratory six-group report: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
