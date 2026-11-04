"""Analyze WED semantic component errors on the fixed DEV carve only."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.wed_semantic_segmenter import load_checkpoint, predict_labels  # noqa: E402
from nutrisense_synth.parameters import (  # noqa: E402
    read_wed_train_manifest, wed_dev_group_ids, wed_group_id,
)
from nutrisense_synth.wed_segmentation import confusion_matrix, group_bootstrap_ci  # noqa: E402

SIZE_BINS = (("tiny_lt_0.10pct", 0.0, 0.001),
             ("small_0.10_to_0.25pct", 0.001, 0.0025),
             ("medium_0.25_to_0.50pct", 0.0025, 0.005),
             ("large_ge_0.50pct", 0.005, float("inf")))


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _format_optional(value: Any) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def _components(mask: np.ndarray) -> list[dict[str, Any]]:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), connectivity=8)
    result = []
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        if area:
            result.append({"mask": labels == index, "area": area})
    return result


def _class_errors(truth: np.ndarray, prediction: np.ndarray,
                  height: int, width: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    size_data = {name: {"gt_regions": 0, "missed_no_overlap": 0,
                        "matched_iou_at_0_5": 0, "gt_pixels": 0,
                        "recalled_pixels": 0, "fragmented_gt_regions": 0}
                 for name, _low, _high in SIZE_BINS}
    total_gt = total_pred = matched = missed = fragmented = merged = 0
    unmatched_pred_duplicate = unmatched_pred_spurious = 0
    per_class: dict[int, dict[str, int]] = defaultdict(lambda: {
        "gt_regions": 0, "pred_regions": 0, "missed": 0,
        "fragmented": 0, "merged_pred_regions": 0, "iou_matched": 0,
    })
    class_ids = sorted(set(map(int, np.unique(truth)))
                       | set(map(int, np.unique(prediction))) - {0})
    class_ids = [class_id for class_id in class_ids if class_id > 0]
    for class_id in class_ids:
        gt_regions = _components(truth == class_id)
        pred_regions = _components(prediction == class_id)
        total_gt += len(gt_regions)
        total_pred += len(pred_regions)
        per_class[class_id]["gt_regions"] += len(gt_regions)
        per_class[class_id]["pred_regions"] += len(pred_regions)
        if not gt_regions:
            unmatched_pred_spurious += len(pred_regions)
            continue
        intersections = np.zeros((len(gt_regions), len(pred_regions)), dtype=np.int64)
        ious = np.zeros_like(intersections, dtype=np.float64)
        for gi, gt in enumerate(gt_regions):
            area_frac = gt["area"] / float(height * width)
            bin_name = next(name for name, low, high in SIZE_BINS
                            if low <= area_frac < high)
            record = size_data[bin_name]
            record["gt_regions"] += 1
            record["gt_pixels"] += gt["area"]
            per_class[class_id]["gt_regions"] += 0
            for pi, pred in enumerate(pred_regions):
                inter = int(np.count_nonzero(gt["mask"] & pred["mask"]))
                intersections[gi, pi] = inter
                union = gt["area"] + pred["area"] - inter
                ious[gi, pi] = inter / union if union else 0.0
            overlaps = np.flatnonzero(intersections[gi] > 0)
            best_recall = (float(intersections[gi, overlaps].max()) / gt["area"]
                           if len(overlaps) else 0.0)
            record["recalled_pixels"] += int(round(best_recall * gt["area"]))
            if len(overlaps) == 0:
                record["missed_no_overlap"] += 1
                missed += 1
                per_class[class_id]["missed"] += 1
            if len(overlaps) >= 2:
                record["fragmented_gt_regions"] += 1
                fragmented += 1
                per_class[class_id]["fragmented"] += 1
        if ious.size:
            from scipy.optimize import linear_sum_assignment
            gi, pi = linear_sum_assignment(-ious)
            matched_pairs = [(int(a), int(b)) for a, b in zip(gi, pi)
                             if ious[a, b] >= 0.5]
        else:
            matched_pairs = []
        matched_gt = {gi for gi, _ in matched_pairs}
        matched_pred = {pi for _, pi in matched_pairs}
        matched += len(matched_pairs)
        per_class[class_id]["iou_matched"] += len(matched_pairs)
        for gi, _ in matched_pairs:
            area_frac = gt_regions[gi]["area"] / float(height * width)
            bin_name = next(name for name, low, high in SIZE_BINS
                            if low <= area_frac < high)
            size_data[bin_name]["matched_iou_at_0_5"] += 1
        for pi, pred in enumerate(pred_regions):
            overlaps_gt = int(np.count_nonzero(intersections[:, pi]))
            if overlaps_gt >= 2:
                merged += 1
                per_class[class_id]["merged_pred_regions"] += 1
            if pi not in matched_pred:
                if overlaps_gt:
                    unmatched_pred_duplicate += 1
                else:
                    unmatched_pred_spurious += 1

    for values in size_data.values():
        regions = values["gt_regions"]
        values["region_recall_iou_0_5"] = (
            values["matched_iou_at_0_5"] / regions if regions else None)
        values["no_overlap_miss_rate"] = (
            values["missed_no_overlap"] / regions if regions else None)
        values["pixel_recall"] = (
            values["recalled_pixels"] / values["gt_pixels"]
            if values["gt_pixels"] else None)
    result = {
        "ground_truth_semantic_regions": total_gt,
        "predicted_semantic_regions": total_pred,
        "one_to_one_iou_matched_regions": matched,
        "missed_regions_with_zero_same_class_overlap": missed,
        "fragmented_gt_regions_overlapping_multiple_predicted_components": fragmented,
        "predicted_components_overlapping_multiple_gt_components_same_class": merged,
        "unmatched_prediction_overlapping_a_gt_region": unmatched_pred_duplicate,
        "unmatched_prediction_with_no_gt_overlap": unmatched_pred_spurious,
        "size_bins": size_data,
        "per_class": {str(k): v for k, v in sorted(per_class.items())},
    }
    return result, []


def _palette() -> np.ndarray:
    palette = np.zeros((42, 3), dtype=np.uint8)
    for class_id in range(1, 42):
        palette[class_id] = np.asarray(
            plt.get_cmap("hsv")((class_id * 0.61803398875) % 1.0)[:3]) * 255
    return palette


def _visual(image: np.ndarray, truth: np.ndarray, prediction: np.ndarray,
            row: dict[str, Any], names: dict[int, str], palette: np.ndarray,
            target: Path) -> None:
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    gt_overlay, pred_overlay = rgb.copy(), rgb.copy()
    for output, labels in ((gt_overlay, truth), (pred_overlay, prediction)):
        foreground = labels > 0
        output[foreground] = (0.48 * output[foreground].astype(np.float32)
                              + 0.52 * palette[labels[foreground]]).astype(np.uint8)
    errors = np.zeros((*truth.shape, 3), dtype=np.uint8)
    correct = (truth == prediction) & (truth > 0)
    missed = (truth > 0) & (prediction == 0)
    false_food = (truth == 0) & (prediction > 0)
    class_confusion = (truth > 0) & (prediction > 0) & (truth != prediction)
    errors[correct] = (0, 220, 70)
    errors[missed] = (235, 35, 35)
    errors[false_food] = (30, 95, 255)
    errors[class_confusion] = (245, 205, 25)
    error_overlay = rgb.copy()
    changed = errors.any(axis=2)
    error_overlay[changed] = (
        0.30 * rgb[changed].astype(np.float32)
        + 0.70 * errors[changed].astype(np.float32)).astype(np.uint8)

    fig, axes = plt.subplots(1, 4, figsize=(18, 6), constrained_layout=False)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.88, bottom=0.23, wspace=0.025)
    for axis, panel, title in zip(
            axes, (rgb, gt_overlay, pred_overlay, error_overlay),
            ("Original DEV thali", "WED ground truth", "DeepLabV3 prediction",
             "Pixel errors")):
        axis.imshow(panel)
        axis.set_title(title, fontsize=10)
        axis.axis("off")
    true_classes = sorted(set(map(int, np.unique(truth))) - {0})
    handles = [Patch(facecolor=palette[c] / 255.0, label=f"{c}: {names[c]}")
               for c in true_classes]
    fig.legend(handles=handles, loc="lower center", ncol=6,
               fontsize=8, bbox_to_anchor=(0.5, 0.06), frameon=False)
    fig.suptitle(f"{row['image']} — {len(true_classes)} annotated food classes",
                 fontsize=9, y=0.98)
    fig.text(0.5, 0.015,
             "Error colors: green correct, red missed food, blue false food, yellow wrong food class",
             ha="center", fontsize=8)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, dpi=140, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def analyze(*, manifest: Path, wed_root: Path, checkpoint: Path,
            baseline_report: Path, out_dir: Path,
            device_name: str = "cuda") -> dict[str, Any]:
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; use the approved GPU runtime")
    device = torch.device(device_name)
    rows = read_wed_train_manifest(manifest)
    dev_groups = wed_dev_group_ids(rows)
    dev_rows = [row for row in rows if wed_group_id(row) in dev_groups]
    if len(dev_rows) != 108:
        raise ValueError(f"Expected fixed 108-view DEV carve, got {len(dev_rows)}")
    model, checkpoint_data = load_checkpoint(checkpoint, device=device)
    index_map = json.loads((ROOT / "data/wed/index_map.json").read_text())
    names = {int(k): v for k, v in index_map.items() if int(k) > 0}
    palette = _palette()
    per_view = []
    all_confusions = []
    cached_visuals: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    for index, row in enumerate(dev_rows):
        image_path, mask_path = wed_root / row["image"], wed_root / row["mask"]
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        truth = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if image is None or truth is None:
            raise FileNotFoundError(f"Cannot decode DEV input {row['image']}")
        prediction = predict_labels(model, image, device)
        if prediction.shape != truth.shape:
            prediction = cv2.resize(prediction, (truth.shape[1], truth.shape[0]),
                                    interpolation=cv2.INTER_NEAREST)
        h, w = truth.shape
        component_result, _ = _class_errors(truth, prediction, h, w)
        gt_classes = set(map(int, np.unique(truth))) - {0}
        confusion = confusion_matrix(truth, prediction)
        all_confusions.append(confusion)
        row_result = {
            "group": wed_group_id(row),
            "image": row["image"],
            "ground_truth_class_count": len(gt_classes),
            "ground_truth_classes": [names[c] for c in sorted(gt_classes)],
            "class_set_exact": (gt_classes == (set(map(int, np.unique(prediction))) - {0})),
            "component_errors": component_result,
            "same_class_pixel_recall": float(
                np.trace(confusion[1:, 1:]) / max(1, confusion[1:, :].sum())),
            "class_confusion_pixels": int(confusion[1:, 1:].sum()
                                           - np.trace(confusion[1:, 1:])),
        }
        per_view.append(row_result)
        cached_visuals[index] = (image, truth, prediction)
        if (index + 1) % 20 == 0 or index + 1 == len(dev_rows):
            print(f"semantic error analysis: {index + 1}/{len(dev_rows)} DEV views",
                  flush=True)

    totals = Counter()
    size_totals = {name: Counter() for name, _, _ in SIZE_BINS}
    per_class_totals: dict[str, Counter] = defaultdict(Counter)
    for row in per_view:
        comp = row["component_errors"]
        for key in ("ground_truth_semantic_regions", "predicted_semantic_regions",
                    "one_to_one_iou_matched_regions",
                    "missed_regions_with_zero_same_class_overlap",
                    "fragmented_gt_regions_overlapping_multiple_predicted_components",
                    "predicted_components_overlapping_multiple_gt_components_same_class",
                    "unmatched_prediction_overlapping_a_gt_region",
                    "unmatched_prediction_with_no_gt_overlap"):
            totals[key] += comp[key]
        for size_name, values in comp["size_bins"].items():
            for key in ("gt_regions", "missed_no_overlap", "matched_iou_at_0_5",
                        "gt_pixels", "recalled_pixels", "fragmented_gt_regions"):
                size_totals[size_name][key] += values[key]
        for class_id, values in comp["per_class"].items():
            per_class_totals[class_id].update(values)

    for size_name, values in size_totals.items():
        n = values["gt_regions"]
        values["region_recall_iou_0_5"] = values["matched_iou_at_0_5"] / n if n else None
        values["no_overlap_miss_rate"] = values["missed_no_overlap"] / n if n else None
        values["pixel_recall"] = (values["recalled_pixels"] / values["gt_pixels"]
                                   if values["gt_pixels"] else None)
    all_cm = np.sum(all_confusions, axis=0)
    class_reports = {}
    for raw_id, counts in sorted(per_class_totals.items(), key=lambda kv: int(kv[0])):
        class_id = int(raw_id)
        tp = int(all_cm[class_id, class_id])
        fn = int(all_cm[class_id, :].sum() - tp)
        fp = int(all_cm[:, class_id].sum() - tp)
        class_reports[raw_id] = {
            "class": names[class_id], **counts,
            "pixel_precision": tp / max(1, tp + fp),
            "pixel_recall": tp / max(1, tp + fn),
            "pixel_iou": tp / max(1, tp + fp + fn),
        }
    summary_rows = [{"group": row["group"],
                     "missed": row["component_errors"][
                         "missed_regions_with_zero_same_class_overlap"],
                     "fragmented": row["component_errors"][
                         "fragmented_gt_regions_overlapping_multiple_predicted_components"],
                     "merged": row["component_errors"][
                         "predicted_components_overlapping_multiple_gt_components_same_class"]}
                    for row in per_view]
    bootstrap = {metric: group_bootstrap_ci(summary_rows, metric)
                 for metric in ("missed", "fragmented", "merged")}

    selected: list[tuple[int, str]] = []
    used_groups: set[str] = set()

    def select_case(focus: str, score) -> None:
        candidates = [i for i, row in enumerate(per_view)
                      if row["ground_truth_class_count"] >= 10
                      and row["group"] not in used_groups]
        if not candidates:
            return
        selected_index = max(candidates, key=lambda i: (
            score(per_view[i]), per_view[i]["ground_truth_class_count"], -i))
        selected.append((selected_index, focus))
        used_groups.add(per_view[selected_index]["group"])

    select_case("small_item_misses", lambda row: row["component_errors"][
        "size_bins"]["tiny_lt_0.10pct"]["missed_no_overlap"])
    select_case("fragmentation", lambda row: row["component_errors"][
        "fragmented_gt_regions_overlapping_multiple_predicted_components"])
    select_case("merge_proxy", lambda row: row["component_errors"][
        "predicted_components_overlapping_multiple_gt_components_same_class"])
    visual_paths = []
    visual_cases = []
    for number, (index, focus) in enumerate(selected, 1):
        image, truth, prediction = cached_visuals[index]
        path = out_dir / "visuals" / f"{focus}_{number}_{Path(per_view[index]['image']).stem}.png"
        _visual(image, truth, prediction, per_view[index], names, palette, path)
        visual_paths.append(path.relative_to(out_dir).as_posix())
        visual_cases.append({"focus": focus, "view_index": index,
                             "image": per_view[index]["image"],
                             "group": per_view[index]["group"]})

    report = {
        "stage": "wed_semantic_error_analysis",
        "created_at": datetime.now(UTC).isoformat(),
        "tier": "dev",
        "split": "fixed seed-42 10% physical-group carve from WED TRAIN",
        "locked_accessed": False,
        "aruco_accessed": False,
        "test_split_accessed": False,
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": _sha(checkpoint),
        "baseline_report": str(baseline_report),
        "baseline_report_sha256": _sha(baseline_report),
        "dev_data_sha256": json.loads(baseline_report.read_text())["data_sha256"],
        "analysis_script_sha256": _sha(Path(__file__).resolve()),
        "architecture": checkpoint_data["architecture"],
        "n_views": len(per_view),
        "n_groups": len(dev_groups),
        "dev_groups_sha256": hashlib.sha256(
            "\n".join(sorted(dev_groups)).encode()).hexdigest(),
        "connected_component_definition": (
            "8-connected components within each semantic class; region matching "
            "is same-class one-to-one IoU>=0.5"),
        "area_bin_definition": (
            "ground-truth semantic component pixel area divided by image pixels"),
        "summary": {
            **dict(totals),
            "same_class_region_iou_recall": (
                totals["one_to_one_iou_matched_regions"]
                / max(1, totals["ground_truth_semantic_regions"])),
            "class_set_exact_meals": int(sum(row["class_set_exact"] for row in per_view)),
            "class_set_exact_rate": float(np.mean(
                [row["class_set_exact"] for row in per_view])),
            "per_class": class_reports,
            "size_bins": {k: dict(v) for k, v in size_totals.items()},
            "group_bootstrap_95ci_mean_per_view_error_counts": bootstrap,
            "interpretation": (
                "Merges, fragments, and misses are measured against semantic "
                "connected regions only. They cannot identify touching or "
                "overlapping same-class physical servings that WED did not label separately."),
        },
        "visuals": visual_paths,
        "visual_cases": visual_cases,
        "per_view": per_view,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "error_analysis.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_markdown(report, out_dir / "error_analysis.md")
    return report


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# WED semantic segmentation error analysis", "",
        f"Checkpoint SHA-256: `{report['checkpoint_sha256']}`", "",
        f"DEV scope: {report['n_views']} views from {report['n_groups']} physical groups. LOCKED / ArUco / WED test accessed: `{report['locked_accessed']}` / `{report['aruco_accessed']}` / `{report['test_split_accessed']}`.", "",
        "## Error types against semantic connected-region proxies", "",
        "| Measure | Count | Interpretation |", "|---|---:|---|",
        f"| WED GT semantic regions | {summary['ground_truth_semantic_regions']} | 8-connected components per class |",
        f"| Predicted semantic regions | {summary['predicted_semantic_regions']} | 8-connected components per predicted class |",
        f"| One-to-one matches at IoU ≥ 0.5 | {summary['one_to_one_iou_matched_regions']} | class-consistent |",
        f"| GT components with no same-class overlap | {summary['missed_regions_with_zero_same_class_overlap']} | fully disappeared at component level |",
        f"| GT components touched by multiple predicted components | {summary['fragmented_gt_regions_overlapping_multiple_predicted_components']} | fragmentation proxy |",
        f"| Predicted components overlapping multiple GT components of the same class | {summary['predicted_components_overlapping_multiple_gt_components_same_class']} | merge proxy |",
        f"| Unmatched predictions overlapping a GT component | {summary['unmatched_prediction_overlapping_a_gt_region']} | duplicate/fragment candidates |",
        f"| Unmatched predictions with no GT overlap | {summary['unmatched_prediction_with_no_gt_overlap']} | spurious components |",
        f"| Same-class region recall at IoU ≥ 0.5 | {summary['same_class_region_iou_recall']:.4f} | component matching recall |",
        f"| Exact class-set meals | {summary['class_set_exact_meals']}/{report['n_views']} ({summary['class_set_exact_rate']:.1%}) | all WED classes present in the image predicted, with no extra classes |",
        "", "## Small-item and region-size analysis", "",
        "Area bins use each WED ground-truth component's share of the full image.", "",
        "| GT component area | GT regions | No-overlap misses | IoU≥0.5 recall | Pixel recall | Fragmented GT regions |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, _low, _high in SIZE_BINS:
        v = summary["size_bins"][name]
        lines.append(
            f"| {name} | {v['gt_regions']} | {v['missed_no_overlap']} | "
            f"{_format_optional(v.get('region_recall_iou_0_5'))} | "
            f"{_format_optional(v.get('pixel_recall'))} | "
            f"{v['fragmented_gt_regions']} |")
    lines.extend(["", "## Per-class pixel and component errors", "",
                  "| Class | Pixel precision | Pixel recall | Pixel IoU | GT regions | Predicted regions | Missed | Fragmented | Merged |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|"])
    for item in summary["per_class"].values():
        lines.append(
            f"| {item['class']} | {item['pixel_precision']:.3f} | "
            f"{item['pixel_recall']:.3f} | {item['pixel_iou']:.3f} | "
            f"{item['gt_regions']} | {item['pred_regions']} | {item['missed']} | "
            f"{item['fragmented']} | {item['merged_pred_regions']} |")
    lines.extend(["", "## Representative DEV error views", ""])
    for case, relative in zip(report["visual_cases"], report["visuals"]):
        lines.extend([f"### {case['focus'].replace('_', ' ').title()}", "",
                      f"![Ground truth, prediction, and pixel errors]({relative})", ""])
    lines.extend([
        "## Connected-component limitations", "",
        "WED contains semantic class rasters, not per-serving IDs. Connected components split same-class pixels that are disconnected in the raster and merge same-class pixels that touch. They can also split one serving because of annotation gaps or prediction holes. A predicted region overlapping multiple GT components is therefore a merge only relative to the connected-component proxy. It cannot prove that multiple physical servings merged, nor can the absence of multiple GT components prove distinct servings were recovered. The same restriction applies to fragmentation and complete-region counts.", "",
        "Small-item disappearance is assessed by GT pixel-area bins and whether any same-class prediction overlaps the component. A component can be absent from the predicted mask even when its class appears elsewhere in the meal; class-set accuracy does not imply every serving was localized.", "",
        "No synthetic data, LOCKED images, ArUco images, depth model, or geometry/weight pipeline was used or changed.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--wed-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--checkpoint", type=Path,
                        default=ROOT / "experiments/wed_native_segmentation/model_best.pt")
    parser.add_argument("--baseline-report", type=Path,
                        default=ROOT / "experiments/wed_native_segmentation/dev_report.json")
    parser.add_argument("--out-dir", type=Path,
                        default=ROOT / "experiments/wed_native_segmentation")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    report = analyze(manifest=args.manifest, wed_root=args.wed_root,
                     checkpoint=args.checkpoint, baseline_report=args.baseline_report,
                     out_dir=args.out_dir, device_name=args.device)
    print(json.dumps({
        "views": report["n_views"],
        "merges": report["summary"][
            "predicted_components_overlapping_multiple_gt_components_same_class"],
        "fragments": report["summary"][
            "fragmented_gt_regions_overlapping_multiple_predicted_components"],
        "small_bins": report["summary"]["size_bins"],
        "report": str(args.out_dir / "error_analysis.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
