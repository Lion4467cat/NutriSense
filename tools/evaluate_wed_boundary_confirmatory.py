"""Evaluate paired WED boundary-loss runs on the fixed DEV carve."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.wed_segmentation_variants import build_variant
from models.wed_semantic_segmenter import load_checkpoint
from nutrisense_synth.parameters import (
    read_wed_train_manifest, wed_dev_group_ids, wed_group_id,
)
from nutrisense_synth.wed_segmentation import (
    N_CLASSES, class_metrics, confusion_matrix,
)
from tools.analyze_wed_semantic_errors import _class_errors
from tools.evaluate_wed_segmentation_study import (
    SIZE_BINS, _aggregate, _boundary_counts, _load_candidate, _paired_bootstrap,
    _predict, _sha, _sha_data, _group_sufficient_counts, _metric_from_counts,
)

SEEDS = (42, 43, 44)
PRIORITY_NAMES = {"steamed rice", "papad", "salad", "leaf-dal",
                  "muskmelon", "tomato-pappu"}


def _component_diagnostics(truth: np.ndarray, prediction: np.ndarray
                           ) -> dict[str, Any]:
    height, width = truth.shape
    buckets = {"no_overlap": 0, "overlap_best_iou_lt_0_1": 0,
               "overlap_best_iou_0_1_to_0_25": 0,
               "overlap_best_iou_0_25_to_0_5": 0,
               "matched_iou_ge_0_5": 0}
    best_ious: list[float] = []
    best_coverages: list[float] = []
    overlap_counts: list[int] = []
    gt_tiny = 0
    for class_id in range(1, N_CLASSES):
        gt_count, gt_labels, gt_stats, _ = cv2.connectedComponentsWithStats(
            (truth == class_id).astype(np.uint8), connectivity=8)
        pred_count, pred_labels, _, _ = cv2.connectedComponentsWithStats(
            (prediction == class_id).astype(np.uint8), connectivity=8)
        gt_components = []
        for component_id in range(1, gt_count):
            area = int(gt_stats[component_id, cv2.CC_STAT_AREA])
            if area and area / float(height * width) < 0.001:
                gt_components.append((gt_labels == component_id, area))
        pred_components = [pred_labels == component_id
                           for component_id in range(1, pred_count)]
        for gt_mask, area in gt_components:
            gt_tiny += 1
            intersections = [int(np.count_nonzero(gt_mask & pred_mask))
                             for pred_mask in pred_components]
            positive = [value for value in intersections if value > 0]
            if not positive:
                buckets["no_overlap"] += 1
                best_ious.append(0.0)
                best_coverages.append(0.0)
                overlap_counts.append(0)
                continue
            best_intersection = max(positive)
            best_coverage = best_intersection / area
            best_iou = max(
                intersection / (area + int(pred_mask.sum()) - intersection)
                for intersection, pred_mask in zip(intersections, pred_components)
                if intersection > 0)
            best_ious.append(float(best_iou))
            best_coverages.append(float(best_coverage))
            overlap_counts.append(len(positive))
            if best_iou >= 0.5:
                buckets["matched_iou_ge_0_5"] += 1
            elif best_iou < 0.1:
                buckets["overlap_best_iou_lt_0_1"] += 1
            elif best_iou < 0.25:
                buckets["overlap_best_iou_0_1_to_0_25"] += 1
            else:
                buckets["overlap_best_iou_0_25_to_0_5"] += 1
    nonzero_iou = [value for value in best_ious if value > 0]
    return {
        "gt_tiny_components": gt_tiny,
        "best_iou_buckets": buckets,
        "no_overlap_components": buckets["no_overlap"],
        "partial_overlap_below_0_5": sum(
            buckets[key] for key in ("overlap_best_iou_lt_0_1",
                                      "overlap_best_iou_0_1_to_0_25",
                                      "overlap_best_iou_0_25_to_0_5")),
        "matched_iou_ge_0_5": buckets["matched_iou_ge_0_5"],
        "mean_best_iou_all_tiny": float(np.mean(best_ious)) if best_ious else None,
        "median_best_iou_when_overlapping": (
            float(np.median(nonzero_iou)) if nonzero_iou else None),
        "mean_best_pixel_coverage": float(np.mean(best_coverages)) if best_coverages else None,
        "gt_components_touched_by_multiple_pred_components": int(
            sum(count >= 2 for count in overlap_counts)),
    }


def _multi_seed_group_bootstrap(
        candidate_rows: dict[int, list[dict[str, Any]]],
        reference_rows: dict[int, list[dict[str, Any]]], metric: str,
        *, reps: int = 10_000, seed: int = 42) -> dict[str, Any]:
    candidate_states = {s: _group_sufficient_counts(rows)
                        for s, rows in candidate_rows.items()}
    reference_states = {s: _group_sufficient_counts(rows)
                        for s, rows in reference_rows.items()}
    seeds = sorted(set(candidate_states) & set(reference_states))
    groups = sorted(set.intersection(*[
        set(candidate_states[s]) & set(reference_states[s]) for s in seeds]))
    if not seeds or not groups:
        return {"point": None, "ci95": None}
    all_counts = sum((candidate_states[seeds[0]][g]["class_counts"]
                      for g in groups), start=np.zeros((N_CLASSES, 3), np.int64))
    present = [cid for cid in range(1, N_CLASSES)
               if all_counts[cid, 2] > 0]

    def delta(selected_groups: list[str]) -> float:
        per_seed = []
        for current_seed in seeds:
            c_value = _metric_from_counts(
                [candidate_states[current_seed][g] for g in selected_groups],
                metric, present)
            r_value = _metric_from_counts(
                [reference_states[current_seed][g] for g in selected_groups],
                metric, present)
            per_seed.append(c_value - r_value)
        return float(np.mean(per_seed))

    point = delta(groups)
    rng = np.random.default_rng(seed)
    samples = np.empty(reps, dtype=np.float64)
    for idx in range(reps):
        selected = [groups[int(i)] for i in rng.integers(0, len(groups), size=len(groups))]
        samples[idx] = delta(selected)
    low, high = np.quantile(samples, (0.025, 0.975))
    return {"point": point, "ci95": [float(low), float(high)],
            "bootstrap_unit": "physical meal group, paired within each of three seeds"}


def _mean_sd(values: list[float | None]) -> dict[str, float | None]:
    present = [float(x) for x in values if x is not None]
    return {"mean": float(np.mean(present)) if present else None,
            "sd_across_seeds": float(np.std(present, ddof=1)) if len(present) > 1 else None,
            "min": min(present) if present else None,
            "max": max(present) if present else None}


def _merge_seed_rows(run_rows: dict[int, list[dict[str, Any]]]
                     ) -> list[dict[str, Any]]:
    # Kept separate by seed for paired bootstrap; this helper only validates view alignment.
    first = run_rows[min(run_rows)]
    expected = [(r["group"], r["image"]) for r in first]
    for seed, rows in run_rows.items():
        if [(r["group"], r["image"]) for r in rows] != expected:
            raise AssertionError(f"DEV view order differs at seed {seed}")
    return first


def evaluate(*, output: Path, manifest: Path, wed_root: Path,
             frozen_checkpoint: Path, report_dir: Path,
             device_name: str = "cuda") -> dict[str, Any]:
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; use the approved GPU runtime")
    device = torch.device(device_name)
    training = json.loads((output / "training_report.json").read_text())
    if not training.get("pair_checks_passed") or len(training.get("runs", [])) != 6:
        raise ValueError("All three paired 20-epoch runs must pass finalization first")
    for item in training["runs"]:
        if item["training_budget"]["epochs_completed"] != 20:
            raise ValueError("Refusing DEV evaluation of incomplete training")

    manifest_rows = read_wed_train_manifest(manifest)
    dev_groups = wed_dev_group_ids(manifest_rows)
    dev_rows = [row for row in manifest_rows if wed_group_id(row) in dev_groups]
    if len(dev_rows) != 108 or len(dev_groups) != 21:
        raise ValueError("Expected the fixed 108-view / 21-group DEV carve")
    index_map = json.loads((ROOT / "data/wed/index_map.json").read_text())
    names = {int(key): str(value) for key, value in index_map.items()
             if int(key) > 0}
    baseline_manifest = json.loads((frozen_checkpoint.parent / "baseline_manifest.json").read_text())
    if _sha(frozen_checkpoint) != baseline_manifest["checkpoint_sha256"]:
        raise ValueError("Frozen checkpoint differs from its pinned SHA-256")
    images, truths = [], []
    data_paths: list[Path] = []
    for row in dev_rows:
        image_path, mask_path = wed_root / row["image"], wed_root / row["mask"]
        image, truth = cv2.imread(str(image_path)), cv2.imread(
            str(mask_path), cv2.IMREAD_GRAYSCALE)
        if image is None or truth is None:
            raise FileNotFoundError(row["image"])
        images.append(image)
        truths.append(truth)
        data_paths.extend((image_path, mask_path))

    model_specs: dict[str, tuple[Path | None, tuple[int, int], dict[str, Any]]] = {}
    model_specs["frozen_original"] = (
        None, (768, 1024), {"checkpoint": str(frozen_checkpoint),
                            "checkpoint_sha256": _sha(frozen_checkpoint)})
    run_by_seed_loss = {}
    for item in training["runs"]:
        seed, loss = int(item["training_seed"]), item["loss_kind"]
        key = f"seed_{seed}_{loss}"
        path = Path(item["checkpoint"])
        model_specs[key] = (path, (768, 1024), {
            "checkpoint": str(path),
            "checkpoint_sha256": _sha(path),
            "training_report_sha256": _sha(
                output / "candidates" / f"seed_{seed}" / loss / "training_report.json"),
            "training_seed": seed,
            "loss_kind": loss,
            "initialization_sha256": item["initialization_sha256"],
            "selected_epoch": item["training_budget"]["selected_epoch"],
            "peak_training_vram_mb": item["peak_training_vram_mb"],
        })
        run_by_seed_loss[(seed, loss)] = key

    results, all_predictions = {}, {}
    diagnostics_by_model = {}
    for model_name, (checkpoint_path, size, metadata) in model_specs.items():
        if device.type == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats(device)
        if checkpoint_path is None:
            model, _ = load_checkpoint(frozen_checkpoint, device=device)
            metadata["architecture"] = "frozen DeepLabV3"
            evaluated_checkpoint = frozen_checkpoint
        else:
            model, _ckpt, _ = _load_candidate(checkpoint_path, device=device)
            metadata["architecture"] = "DeepLabV3"
            evaluated_checkpoint = checkpoint_path
        metadata["parameter_count"] = sum(parameter.numel() for parameter in model.parameters())
        metadata["checkpoint_mb"] = evaluated_checkpoint.stat().st_size / (1024 ** 2)
        metadata["peak_inference_vram_mb"] = None
        predictions, per_view, confusions, tiny_diag = [], [], [], []
        _predict(model, images[0], size, device)
        _predict(model, images[0], size, device)
        for index, (image, truth, source_row) in enumerate(zip(images, truths, dev_rows)):
            prediction, latency, _ = _predict(model, image, size, device)
            predictions.append(prediction)
            cm = confusion_matrix(truth, prediction)
            confusions.append(cm)
            regions, _ = _class_errors(truth, prediction, *truth.shape)
            boundary = _boundary_counts(truth, prediction, radius=3)
            class_gt = set(map(int, np.unique(truth))) - {0}
            class_pred = set(map(int, np.unique(prediction))) - {0}
            tiny_diag.append(_component_diagnostics(truth, prediction))
            tiny = regions["size_bins"][SIZE_BINS[0]]
            per_view.append({
                "group": wed_group_id(source_row),
                "image": source_row["image"],
                "regions": regions,
                "boundary": list(boundary),
                "inference_ms": latency,
                "class_set_exact": class_gt == class_pred,
                "pixel_class_counts": [[
                    int(cm[cid, cid]), int(cm[:, cid].sum() - cm[cid, cid]),
                    int(cm[cid, :].sum() - cm[cid, cid]),
                ] for cid in range(N_CLASSES)],
                "foreground_counts": [int(cm[1:, 1:].sum()),
                                      int(cm[:, 1:].sum()),
                                      int(cm[1:, :].sum())],
                "tiny_pixel_recall": tiny["pixel_recall"],
                "tiny_region_recall_iou_0_5": tiny["region_recall_iou_0_5"],
            })
        if device.type == "cuda":
            metadata["peak_inference_vram_mb"] = round(
                torch.cuda.max_memory_allocated(device) / (1024 ** 2), 1)
        aggregate = _aggregate(metadata, per_view, confusions, names)
        aggregate["tiny_pixel_recall"] = aggregate["size_bins"][
            SIZE_BINS[0]]["pixel_recall"]
        aggregate["tiny_region_recall_iou_0_5"] = aggregate["size_bins"][
            SIZE_BINS[0]]["region_recall_iou_0_5"]
        aggregate.pop("per_view", None)
        metadata.update(aggregate)
        results[model_name] = metadata
        all_predictions[model_name] = predictions
        diagnostics_by_model[model_name] = {
            "per_view": per_view,
            "tiny_components": tiny_diag,
        }
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()
        print(f"evaluated {model_name}: 108/108 DEV views", flush=True)

    def rows_for(seed: int, loss: str) -> list[dict[str, Any]]:
        return diagnostics_by_model[run_by_seed_loss[(seed, loss)]] ["per_view"]

    def metric_point(model_name: str, metric: str) -> float:
        return float(results[model_name][metric])

    frozen_rows = diagnostics_by_model["frozen_original"]["per_view"]
    seed_summaries: dict[str, Any] = {}
    all_delta_names = ("macro_food_iou", "foreground_iou", "region_f1",
                       "boundary_f1_tolerance_3px", "tiny_pixel_recall",
                       "tiny_region_recall_iou_0_5",
                       "mean_merge_proxy_per_view",
                       "mean_fragmentation_proxy_per_view")
    for seed in SEEDS:
        standard = rows_for(seed, "standard")
        boundary = rows_for(seed, "boundary_aware")
        seed_summaries[str(seed)] = {
            "standard": {metric: results[run_by_seed_loss[(seed, "standard")]][metric]
                         for metric in all_delta_names},
            "boundary_aware": {metric: results[run_by_seed_loss[(seed, "boundary_aware")]][metric]
                               for metric in all_delta_names},
            "boundary_minus_standard": {
                metric: {"point": metric_point(
                    run_by_seed_loss[(seed, "boundary_aware")], metric)
                    - metric_point(run_by_seed_loss[(seed, "standard")], metric),
                    "ci95_group_bootstrap": _paired_bootstrap(boundary, standard, metric)}
                for metric in all_delta_names
            },
            "boundary_minus_frozen": {
                metric: {"point": metric_point(
                    run_by_seed_loss[(seed, "boundary_aware")], metric)
                    - metric_point("frozen_original", metric),
                    "ci95_group_bootstrap": _paired_bootstrap(boundary, frozen_rows, metric)}
                for metric in all_delta_names
            },
        }

    delta_reports = {}
    for comparison, reference_condition in (
            ("boundary_minus_standard", "standard"),
            ("boundary_minus_frozen", "frozen")):
        candidate_by_seed = {seed: rows_for(seed, "boundary_aware")
                             for seed in SEEDS}
        reference_by_seed = {
            seed: (rows_for(seed, "standard") if reference_condition == "standard"
                   else frozen_rows) for seed in SEEDS}
        delta_reports[comparison] = {}
        for metric in all_delta_names:
            boot = _multi_seed_group_bootstrap(candidate_by_seed,
                                               reference_by_seed, metric)
            per_seed_points = [seed_summaries[str(seed)][comparison][metric]["point"]
                               for seed in SEEDS]
            delta_reports[comparison][metric] = {
                **boot,
                "mean_across_seed_points": float(np.mean(per_seed_points)),
                "sd_across_seed_points": float(np.std(per_seed_points, ddof=1)),
                "per_seed_points": per_seed_points,
            }

    mean_per_class = {}
    for class_id in range(1, N_CLASSES):
        baseline = results["frozen_original"]["per_class_iou"][str(class_id)]
        standard_values, boundary_values = [], []
        for seed in SEEDS:
            standard_values.append(results[run_by_seed_loss[(seed, "standard")]][
                "per_class_iou"][str(class_id)]["iou"])
            boundary_values.append(results[run_by_seed_loss[(seed, "boundary_aware")]][
                "per_class_iou"][str(class_id)]["iou"])
        mean_per_class[str(class_id)] = {
            "class": baseline["class"],
            "dev_gt_pixels": baseline["ground_truth_pixels"],
            "frozen_iou": baseline["iou"] if baseline["ground_truth_pixels"] else None,
            "standard_seed_values": standard_values,
            "standard_mean_sd": _mean_sd(standard_values),
            "boundary_seed_values": boundary_values,
            "boundary_mean_sd": _mean_sd(boundary_values),
            "boundary_minus_standard_per_seed": [b - s for b, s in zip(
                boundary_values, standard_values)],
            "boundary_minus_standard_mean": float(np.mean(
                [b - s for b, s in zip(boundary_values, standard_values)])),
            "boundary_minus_frozen_mean": float(
                np.mean(boundary_values) - baseline["iou"]),
        }

    tiny_explanation = {}
    for loss in ("standard", "boundary_aware"):
        summaries = []
        for seed in SEEDS:
            key = run_by_seed_loss[(seed, loss)]
            model_diags = diagnostics_by_model[key]["tiny_components"]
            summaries.append({
                "seed": seed,
                "gt_tiny_components": sum(x["gt_tiny_components"] for x in model_diags),
                "no_overlap": sum(x["no_overlap_components"] for x in model_diags),
                "partial_overlap_below_0_5": sum(x["partial_overlap_below_0_5"] for x in model_diags),
                "matched_iou_ge_0_5": sum(x["matched_iou_ge_0_5"] for x in model_diags),
                "components_touched_by_multiple_predictions": sum(
                    x["gt_components_touched_by_multiple_pred_components"]
                    for x in model_diags),
                "mean_best_iou_all_tiny": float(np.mean([
                    x["mean_best_iou_all_tiny"] for x in model_diags
                    if x["mean_best_iou_all_tiny"] is not None])),
                "mean_best_pixel_coverage": float(np.mean([
                    x["mean_best_pixel_coverage"] for x in model_diags
                    if x["mean_best_pixel_coverage"] is not None])),
            })
        tiny_explanation[loss] = summaries

    priority_classes = {str(cid): data["class"]
                        for cid, data in mean_per_class.items()
                        if data["class"].casefold().replace("-", " ")
                        in {name.casefold().replace("-", " ") for name in PRIORITY_NAMES}}
    boundary_vs_control = delta_reports["boundary_minus_standard"]
    boundary_vs_frozen = delta_reports["boundary_minus_frozen"]

    def _gate(differences: dict[str, Any]) -> dict[str, bool]:
        macro, tiny_pixel, tiny_region = (differences[name]
            for name in ("macro_food_iou", "tiny_pixel_recall",
                         "tiny_region_recall_iou_0_5"))
        foreground = differences["foreground_iou"]["ci95"]
        region = differences["region_f1"]["ci95"]
        boundary = differences["boundary_f1_tolerance_3px"]
        merge_ci = differences["mean_merge_proxy_per_view"]["ci95"]
        fragment_ci = differences["mean_fragmentation_proxy_per_view"]["ci95"]
        small_gain = (
            tiny_pixel["point"] >= 0.05 and tiny_pixel["ci95"][0] > 0
            or tiny_region["point"] >= 0.05 and tiny_region["ci95"][0] > 0)
        priority_key = ("boundary_minus_standard_mean"
                        if differences is boundary_vs_control
                        else "boundary_minus_frozen_mean")
        priority_deltas = [data[priority_key]
                           for data in mean_per_class.values()
                           if data["class"].casefold().replace("-", " ")
                           in {x.casefold().replace("-", " ") for x in PRIORITY_NAMES}
                           and data["dev_gt_pixels"] > 0]
        ref_name = ("standard" if differences is boundary_vs_control else "frozen_original")
        candidate_latency = float(np.mean([
            results[run_by_seed_loss[(seed, "boundary_aware")]][
                "inference_latency_ms_batch1"]["mean"] for seed in SEEDS]))
        if ref_name == "standard":
            ref_latency = float(np.mean([
                results[run_by_seed_loss[(seed, "standard")]][
                    "inference_latency_ms_batch1"]["mean"] for seed in SEEDS]))
        else:
            ref_latency = results["frozen_original"][
                "inference_latency_ms_batch1"]["mean"]
        return {
            "macro_gain_at_least_0_01_with_ci_above_zero": (
                macro["point"] >= 0.01 and macro["ci95"][0] > 0),
            "tiny_pixel_or_component_gain_at_least_0_05_with_ci_above_zero": small_gain,
            "foreground_iou_lower_ci_above_minus_0_01": foreground[0] > -0.01,
            "region_f1_lower_ci_above_minus_0_01": region[0] > -0.01,
            "priority_class_iou_regression_no_worse_than_minus_0_05": (
                not priority_deltas or min(priority_deltas) >= -0.05),
            "merge_increase_upper_ci_at_most_0_25": merge_ci[1] <= 0.25,
            "fragmentation_increase_upper_ci_at_most_0_25": fragment_ci[1] <= 0.25,
            "boundary_f1_drop_no_more_than_0_01": boundary["point"] >= -0.01,
            "latency_no_more_than_2x_reference": candidate_latency / max(ref_latency, 1e-9) <= 2.0,
        }

    paired_gate = _gate(boundary_vs_control)
    frozen_gate = _gate(boundary_vs_frozen)
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "stage": "confirmatory_wed_boundary_loss_dev_evaluation",
        "created_at": datetime.now(UTC).isoformat(),
        "seeds": list(SEEDS),
        "epochs_per_run": 20,
        "dev_views": len(dev_rows),
        "dev_groups": len(dev_groups),
        "dev_group_sha256": hashlib.sha256(
            "\n".join(sorted(dev_groups)).encode()).hexdigest(),
        "dev_data_sha256": _sha_data(data_paths),
        "frozen_checkpoint_sha256": _sha(frozen_checkpoint),
        "training_summary_sha256": _sha(output / "training_report.json"),
        "metric_definitions": {
            "macro_food_iou": "global confusion-matrix IoU averaged over WED food classes present in the fixed DEV carve",
            "foreground_iou": "binary food-vs-background union IoU",
            "boundary_f1": "class-wise semantic-mask boundaries with a 3-pixel tolerance at original DEV resolution",
            "tiny_bin": "WED GT 8-connected per-class semantic components under 0.10% of image area",
            "component_recall": "same-class one-to-one Hungarian component match at IoU >= 0.5",
            "region_f1": "same-class one-to-one Hungarian component precision/recall/F1 at IoU >= 0.5",
            "bootstrap": "10,000 paired resamples of the same 21 physical meal groups; differences averaged across three trained seeds",
        },
        "per_model_metrics": results,
        "per_seed": seed_summaries,
        "boundary_minus_standard": boundary_vs_control,
        "boundary_minus_frozen_reference": boundary_vs_frozen,
        "per_class_iou": mean_per_class,
        "priority_classes": priority_classes,
        "tiny_component_overlap_diagnostics": tiny_explanation,
        "paired_control_gate": paired_gate,
        "frozen_reference_promotion_gate": frozen_gate,
        "promotion_recommendation": (
            "promote_candidate" if all(paired_gate.values()) and all(frozen_gate.values())
            else "retain_frozen_deeplabv3_and_close_boundary_loss_line"),
        "locked_accessed": False,
        "aruco_accessed": False,
        "wed_test_split_accessed": False,
        "synthetic_data_used": False,
        "geometry_or_weight_code_changed": False,
    }
    report_path = report_dir / "comparison_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_markdown(report, report_dir / "comparison_report.md")
    return report


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    def m_sd(value: dict[str, Any]) -> str:
        return f"{value['mean']:.4f} ± {value['sd_across_seeds']:.4f}"

    lines = [
        "# Confirmatory WED boundary-loss comparison", "",
        f"Fixed DEV: {report['dev_views']} views / {report['dev_groups']} meal groups. Seeds: {', '.join(map(str, report['seeds']))}; 20 epochs per run.",
        f"Frozen reference SHA-256: `{report['frozen_checkpoint_sha256']}`. LOCKED/ArUco/WED test/synthetic accessed: **No**.", "",
        "Both loss conditions use paired initialization, per-epoch sample order and augmentation seeds. Per-seed figures and pooled 21-group bootstrap intervals are in the JSON.", "",
        "## Per-seed metrics", "",
        "| Seed | Loss | Macro food IoU | Foreground IoU | Boundary F1 | Tiny pixel recall | Tiny component recall | Region F1 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for seed in report["seeds"]:
        for condition in ("standard", "boundary_aware"):
            v = report["per_seed"][str(seed)][condition]
            lines.append(f"| {seed} | {condition} | {v['macro_food_iou']:.4f} | {v['foreground_iou']:.4f} | {v['boundary_f1_tolerance_3px']:.4f} | {v['tiny_pixel_recall']:.4f} | {v['tiny_region_recall_iou_0_5']:.4f} | {v['region_f1']:.4f} |")
    lines.extend(["", "## Mean across seeds", "", "| Loss | Macro food IoU | Foreground IoU | Boundary F1 | Tiny pixel recall | Tiny component recall | Region F1 |",
                  "|---|---:|---:|---:|---:|---:|---:|"])
    for condition in ("standard", "boundary_aware"):
        keys = [f"seed_{seed}_{condition}" for seed in report["seeds"]]
        metric_rows = [report["per_model_metrics"][key] for key in keys]
        lines.append("| " + condition + " | " + " | ".join(
            m_sd(_mean_sd([row[metric] for row in metric_rows]))
            for metric in ("macro_food_iou", "foreground_iou",
                           "boundary_f1_tolerance_3px", "tiny_pixel_recall",
                           "tiny_region_recall_iou_0_5", "region_f1")) + " |")
    for comparison_key, title in (("boundary_minus_standard", "Boundary-aware minus matched standard loss"),
                                  ("boundary_minus_frozen_reference", "Boundary-aware minus frozen reference")):
        lines.extend(["", f"## {title}", "", "| Metric | Mean paired difference | 95% group-bootstrap CI | Across-seed SD |",
                      "|---|---:|---:|---:|"])
        for metric, data in report[comparison_key].items():
            ci = data["ci95"]
            lines.append(f"| {metric} | {data['point']:+.4f} | [{ci[0]:+.4f}, {ci[1]:+.4f}] | {data['sd_across_seed_points']:.4f} |")
    lines.extend(["", "## Per-class IoU", "", "Mean over the three seeds; absent DEV classes are `n/a`.", "",
                  "| ID | Class | Frozen | Standard mean ± SD | Boundary mean ± SD | Boundary − standard |",
                  "|---:|---|---:|---:|---:|---:|"])
    for class_id, values in report["per_class_iou"].items():
        if values["dev_gt_pixels"] == 0:
            continue
        lines.append(f"| {class_id} | {values['class']} | {values['frozen_iou']:.3f} | {m_sd(values['standard_mean_sd'])} | {m_sd(values['boundary_mean_sd'])} | {values['boundary_minus_standard_mean']:+.3f} |")
    lines.extend(["", "## Tiny-component overlap diagnosis", "",
                  "Buckets classify each tiny GT component by its best same-class predicted-component IoU. Partial overlap can raise pixel coverage while remaining below the complete-component IoU≥0.5 threshold.", ""])
    for condition, rows in report["tiny_component_overlap_diagnostics"].items():
        lines.append(f"### {condition}")
        lines.append("")
        lines.append("| Seed | Tiny GT | No overlap | Partial overlap <0.5 | Match ≥0.5 | Multi-pred overlaps | Mean best pixel coverage |")
        lines.append("|---:|---:|---:|---:|---:|---:|---:|")
        for row in rows:
            lines.append(f"| {row['seed']} | {row['gt_tiny_components']} | {row['no_overlap']} | {row['partial_overlap_below_0_5']} | {row['matched_iou_ge_0_5']} | {row['components_touched_by_multiple_predictions']} | {row['mean_best_pixel_coverage']:.3f} |")
        lines.append("")
    lines.extend(["## Promotion", "",
                  f"Matched-control gate: **{'PASS' if all(report['paired_control_gate'].values()) else 'FAIL'}**.",
                  f"Frozen-reference gate: **{'PASS' if all(report['frozen_reference_promotion_gate'].values()) else 'FAIL'}**.",
                  f"Recommendation: **{report['promotion_recommendation']}**.", "",
                  "All regions, merges, and fragments are connected components of semantic WED masks, not serving-level instance labels. If gates fail, retain the frozen checkpoint and close this loss line.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "experiments/wed_boundary_confirmatory")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--wed-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--baseline", type=Path,
                        default=ROOT / "experiments/wed_native_segmentation/model_wed_semantic_baseline.pt")
    parser.add_argument("--report-dir", type=Path,
                        default=ROOT / "experiments/wed_boundary_confirmatory/dev_report")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    report = evaluate(output=args.output, manifest=args.manifest,
                      wed_root=args.wed_root, frozen_checkpoint=args.baseline,
                      report_dir=args.report_dir, device_name=args.device)
    print(json.dumps({"recommendation": report["promotion_recommendation"],
                      "report": str(args.report_dir / "comparison_report.md")}, indent=2))


if __name__ == "__main__":
    main()
