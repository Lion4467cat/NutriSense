"""Metrics for WED semantic masks and derived class-agnostic regions."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

N_CLASSES = 42


def confusion_matrix(truth: np.ndarray, prediction: np.ndarray) -> np.ndarray:
    truth = np.asarray(truth, dtype=np.int64)
    prediction = np.asarray(prediction, dtype=np.int64)
    if truth.shape != prediction.shape:
        raise ValueError("truth and prediction shapes must match")
    valid = ((truth >= 0) & (truth < N_CLASSES)
             & (prediction >= 0) & (prediction < N_CLASSES))
    encoded = N_CLASSES * truth[valid] + prediction[valid]
    return np.bincount(encoded, minlength=N_CLASSES ** 2).reshape(
        N_CLASSES, N_CLASSES)


def class_metrics(confusions: list[np.ndarray], class_names: dict[int, str]
                  ) -> dict[str, Any]:
    total = np.sum(confusions, axis=0, dtype=np.int64)
    result: dict[str, Any] = {}
    for class_id in range(1, N_CLASSES):
        tp = int(total[class_id, class_id])
        fp = int(total[:, class_id].sum() - tp)
        fn = int(total[class_id, :].sum() - tp)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        union = tp + fp + fn
        iou = tp / union if union else 0.0
        dice = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
        result[str(class_id)] = {
            "class": class_names.get(class_id, str(class_id)),
            "pixel_precision": precision,
            "pixel_recall": recall,
            "iou": iou,
            "dice": dice,
            "ground_truth_pixels": int(total[class_id, :].sum()),
            "predicted_pixels": int(total[:, class_id].sum()),
        }
    present = [value for value in result.values()
               if value["ground_truth_pixels"] > 0]
    diagonal = int(np.trace(total))
    union = int(total.sum())
    return {
        "per_class": result,
        "macro_food_iou": float(np.mean([v["iou"] for v in present])),
        "macro_food_dice": float(np.mean([v["dice"] for v in present])),
        "foreground_pixel_accuracy": (
            float(sum(int(total[i, i]) for i in range(1, N_CLASSES))
                  / max(1, int(total[1:, :].sum())))),
        "all_pixel_accuracy": diagonal / max(1, union),
        "foreground_union": _foreground_metrics(total),
    }


def _foreground_metrics(confusion: np.ndarray) -> dict[str, float]:
    truth_food = int(confusion[1:, :].sum())
    pred_food = int(confusion[:, 1:].sum())
    tp = int(confusion[1:, 1:].sum())
    fp = pred_food - tp
    fn = truth_food - tp
    union = tp + fp + fn
    denom = 2 * tp + fp + fn
    return {
        "precision": tp / max(1, pred_food),
        "recall": tp / max(1, truth_food),
        "iou": tp / union if union else 1.0,
        "dice": 2 * tp / denom if denom else 1.0,
    }


def connected_regions(labels: np.ndarray, *, class_aware: bool
                      ) -> list[dict[str, Any]]:
    """Create deterministic 8-connected regions from a semantic raster.

    For class-agnostic comparison, all food pixels form one binary mask.
    For class-aware matching, each class is connected-component labeled
    separately, retaining a class on every derived region.
    """
    labels = np.asarray(labels)
    regions: list[dict[str, Any]] = []
    for class_id in range(1, N_CLASSES):
        binary = labels == class_id
        if not binary.any():
            continue
        count, component_labels, stats, _ = cv2.connectedComponentsWithStats(
            binary.astype(np.uint8), connectivity=8)
        for component_id in range(1, count):
            area = int(stats[component_id, cv2.CC_STAT_AREA])
            if area == 0:
                continue
            regions.append({
                "class_id": int(class_id) if class_aware else None,
                "mask": component_labels == component_id,
                "area": area,
            })
    return regions


def region_counts(truth: np.ndarray, predictions: list[dict[str, Any]], *,
                  class_aware: bool, iou_threshold: float = 0.5
                  ) -> dict[str, Any]:
    """One-to-one Hungarian region matching and duplicate/miss diagnostics."""
    gt_regions = connected_regions(truth, class_aware=class_aware)
    pred_regions = predictions
    overlaps = np.zeros((len(gt_regions), len(pred_regions)), dtype=np.float64)
    intersections = np.zeros_like(overlaps, dtype=np.int64)
    for gi, gt in enumerate(gt_regions):
        gt_mask = gt["mask"]
        for pi, pred in enumerate(pred_regions):
            if (class_aware and pred.get("class_id") is not None
                    and pred["class_id"] != gt["class_id"]):
                continue
            pred_mask = pred["mask"]
            inter = int(np.count_nonzero(gt_mask & pred_mask))
            intersections[gi, pi] = inter
            union = gt["area"] + int(pred.get("area", pred_mask.sum())) - inter
            overlaps[gi, pi] = inter / union if union else 0.0
    matched: list[tuple[int, int]] = []
    if overlaps.size:
        gt_indices, pred_indices = linear_sum_assignment(-overlaps)
        matched = [(int(gi), int(pi)) for gi, pi in zip(gt_indices, pred_indices)
                   if overlaps[gi, pi] >= iou_threshold]
    matched_gt = {gi for gi, _ in matched}
    matched_pred = {pi for _, pi in matched}
    unmatched_predictions = [i for i in range(len(pred_regions))
                             if i not in matched_pred]
    duplicates = sum(bool(intersections[:, i].any())
                     for i in unmatched_predictions)
    spurious = len(unmatched_predictions) - duplicates
    merged = sum(int(np.count_nonzero(intersections[:, i])) >= 2
                 for i in range(len(pred_regions)))
    tp = len(matched)
    fp = len(pred_regions) - tp
    fn = len(gt_regions) - tp
    exact_region_recovery = (len(gt_regions) > 0 and tp == len(gt_regions)
                             and len(pred_regions) == len(gt_regions))
    return {
        "ground_truth_regions": len(gt_regions),
        "predicted_regions": len(pred_regions),
        "true_positive_regions": tp,
        "false_positive_regions": fp,
        "false_negative_regions": fn,
        "precision": tp / max(1, tp + fp),
        "recall": tp / max(1, tp + fn),
        "f1": 2 * tp / max(1, 2 * tp + fp + fn),
        "duplicate_overlapping_predictions": int(duplicates),
        "spurious_nonoverlapping_predictions": int(spurious),
        "predictions_merging_multiple_gt_regions": int(merged),
        "missed_semantic_regions": int(fn),
        "complete_region_recovery": bool(exact_region_recovery),
    }


def class_set_metrics(truth: np.ndarray, prediction: np.ndarray
                      ) -> dict[str, Any]:
    true_classes = set(map(int, np.unique(truth))) - {0}
    pred_classes = set(map(int, np.unique(prediction))) - {0}
    return {
        "ground_truth_class_ids": sorted(true_classes),
        "predicted_class_ids": sorted(pred_classes),
        "class_set_exact": true_classes == pred_classes,
        "missed_class_ids": sorted(true_classes - pred_classes),
        "extra_class_ids": sorted(pred_classes - true_classes),
    }


def group_bootstrap_ci(rows: list[dict[str, Any]], metric: str, *,
                       reps: int = 2000, seed: int = 42
                       ) -> list[float] | None:
    """Bootstrap a mean across physical groups, preserving group dependence."""
    group_values: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        value = row.get(metric)
        if value is not None:
            group_values[str(row["group"])].append(float(value))
    if not group_values:
        return None
    groups = sorted(group_values)
    means = np.asarray([np.mean(group_values[group]) for group in groups])
    if len(means) == 1:
        return [float(means[0]), float(means[0])]
    rng = np.random.default_rng(seed)
    samples = np.empty(reps, dtype=np.float64)
    for index in range(reps):
        selected = rng.integers(0, len(means), size=len(means))
        samples[index] = means[selected].mean()
    low, high = np.quantile(samples, [0.025, 0.975])
    return [float(low), float(high)]
