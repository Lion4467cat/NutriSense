"""Paired plate-bootstrap comparison of two matching outer-CV reports."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def _validate_pair(baseline: dict, candidate: dict) -> tuple[dict, dict]:
    for key in ("protocol", "seed", "folds", "encoder", "manifest_sha256"):
        if baseline.get(key) != candidate.get(key):
            raise ValueError(f"CV reports differ in {key}")
    base_plates = {}
    cand_plates = {}
    base_classes = {}
    cand_classes = {}
    base_folds = {}
    cand_folds = {}
    for report, plates, classes, fold_map in (
        (baseline, base_plates, base_classes, base_folds),
        (candidate, cand_plates, cand_classes, cand_folds),
    ):
        for fold in report["fold_results"]:
            outer = fold.get("outer_cv", fold)
            index = int(outer["fold_index"])
            if index in fold_map:
                raise ValueError(f"duplicate fold index {index}")
            fold_map[index] = outer
            plates.update(outer["per_plate_errors"])
            for name, stats in outer["per_class_errors"].items():
                acc = classes.setdefault(name, {"n_rois": 0,
                                                "sum_abs_err_g": 0.0})
                acc["n_rois"] += int(stats["n_rois"])
                acc["sum_abs_err_g"] += float(stats["sum_abs_err_g"])
    if set(base_folds) != set(cand_folds):
        raise ValueError("outer fold indices differ")
    for index, base_fold in base_folds.items():
        for key in ("held_out_plates", "train_plates",
                    "epoch_selection_plates", "excluded_dev_plates"):
            if base_fold.get(key) != cand_folds[index].get(key):
                raise ValueError(f"fold {index} differs in {key}")
    if set(base_plates) != set(cand_plates):
        raise ValueError("outer held-out plate sets differ")
    for plate in base_plates:
        if base_plates[plate]["n_rois"] != cand_plates[plate]["n_rois"]:
            raise ValueError(f"ROI count differs for plate {plate}")
    if set(base_classes) != set(cand_classes):
        raise ValueError("outer held-out class sets differ")
    for name in base_classes:
        if base_classes[name]["n_rois"] != cand_classes[name]["n_rois"]:
            raise ValueError(f"ROI count differs for class {name}")
    return (
        {"plates": base_plates, "classes": base_classes},
        {"plates": cand_plates, "classes": cand_classes},
    )


def compare(baseline: dict, candidate: dict, *, seed: int = 42,
            replicates: int = 10_000) -> dict:
    if replicates < 1:
        raise ValueError("replicates must be >= 1")
    base, cand = _validate_pair(baseline, candidate)
    names = sorted(base["plates"])
    n_by_plate = np.array([base["plates"][p]["n_rois"] for p in names])
    base_abs = np.array([base["plates"][p]["sum_abs_err_g"]
                         for p in names], dtype=float)
    cand_abs = np.array([cand["plates"][p]["sum_abs_err_g"]
                         for p in names], dtype=float)
    base_mae = float(base_abs.sum() / n_by_plate.sum())
    cand_mae = float(cand_abs.sum() / n_by_plate.sum())
    rng = np.random.default_rng(seed)
    deltas = np.empty(replicates, dtype=float)
    for i in range(replicates):
        draw = rng.integers(0, len(names), size=len(names))
        denom = n_by_plate[draw].sum()
        deltas[i] = ((cand_abs[draw].sum() - base_abs[draw].sum())
                     / max(1, denom))
    delta_ci = np.quantile(deltas, [0.025, 0.975]).tolist()

    class_results = {}
    class_regressions = []
    for name, b in sorted(base["classes"].items()):
        c = cand["classes"][name]
        b_mae = b["sum_abs_err_g"] / b["n_rois"]
        c_mae = c["sum_abs_err_g"] / c["n_rois"]
        regression = c_mae > b_mae * 1.10
        class_results[name] = {
            "n_rois": b["n_rois"],
            "baseline_mae_g": round(b_mae, 3),
            "candidate_mae_g": round(c_mae, 3),
            "relative_change_pct": round(100 * (c_mae - b_mae)
                                          / max(b_mae, 1e-9), 3),
        }
        if b["n_rois"] >= 50 and regression:
            class_regressions.append(name)

    def plate_total_mae(grouped: dict) -> float:
        return float(np.mean([abs(v["sum_signed_err_g"])
                              for v in grouped.values()]))

    base_plate_total = plate_total_mae(base["plates"])
    cand_plate_total = plate_total_mae(cand["plates"])
    base_bias = sum(v["sum_signed_err_g"] for v in base["plates"].values()) \
        / n_by_plate.sum()
    cand_bias = sum(v["sum_signed_err_g"] for v in cand["plates"].values()) \
        / n_by_plate.sum()
    paired_pass = bool(delta_ci[1] < 0)
    class_pass = bool(not class_regressions)
    plate_total_pass = bool(cand_plate_total <= base_plate_total * 1.05)
    bias_pass = bool(abs(cand_bias) <= abs(base_bias) + 2.0)
    return {
        "protocol": "paired outer-CV plate bootstrap",
        "baseline_tag": baseline.get("tag"),
        "candidate_tag": candidate.get("tag"),
        "n_outer_plates": len(names),
        "n_outer_rois": int(n_by_plate.sum()),
        "baseline_weighted_mae_g": round(base_mae, 3),
        "candidate_weighted_mae_g": round(cand_mae, 3),
        "paired_delta_mae_g": round(cand_mae - base_mae, 3),
        "paired_delta_plate_bootstrap_95ci_g": [
            round(float(delta_ci[0]), 3), round(float(delta_ci[1]), 3)],
        "baseline_mean_abs_plate_total_error_g": round(base_plate_total, 3),
        "candidate_mean_abs_plate_total_error_g": round(cand_plate_total, 3),
        "baseline_signed_bias_g": round(base_bias, 3),
        "candidate_signed_bias_g": round(cand_bias, 3),
        "high_support_class_regressions_over_10pct": class_regressions,
        "class_metrics": class_results,
        "gates": {
            "paired_mae_ci_below_zero": paired_pass,
            "no_high_support_class_regression_over_10pct": class_pass,
            "plate_total_error_regression_at_most_5pct": plate_total_pass,
            "absolute_bias_increase_at_most_2g": bias_pass,
        },
        "decision": "pass" if all((paired_pass, class_pass,
                                      plate_total_pass, bias_pass))
        else "reject",
        "bootstrap_seed": seed,
        "bootstrap_replicates": replicates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--replicates", type=int, default=10_000)
    args = parser.parse_args()
    result = compare(json.loads(args.baseline.read_text()),
                     json.loads(args.candidate.read_text()),
                     seed=args.seed, replicates=args.replicates)
    result["input_report_sha256"] = {
        "baseline": hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
        "candidate": hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
        "comparison_code": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
