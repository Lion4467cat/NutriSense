"""Pure helpers for end-to-end food-mass evaluation reports."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import numpy as np

from nutrisense_synth.evaluation import group_bootstrap_ci


def extract_food_mass_g(wire: dict[str, Any]) -> float | None:
    """Read the pipeline's net food mass, never plate/bowl tare."""
    candidates = [
        (wire.get("nutrition") or {}).get("grams"),
        (wire.get("portion") or {}).get("grams"),
    ]
    for value in candidates:
        try:
            grams = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(grams) and grams >= 0:
            return grams
    return None


def summarize_end_to_end(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize per-view meal totals with group-bootstrap uncertainty.

    A critical failure includes a missing/invalid mass or a returned item
    count that differs from the ground-truth meal component count. MAE is
    reported among returned masses alongside coverage and failure rate.
    """
    if not rows:
        raise ValueError("End-to-end summary requires at least one DEV view")
    valid = [row for row in rows if row.get("predicted_mass_g") is not None]
    errors_by_group: dict[str, list[float]] = defaultdict(list)
    for row in valid:
        errors_by_group[str(row["group"])].append(
            float(row["predicted_mass_g"]) - float(row["ground_truth_mass_g"]))
    abs_errors = [abs(error) for values in errors_by_group.values() for error in values]
    signed_errors = [error for values in errors_by_group.values() for error in values]
    critical = [bool(row.get("critical_failure")) for row in rows]
    return {
        "n_views": len(rows),
        "n_groups": len({str(row["group"]) for row in rows}),
        "n_mass_predictions": len(valid),
        "mass_return_rate": len(valid) / len(rows),
        "meal_mass_mae_g_returned": float(np.mean(abs_errors)) if abs_errors else None,
        "meal_mass_bias_g_returned": float(np.mean(signed_errors)) if signed_errors else None,
        "meal_mass_mae_g_group_bootstrap_95ci": group_bootstrap_ci(
            {group: [abs(error) for error in errors]
             for group, errors in errors_by_group.items()}),
        "critical_failures": int(sum(critical)),
        "critical_failure_rate": float(np.mean(critical)),
        "n_complete_item_outputs": sum(bool(row.get("complete_items")) for row in rows),
    }


def compare_regions_to_semantic_mask(labels: np.ndarray,
                                    class_ids: list[int],
                                    item_masks: list[np.ndarray]) -> dict[str, Any]:
    """Keep food-foreground quality separate from semantic-region proposals.

    WED labels food classes within one plate; SAM proposals are unlabeled food
    regions. Union IoU measures foreground segmentation. Best per-class IoU and
    GT-pixel recall describe proposal overlap without claiming instance AP.
    """
    labels = np.asarray(labels)
    truth = np.isin(labels, [int(class_id) for class_id in class_ids])
    resized: list[np.ndarray] = []
    for item in item_masks:
        mask = np.asarray(item, dtype=bool)
        if mask.shape != truth.shape:
            import cv2
            mask = cv2.resize(mask.astype(np.uint8),
                              (truth.shape[1], truth.shape[0]),
                              interpolation=cv2.INTER_NEAREST).astype(bool)
        resized.append(mask)
    pred = np.logical_or.reduce(resized) if resized else np.zeros_like(truth)
    union = int(np.count_nonzero(pred | truth))
    denominator = int(pred.sum() + truth.sum())
    details = []
    for class_id in class_ids:
        gt = labels == int(class_id)
        if not gt.any():
            continue
        best_iou, best_recall = 0.0, 0.0
        for mask in resized:
            intersection = int(np.count_nonzero(mask & gt))
            item_union = int(np.count_nonzero(mask | gt))
            best_iou = max(best_iou,
                           intersection / item_union if item_union else 1.0)
            best_recall = max(best_recall, intersection / int(gt.sum()))
        details.append({"class_id": int(class_id), "best_iou": best_iou,
                        "best_gt_area_recall": best_recall,
                        "ground_truth_area_fraction": float(gt.mean())})
    n = len(details)
    return {
        "foreground_union_iou": (
            float(np.count_nonzero(pred & truth)) / union if union else 1.0),
        "foreground_union_dice": (
            float(2 * np.count_nonzero(pred & truth)) / denominator
            if denominator else 1.0),
        "predicted_region_count": len(resized),
        "ground_truth_semantic_region_count": n,
        "semantic_region_iou_at_0_5": (
            sum(x["best_iou"] >= 0.5 for x in details) / n if n else 0.0),
        "semantic_region_gt_recall_at_0_5": (
            sum(x["best_gt_area_recall"] >= 0.5 for x in details) / n
            if n else 0.0),
        "semantic_regions": details,
    }


def summarize_segmentation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Segmentation summary requires at least one DEV view")
    fields = ("foreground_union_iou", "foreground_union_dice",
              "semantic_region_iou_at_0_5",
              "semantic_region_gt_recall_at_0_5")
    groups: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list))
    for row in rows:
        for key in fields:
            groups[str(row["group"])][key].append(float(row[key]))
    return {
        "n_views": len(rows),
        "n_groups": len(groups),
        "mean_predicted_regions": float(np.mean(
            [row["predicted_region_count"] for row in rows])),
        "mean_ground_truth_semantic_regions": float(np.mean(
            [row["ground_truth_semantic_region_count"] for row in rows])),
        **{key: float(np.mean([row[key] for row in rows])) for key in fields},
        "group_bootstrap_95ci": {
            key: group_bootstrap_ci({group: [float(np.mean(values[key]))]
                                     for group, values in groups.items()})
            for key in fields
        },
    }
