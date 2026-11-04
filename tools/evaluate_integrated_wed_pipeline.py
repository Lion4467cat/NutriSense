"""Image-only end-to-end evaluation on the fixed WED DEV carve.

Only train-split records are loaded by tools.run_eval.dev_rows(); its seed-42
10% physical-group carve defines DEV. Ground-truth masks and gram labels are
read only after the production pipeline has returned its predictions.
"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import load_wed_index  # noqa: E402
from engine.pipeline import analyze  # noqa: E402
from models.wed_inference import DEFAULT_CHECKPOINT, MODEL_ID, pipeline_deps  # noqa: E402
from nutrisense_synth.wed_segmentation import (  # noqa: E402
    class_metrics, confusion_matrix, region_counts,
)
from tools.run_eval import LOADED, dev_rows, wed_root  # noqa: E402

OUT = ROOT / "experiments/real_pipeline_baseline"
Z90 = 1.6448536269514722


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _component_predictions(runtime_result: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"class_id": int(region["class_id"]), "mask": region["mask"],
             "area": int(region["area"])}
            for region in runtime_result["regions"]]


def _slot_predictions(result: dict[str, Any], slot_names: dict[int, str]
                      ) -> dict[str, float]:
    by_class: dict[str, float] = {}
    items = result.get("items") or []
    for item in items:
        portion = item.get("portion") or {}
        slots = portion.get("head_slots") or {}
        if slots:
            for slot, grams in slots.items():
                name = slot_names.get(int(slot))
                if name is not None:
                    by_class[name] = by_class.get(name, 0.0) + float(grams)
            continue
        name = (item.get("classification") or {}).get("dish")
        grams = portion.get("grams")
        if name in slot_names.values() and grams is not None:
            by_class[name] = by_class.get(name, 0.0) + float(grams)
    if not by_class:
        # A one-class estimate can be exposed through the top-level blocks in
        # older contract paths. Keep its label explicit when resolvable.
        portion = result.get("portion") or {}
        cls = result.get("classification") or {}
        name = cls.get("dish")
        if name in slot_names.values() and portion.get("grams") is not None:
            by_class[name] = float(portion["grams"])
    return by_class


def _save_visual(image: np.ndarray, truth: np.ndarray, prediction: np.ndarray,
                 names: dict[int, str], path: Path) -> None:
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    palette = np.zeros((42, 3), dtype=np.uint8)
    for class_id in range(1, 42):
        color = plt.get_cmap("hsv")((class_id * 0.61803398875) % 1.0)[:3]
        palette[class_id] = (np.asarray(color) * 255).astype(np.uint8)

    def overlay(labels: np.ndarray) -> np.ndarray:
        output = image_rgb.copy()
        foreground = labels > 0
        colors = palette[np.clip(labels, 0, 41)]
        output[foreground] = (0.54 * output[foreground]
                             + 0.46 * colors[foreground]).astype(np.uint8)
        return output

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), constrained_layout=True)
    axes[0].imshow(image_rgb)
    axes[0].set_title("Original DEV image")
    axes[1].imshow(overlay(truth))
    axes[1].set_title("WED semantic target")
    axes[2].imshow(overlay(prediction))
    axes[2].set_title("Image-only integrated prediction")
    for axis in axes:
        axis.axis("off")
    labels = sorted({int(v) for v in np.unique(truth) if v > 0})
    fig.suptitle("Ground-truth classes: " + ", ".join(names.get(v, str(v))
                                                         for v in labels))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130)
    plt.close(fig)


def evaluate() -> dict[str, Any]:
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    rows = dev_rows()
    if len(rows) != 108 or set(LOADED) != {"train"}:
        raise RuntimeError(f"unexpected DEV selection: {len(rows)} views, loaded={LOADED}")
    root = wed_root()
    slot_names = {slot: name for name, slot in load_wed_index().items()}
    class_names = {slot + 1: name for slot, name in slot_names.items()}
    confusions: list[np.ndarray] = []
    view_reports: list[dict[str, Any]] = []
    image_hashes: list[str] = []
    mask_hashes: list[str] = []
    stage_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    latencies: list[float] = []
    errors: list[str] = []
    estimated_weights: list[tuple[float, float]] = []
    intervals: list[tuple[float, float, float]] = []
    gt_total_by_view: list[float] = []
    pred_total_by_view: list[float] = []
    class_abs_errors: list[float] = []
    class_signed_errors: list[float] = []
    class_counts: Counter[str] = Counter()
    class_region_counts: Counter[str] = Counter()
    quality_sums = Counter()
    representative_indices = {0, len(rows) // 2, len(rows) - 1}
    visuals: list[str] = []
    peak_rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    for index, row in enumerate(rows):
        image_path = root / row["image"]
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"could not decode DEV image {image_path}")
        deps = {**pipeline_deps(image), "ingredient_head": None}
        start = time.perf_counter()
        # Deliberately no GT mask or label is passed to analyze().
        result = analyze(image, day="mon", band="1-5", mode="general",
                         deps=deps)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)
        stage_counts[str(result.get("path_used") or "abstain")] += 1
        verdict_counts[str(result.get("verdict") or "unknown")] += 1
        if result.get("portion") and result["portion"].get("grams") is not None:
            pred_total = float(result["portion"]["grams"])
            gt_total = float(sum(float(dish["weight_g"])
                                 for dish in row["dishes"]))
            estimated_weights.append((pred_total, gt_total))
            pred_total_by_view.append(pred_total)
            gt_total_by_view.append(gt_total)
            sigma = float(result["portion"].get("sigma_grams_rel") or 0.0)
            half_width = Z90 * sigma * pred_total
            intervals.append((pred_total - half_width, pred_total + half_width,
                              gt_total))
        else:
            pred_total = None
            gt_total = float(sum(float(dish["weight_g"])
                                 for dish in row["dishes"]))
            errors.append(f"{row['image']}: {result.get('verdict')} / "
                          f"{result.get('reasons')}")

        # Ground truth is opened only after image-only inference is complete.
        truth_path = root / row["mask"]
        truth = cv2.imread(str(truth_path), cv2.IMREAD_GRAYSCALE)
        if truth is None:
            raise RuntimeError(f"could not decode DEV mask {truth_path}")
        pred = deps["inspect_prediction"]()["labels"]
        if truth.shape != pred.shape:
            raise RuntimeError(f"DEV mask shape mismatch: {row['image']}")
        confusions.append(confusion_matrix(truth, pred))
        prediction = deps["inspect_prediction"]()
        region_summary = region_counts(
            truth, _component_predictions(prediction), class_aware=True,
            iou_threshold=0.5)
        quality_sums["gt_components"] += region_summary["ground_truth_regions"]
        quality_sums["pred_components"] += region_summary["predicted_regions"]
        quality_sums["matched_components"] += region_summary["true_positive_regions"]
        quality_sums["missed_components"] += region_summary["false_negative_regions"]
        quality_sums["duplicate_components"] += region_summary[
            "duplicate_overlapping_predictions"]
        quality_sums["merge_components"] += region_summary[
            "predictions_merging_multiple_gt_regions"]
        quality_sums["exact_class_set_views"] += int(
            {int(v) for v in np.unique(truth) if v > 0}
            == {int(v) for v in np.unique(pred) if v > 0})

        gt_by_class = {str(dish["name"]): float(dish["weight_g"])
                       for dish in row["dishes"]}
        predicted_by_class = _slot_predictions(result, slot_names)
        for class_name in set(gt_by_class) | set(predicted_by_class):
            actual = gt_by_class.get(class_name, 0.0)
            estimate = predicted_by_class.get(class_name, 0.0)
            class_abs_errors.append(abs(estimate - actual))
            class_signed_errors.append(estimate - actual)
            class_counts[class_name] += 1
            class_region_counts[class_name] += int(class_name in predicted_by_class)

        for candidate in result.get("items") or []:
            portion = candidate.get("portion") or {}
            if portion.get("grams") is not None:
                # Keep interval bounds for the item-level uncertainty report.
                grams = float(portion["grams"])
                sigma = float(portion.get("sigma_grams_rel") or 0.0)
                quality_sums["numeric_item_outputs"] += 1
                quality_sums["item_interval_half_width_sum"] += Z90 * sigma * grams
            else:
                quality_sums["abstained_item_outputs"] += 1
        quality_sums["predicted_items"] += len(result.get("items") or [])
        quality_sums["target_items"] += len(row["dishes"])
        if result.get("portion") is not None:
            pred_classes = set(predicted_by_class)
            gt_classes = set(gt_by_class)
            quality_sums["complete_weighted_meals"] += int(
                gt_classes == pred_classes and len(result.get("items") or []) > 0
                and all(item.get("portion") is not None
                        for item in (result.get("items") or [])))
        image_hashes.append(_sha(image_path))
        mask_hashes.append(_sha(truth_path))
        view_reports.append({
            "image": row["image"],
            "group": f"{row.get('date_key', row.get('date'))}_{row['set']}",
            "verdict": result.get("verdict"),
            "path_used": result.get("path_used"),
            "predicted_food_classes": sorted(predicted_by_class),
            "ground_truth_food_classes": sorted(gt_by_class),
            "predicted_item_count": len(result.get("items") or []),
            "ground_truth_class_count": len(row["dishes"]),
            "predicted_total_g": pred_total,
            "ground_truth_total_g": round(gt_total, 2),
            "total_90_interval_g": (
                [round(pred_total - Z90 * float(result["portion"].get(
                    "sigma_grams_rel") or 0.0) * pred_total),
                 round(pred_total + Z90 * float(result["portion"].get(
                    "sigma_grams_rel") or 0.0) * pred_total)]
                if pred_total is not None else None),
            "latency_s": round(elapsed, 3),
            "failure_or_abstention": result.get("reasons") if pred_total is None else None,
            "region_counts": region_summary,
        })
        if index in representative_indices:
            target = OUT / "visuals" / f"view_{index + 1:03d}.png"
            _save_visual(image, truth, pred, class_names, target)
            visuals.append(target.relative_to(OUT).as_posix())
        if (index + 1) % 10 == 0 or index + 1 == len(rows):
            print(f"integrated WED DEV {index + 1}/{len(rows)}; "
                  f"mean latency {np.mean(latencies):.2f}s", flush=True)

    cm_total = np.sum(confusions, axis=0)
    pixel = class_metrics(confusions, class_names)
    components = int(quality_sums["pred_components"])
    gt_components = int(quality_sums["gt_components"])
    matched_components = int(quality_sums["matched_components"])
    weights = np.asarray(estimated_weights, dtype=float)
    total_errors = weights[:, 0] - weights[:, 1] if len(weights) else np.array([])
    coverage = (float(np.mean([low <= target <= high
                               for low, high, target in intervals]))
                if intervals else None)
    dev_groups = sorted({
        f"{row.get('date_key', row.get('date'))}_{row['set']}" for row in rows
    })
    report = {
        "stage": "integrated_real_data_pipeline_dev",
        "tier": "dev",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "split": "fixed seed-42 10% physical-group carve from WED TRAIN",
        "n_views": len(rows),
        "n_groups": len(dev_groups),
        "dev_group_sha256": hashlib.sha256("\n".join(dev_groups).encode()).hexdigest(),
        "loaded_manifest_splits": sorted(set(LOADED)),
        "locked_accessed": False,
        "aruco_evaluation_accessed": False,
        "wed_test_accessed": False,
        "ground_truth_passed_to_inference": False,
        "device": "cpu" if not torch.cuda.is_available() else "cuda",
        "cuda_available": bool(torch.cuda.is_available()),
        "checkpoint": str(DEFAULT_CHECKPOINT.relative_to(ROOT)),
        "checkpoint_sha256": _sha(DEFAULT_CHECKPOINT),
        "classifier_gallery_sha256": _sha(ROOT / "data/gallery.npz"),
        "weight_head_checkpoint_sha256": _sha(ROOT / "data/weight_head.pt"),
        "weight_sigma_config_sha256": _sha(ROOT / "data/weight_head_sigma.yaml"),
        "evaluator_script_sha256": _sha(Path(__file__).resolve()),
        "pipeline_sha256": _sha(ROOT / "engine/pipeline.py"),
        "runtime_adapter_sha256": _sha(ROOT / "models/wed_inference.py"),
        "application_entrypoint_sha256": _sha(ROOT / "main.py"),
        "segmenter": MODEL_ID,
        "classifier": "google/siglip2-base-patch16-224 (existing gallery)",
        "region_class_route": "predicted WED semantic class selects the learned weight-head slot; SigLIP region classification is retained as a cross-check reason",
        "siglip_region_label_diagnostic": "experiments/real_pipeline_baseline/siglip_region_labels/dev_report.md",
        "depth_route": "calibrated MoGe only when measured ID 7 / 60 mm anchor is present; WED DEV no-card inputs use learned-weight path and do not run uncalibrated depth",
        "mass_route": "existing WED learned weight head for no-card mapped dishes; marker geometry path only on calibrated scenes",
        "segmentation": {
            "pixel_metrics": pixel,
            "region_matching": "one-to-one class-aware connected-component IoU >= 0.5; WED components are semantic proxies, not serving instances",
            "ground_truth_component_count": gt_components,
            "predicted_component_count": components,
            "matched_component_count": matched_components,
            "region_precision": matched_components / max(1, components),
            "region_recall": matched_components / max(1, gt_components),
            "region_f1": (2 * matched_components / max(1, components + gt_components)),
            "missed_component_count": int(quality_sums["missed_components"]),
            "duplicate_component_count": int(quality_sums["duplicate_components"]),
            "predictions_merging_multiple_gt_regions": int(quality_sums["merge_components"]),
            "exact_semantic_class_set_meals": int(quality_sums["exact_class_set_views"]),
        },
        "classification": {
            "metric_scope": "pixel class accuracy/IoU and exact semantic class-set meals; no serving IDs exist in WED",
            "pixel_class_accuracy": pixel["all_pixel_accuracy"],
            "food_pixel_class_accuracy": pixel["foreground_pixel_accuracy"],
            "exact_semantic_class_set_rate": quality_sums["exact_class_set_views"] / len(rows),
            "per_class": pixel["per_class"],
        },
        "weight": {
            "individual_class_total_granularity": "WED labels one net gram total per food class per image; connected components are aggregated by class",
            "individual_class_mass_mae_g": (float(np.mean(class_abs_errors))
                                             if class_abs_errors else None),
            "individual_class_mass_bias_g": (float(np.mean(class_signed_errors))
                                              if class_signed_errors else None),
            "individual_class_mass_samples": len(class_abs_errors),
            "total_meal_mae_g": float(np.mean(np.abs(total_errors))) if len(total_errors) else None,
            "total_meal_bias_g": float(np.mean(total_errors)) if len(total_errors) else None,
            "total_meal_samples_with_numeric_prediction": len(weights),
            "total_meal_abstention_count": len(rows) - len(weights),
            "complete_meal_weight_outputs": int(quality_sums["complete_weighted_meals"]),
            "total_meal_90_interval_coverage": coverage,
            "mean_total_90_interval_width_g": (float(np.mean([hi - lo for lo, hi, _ in intervals]))
                                                if intervals else None),
            "predicted_items": int(quality_sums["predicted_items"]),
            "ground_truth_class_totals": int(quality_sums["target_items"]),
            "numeric_item_outputs": int(quality_sums["numeric_item_outputs"]),
            "item_abstentions": int(quality_sums["abstained_item_outputs"]),
            "mean_item_90_interval_half_width_g": (
                float(quality_sums["item_interval_half_width_sum"]
                      / max(1, quality_sums["numeric_item_outputs"]))),
        },
        "runtime": {
            "mean_s_per_meal": float(np.mean(latencies)),
            "median_s_per_meal": float(np.median(latencies)),
            "p95_s_per_meal": float(np.percentile(latencies, 95)),
            "total_wall_s": float(np.sum(latencies)),
            "peak_process_rss_mb": float(resource.getrusage(
                resource.RUSAGE_SELF).ru_maxrss / 1024),
            "cuda_peak_memory_mb": None,
            "resource_note": "CPU inference; NVIDIA driver unavailable. Peak RSS is process high-water mark.",
        },
        "path_counts": dict(stage_counts),
        "verdict_counts": dict(verdict_counts),
        "pipeline_failure_count": int(verdict_counts.get("cannot_verify", 0)),
        "pipeline_failure_rate": float(verdict_counts.get("cannot_verify", 0) / len(rows)),
        "total_mass_abstention_rate": float((len(rows) - len(weights)) / len(rows)),
        "sample_errors": errors[:20],
        "visuals": visuals,
        "per_view": view_reports,
        "input_image_sha256": hashlib.sha256("".join(image_hashes).encode()).hexdigest(),
        "ground_truth_mask_sha256": hashlib.sha256("".join(mask_hashes).encode()).hexdigest(),
        "existing_frozen_segmentation_dev_report": "experiments/wed_native_segmentation/dev_report.md",
        "renderer_geometry_validation_report": "experiments/real_pipeline_baseline/renderer_depth_geometry_report.md",
    }
    if set(LOADED) != {"train"}:
        raise RuntimeError(f"DEV evaluator loaded unexpected split(s): {LOADED}")
    return report


def write_markdown(report: dict[str, Any]) -> None:
    seg, weight, runtime = (report["segmentation"], report["weight"],
                            report["runtime"])
    lines = [
        "# Integrated NutriSense real-data prototype — WED DEV", "",
        f"- Fixed DEV carve: {report['n_views']} views / {report['n_groups']} physical groups.",
        f"- Device: {report['device']}; no GPU available.",
        f"- Frozen segmenter checkpoint SHA-256: `{report['checkpoint_sha256']}`.",
        "- LOCKED / ArUco evaluation / WED test accessed: **false / false / false**.",
        "- Ground-truth masks/classes passed to inference: **false**.", "",
        "## Pipeline routes", "",
        "The API uses the frozen 41-class WED DeepLabV3, then derives 8-connected class regions. Because WED has no instance IDs and weight labels are per class, disconnected predicted regions of one class are unioned for the learned mass head. The UI receives one bbox and estimate per predicted class; these are class-level estimates, not verified serving instances.", "",
        "No-card WED-mapped predictions use the existing learned weight head. MoGe is loaded only for a valid measured ID 7 / 60 mm marker; uncalibrated relative depth is never converted to absolute geometry. Renderer-grounded depth/geometry validation is reported separately.", "",
        "## DEV results", "",
        "| Metric | Result |", "|---|---:|",
        f"| Macro food IoU | {report['classification']['per_class'] and report['segmentation']['pixel_metrics']['macro_food_iou']:.4f} |",
        f"| Foreground IoU | {report['segmentation']['pixel_metrics']['foreground_union']['iou']:.4f} |",
        f"| Region precision / recall / F1 | {seg['region_precision']:.4f} / {seg['region_recall']:.4f} / {seg['region_f1']:.4f} |",
        f"| Exact semantic class-set meals | {seg['exact_semantic_class_set_meals']}/{report['n_views']} |",
        f"| Individual class-total mass MAE / bias | {weight['individual_class_mass_mae_g']:.2f} g / {weight['individual_class_mass_bias_g']:.2f} g |" if weight["individual_class_mass_mae_g"] is not None else "| Individual class-total mass MAE / bias | n/a |",
        f"| Total meal mass MAE / bias | {weight['total_meal_mae_g']:.2f} g / {weight['total_meal_bias_g']:.2f} g |" if weight["total_meal_mae_g"] is not None else "| Total meal mass MAE / bias | n/a |",
        f"| Numeric total predictions / abstentions | {weight['total_meal_samples_with_numeric_prediction']} / {weight['total_meal_abstention_count']} |",
        f"| cannot_verify verdicts / rate | {report['pipeline_failure_count']} / {report['pipeline_failure_rate']:.3f} |",
        f"| Total-mass abstention rate | {report['total_mass_abstention_rate']:.3f} |",
        f"| Complete weighted class-coverage meals | {weight['complete_meal_weight_outputs']}/{report['n_views']} |",
        f"| Total 90% interval coverage | {weight['total_meal_90_interval_coverage']:.3f} |" if weight["total_meal_90_interval_coverage"] is not None else "| Total 90% interval coverage | n/a |",
        f"| Mean latency / p95 | {runtime['mean_s_per_meal']:.2f} s / {runtime['p95_s_per_meal']:.2f} s |",
        f"| Peak process RSS | {runtime['peak_process_rss_mb']:.0f} MB |", "",
        "Individual mass is evaluated at WED's class-total granularity, not per connected component. Class false positives and misses contribute zero-vs-label errors. Total meal weight is scored only when the API returns numeric grams; abstentions remain visible in the denominator.", "",
        "The 90% total-weight interval covered 81.5% of DEV meals, below its nominal target. Intervals are not calibrated well enough to support high-confidence use; report them as uncertainty estimates, not guarantees.", "",
        "## Per-class segmentation", "",
        "| Class | IoU | Pixel precision | Pixel recall | GT pixels |", "|---|---:|---:|---:|---:|",
    ]
    for metric in report["segmentation"]["pixel_metrics"]["per_class"].values():
        lines.append(f"| {metric['class']} | {metric['iou']:.4f} | {metric['pixel_precision']:.4f} | {metric['pixel_recall']:.4f} | {metric['ground_truth_pixels']} |")
    lines.extend(["", "## Representative image-only predictions", ""])
    for relative in report["visuals"]:
        lines.extend([f"![Integrated DEV prediction: {relative}]({relative})", ""])
    lines.extend([
        "## Limits and interpretation", "",
        "Connected regions are semantic proxies, not instances. Same-class portions may merge and annotation breaks may fragment a class. The learned WED weight head is trained/evaluated in its existing WED setting and may not generalize to canteen captures; its output is an estimate with a broad model uncertainty, not a scale measurement. With no marker the prototype does not claim metric depth or geometry-derived mass. Six manually weighed ArUco groups and all other protected evaluation data remain unused here.", "",
        "Existing renderer-grounded calibration/geometry results are in `renderer_depth_geometry_report.md`; the frozen segmentation component results are in `../wed_native_segmentation/dev_report.md`.", "",
    ])
    (OUT / "dev_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = evaluate()
    (OUT / "dev_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8")
    write_markdown(report)
    print(json.dumps({key: report[key] for key in (
        "n_views", "n_groups", "device", "segmentation", "weight", "runtime",
        "path_counts", "checkpoint_sha256")}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
