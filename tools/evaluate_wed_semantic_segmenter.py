"""Evaluate WED semantic segmentation and the prior SAM2 candidate on DEV."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
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

from models.wed_semantic_segmenter import (  # noqa: E402
    IMAGE_MEAN, IMAGE_STD, load_checkpoint, predict_labels,
)
from models.model_revisions import SAM2_REVISION  # noqa: E402
from nutrisense_synth.parameters import (  # noqa: E402
    read_wed_train_manifest, wed_dev_group_ids, wed_group_id,
)
from nutrisense_synth.wed_segmentation import (  # noqa: E402
    N_CLASSES, class_metrics, class_set_metrics, confusion_matrix,
    connected_regions, group_bootstrap_ci, region_counts,
)


def _sha(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        digest.update(str(path).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _binary_union(masks: list[np.ndarray], shape: tuple[int, int]) -> np.ndarray:
    union = np.zeros(shape, dtype=bool)
    for mask in masks:
        candidate = np.asarray(mask, dtype=bool)
        if candidate.shape != shape:
            candidate = cv2.resize(candidate.astype(np.uint8),
                                   (shape[1], shape[0]),
                                   interpolation=cv2.INTER_NEAREST).astype(bool)
        union |= candidate
    return union


def _union_metrics(truth: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    intersection = int(np.count_nonzero(truth & prediction))
    union = int(np.count_nonzero(truth | prediction))
    denom = int(truth.sum() + prediction.sum())
    return {
        "foreground_union_iou": intersection / union if union else 1.0,
        "foreground_union_dice": 2 * intersection / denom if denom else 1.0,
        "foreground_pixel_precision": intersection / max(1, int(prediction.sum())),
        "foreground_pixel_recall": intersection / max(1, int(truth.sum())),
    }


def _aggregate_regions(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    sums = {field: 0 for field in (
        "ground_truth_regions", "predicted_regions", "true_positive_regions",
        "false_positive_regions", "false_negative_regions",
        "duplicate_overlapping_predictions", "spurious_nonoverlapping_predictions",
        "predictions_merging_multiple_gt_regions", "missed_semantic_regions")}
    for row in rows:
        for field in sums:
            sums[field] += int(row[key][field])
    tp = sums["true_positive_regions"]
    precision = tp / max(1, tp + sums["false_positive_regions"])
    recall = tp / max(1, tp + sums["false_negative_regions"])
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    group_rows = [{"group": row["group"],
                   **{metric: row[key][metric]
                      for metric in ("precision", "recall", "f1")}}
                  for row in rows]
    result = {
        **sums, "precision": precision, "recall": recall, "f1": f1,
        "complete_region_recovery_views": int(sum(
            bool(row[key]["complete_region_recovery"]) for row in rows)),
        "complete_region_recovery_rate": float(np.mean(
            [row[key]["complete_region_recovery"] for row in rows])),
        "group_bootstrap_95ci": {
            metric: group_bootstrap_ci(group_rows, metric)
            for metric in ("precision", "recall", "f1")
        },
    }
    return result


def _rows_for_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened = []
    for row in rows:
        item = {k: v for k, v in row.items() if k not in ("model_regions", "sam_regions")}
        for method in ("model_regions", "sam_regions"):
            for metric in ("precision", "recall", "f1"):
                item[f"{method}_{metric}"] = row[method][metric]
        flattened.append(item)
    return flattened


def _summarize(rows: list[dict[str, Any]], confusions: list[np.ndarray],
               class_names: dict[int, str]) -> dict[str, Any]:
    summary_rows = _rows_for_summary(rows)
    pixel = class_metrics(confusions, class_names)
    pixel["macro_food_iou_definition"] = (
        "mean over food classes present in DEV; classes with zero DEV "
        "ground-truth pixels are excluded")
    pixel["per_class_iou_interval_definition"] = (
        "95% percentile bootstrap over the mean of per-view IoU within each "
        "resampled physical meal group")
    pixel["group_bootstrap_95ci"] = {
        metric: group_bootstrap_ci(summary_rows, metric)
        for metric in ("foreground_union_iou", "foreground_union_dice",
                       "foreground_pixel_precision", "foreground_pixel_recall")
    }
    for class_id in range(1, N_CLASSES):
        item = pixel["per_class"][str(class_id)]
        class_views = [row for row, cm in zip(rows, confusions)
                       if cm[class_id, :].sum() > 0]
        per_view = []
        for row, cm in zip(rows, confusions):
            tp = int(cm[class_id, class_id])
            fp = int(cm[:, class_id].sum() - tp)
            fn = int(cm[class_id, :].sum() - tp)
            denom = tp + fp + fn
            if cm[class_id, :].sum() > 0:
                per_view.append({"group": row["group"], "iou": tp / denom if denom else 0.0})
        item["iou_group_bootstrap_95ci"] = group_bootstrap_ci(per_view, "iou")
        item["dev_views_present"] = len(class_views)
    pixel["per_class"] = pixel.pop("per_class")
    model_regions = _aggregate_regions(rows, "model_regions")
    sam_regions = _aggregate_regions(rows, "sam_regions")
    model_regions["class_set_exact_rate"] = float(np.mean(
        [row["class_set"]["class_set_exact"] for row in rows]))
    model_regions["class_set_exact_views"] = int(sum(
        row["class_set"]["class_set_exact"] for row in rows))
    model_regions["missed_classes_by_id"] = {
        str(class_id): int(sum(class_id in row["class_set"]["missed_class_ids"]
                               for row in rows))
        for class_id in range(1, N_CLASSES)
    }
    return {
        "n_views": len(rows),
        "n_groups": len({row["group"] for row in rows}),
        "pixel": pixel,
        "semantic_regions_class_aware": model_regions,
        "regions_class_agnostic_comparison": {
            "definition": (
                "same 8-connected per-class semantic regions used as ground "
                "truth; predictions compared class-agnostically by one-to-one "
                "IoU>=0.5 matching"),
            "wed_semantic_model": _aggregate_regions(rows, "model_regions_agnostic"),
            "sam2_dense_grid_candidate": sam_regions,
        },
        "sam2_note": (
            "SAM2 proposals have no class IDs. Pixel per-class metrics and exact "
            "class-set accuracy are not defined for SAM2; region matching is "
            "class-agnostic for both methods on the same views."),
    }


def _palette(class_names: dict[int, str]) -> np.ndarray:
    colors = np.zeros((N_CLASSES, 3), dtype=np.uint8)
    for class_id in range(1, N_CLASSES):
        hue = (class_id * 0.61803398875) % 1.0
        rgb = plt.get_cmap("hsv")(hue)[:3]
        colors[class_id] = np.asarray(rgb) * 255
    colors[0] = (0, 0, 0)
    return colors


def _overlay(image_rgb: np.ndarray, labels: np.ndarray,
             palette: np.ndarray, alpha: float = 0.48) -> np.ndarray:
    color = palette[labels]
    foreground = labels > 0
    output = image_rgb.copy()
    output[foreground] = (
        (1 - alpha) * output[foreground].astype(np.float32)
        + alpha * color[foreground].astype(np.float32)
    ).astype(np.uint8)
    return output


def _save_visual(image_bgr: np.ndarray, truth: np.ndarray,
                 prediction: np.ndarray, sam_masks: list[np.ndarray],
                 row: dict[str, Any], class_names: dict[int, str],
                 palette: np.ndarray, out_path: Path) -> None:
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    sam_union = _binary_union(sam_masks, truth.shape)
    sam_visual = image_rgb.copy()
    for index, mask in enumerate(sam_masks):
        m = np.asarray(mask, dtype=bool)
        if m.shape != truth.shape:
            m = cv2.resize(m.astype(np.uint8), (truth.shape[1], truth.shape[0]),
                           interpolation=cv2.INTER_NEAREST).astype(bool)
        contours, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        color = tuple(int(x) for x in palette[(index % 41) + 1])
        cv2.drawContours(sam_visual, contours, -1, color, 3)
    fig, axes = plt.subplots(1, 4, figsize=(18, 6), constrained_layout=True)
    axes[0].imshow(image_rgb)
    axes[0].set_title("Original")
    axes[1].imshow(_overlay(image_rgb, truth, palette))
    axes[1].set_title("WED semantic ground truth")
    axes[2].imshow(_overlay(image_rgb, prediction, palette))
    axes[2].set_title("WED-native model")
    axes[3].imshow(sam_visual)
    axes[3].set_title(f"SAM2 proposals ({len(sam_masks)}; unlabelled)")
    for axis in axes:
        axis.axis("off")
    classes = sorted(set(map(int, np.unique(truth))) - {0})
    caption = ", ".join(class_names[cid] for cid in classes)
    fig.suptitle(f"{row['image']} — WED classes: {caption}", fontsize=9)
    from matplotlib.patches import Patch
    handles = [Patch(facecolor=palette[cid] / 255.0,
                     label=f"{cid}: {class_names[cid]}")
               for cid in classes]
    fig.legend(handles=handles, loc="lower center", ncol=6, fontsize=8,
               bbox_to_anchor=(0.5, -0.015), frameon=False)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def _representatives(rows: list[dict[str, Any]], wed_root: Path) -> list[int]:
    counts = []
    for row in rows:
        labels = cv2.imread(str(wed_root / row["mask"]), cv2.IMREAD_GRAYSCALE)
        if labels is None:
            raise FileNotFoundError(row["mask"])
        counts.append(len(set(map(int, np.unique(labels))) - {0}))
    targets = [float(np.quantile(counts, q)) for q in (0.15, 0.50, 0.85)]
    chosen: list[int] = []
    used_groups: set[str] = set()
    for target in targets:
        candidates = sorted(range(len(rows)),
                            key=lambda i: (abs(counts[i] - target), i))
        selected = next((i for i in candidates
                         if wed_group_id(rows[i]) not in used_groups), None)
        if selected is not None:
            chosen.append(selected)
            used_groups.add(wed_group_id(rows[selected]))
    return chosen


def evaluate(*, manifest: Path, wed_root: Path, checkpoint_path: Path,
             out_dir: Path, device_name: str = "cuda") -> dict[str, Any]:
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; run evaluation on the approved GPU runtime")
    device = torch.device(device_name)
    manifest_rows = read_wed_train_manifest(manifest)
    dev_groups = wed_dev_group_ids(manifest_rows)
    dev_rows = [row for row in manifest_rows if wed_group_id(row) in dev_groups]
    if len(dev_rows) != 108:
        raise ValueError(f"Expected fixed 108-view DEV carve, got {len(dev_rows)}")
    model, checkpoint = load_checkpoint(checkpoint_path, device=device)
    from models.dish_segmenter import segment_items

    index_map = json.loads((ROOT / "data/wed/index_map.json").read_text())
    class_names = {int(key): value for key, value in index_map.items() if int(key) > 0}
    palette = _palette(class_names)
    rows: list[dict[str, Any]] = []
    confusions: list[np.ndarray] = []
    input_files: list[Path] = []
    representative_indices = set(_representatives(dev_rows, wed_root))
    visual_dir = out_dir / "visuals"
    visual_paths: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for index, row in enumerate(dev_rows, start=1):
        image_path, mask_path = wed_root / row["image"], wed_root / row["mask"]
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        truth = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if image is None or truth is None:
            raise FileNotFoundError(f"Cannot decode WED DEV pair: {row['image']}")
        prediction = predict_labels(model, image, device)
        if prediction.shape != truth.shape:
            prediction = cv2.resize(prediction, (truth.shape[1], truth.shape[0]),
                                    interpolation=cv2.INTER_NEAREST)
        cm = confusion_matrix(truth, prediction)
        confusions.append(cm)

        model_class_regions = connected_regions(prediction, class_aware=True)
        model_agnostic_regions = connected_regions(prediction, class_aware=False)
        sam_report = segment_items(image)
        sam_masks = [np.asarray(item["mask"], dtype=bool)
                     for item in sam_report["items"]]
        sam_regions = [{"mask": mask, "class_id": None,
                        "area": int(mask.sum())} for mask in sam_masks]
        model_region_metrics = region_counts(
            truth, model_class_regions, class_aware=True)
        model_agnostic_metrics = region_counts(
            truth, model_agnostic_regions, class_aware=False)
        sam_region_metrics = region_counts(
            truth, sam_regions, class_aware=False)
        true_food_classes = set(map(int, np.unique(truth))) - {0}
        row_metrics = {
            "group": wed_group_id(row),
            "image": row["image"],
            "ground_truth_class_count": len(true_food_classes),
            "ground_truth_classes": sorted(class_names[c] for c in true_food_classes),
            "foreground_union_iou": _union_metrics(truth > 0, prediction > 0)["foreground_union_iou"],
            "foreground_union_dice": _union_metrics(truth > 0, prediction > 0)["foreground_union_dice"],
            "foreground_pixel_precision": _union_metrics(truth > 0, prediction > 0)["foreground_pixel_precision"],
            "foreground_pixel_recall": _union_metrics(truth > 0, prediction > 0)["foreground_pixel_recall"],
            "class_set": class_set_metrics(truth, prediction),
            "model_regions": model_region_metrics,
            "model_regions_agnostic": model_agnostic_metrics,
            "sam_regions": sam_region_metrics,
            "sam_strategy": sam_report.get("strategy"),
            "sam_proposal_count": len(sam_regions),
        }
        rows.append(row_metrics)
        input_files.extend((image_path, mask_path))
        if index - 1 in representative_indices:
            target = visual_dir / f"representative_{index}_{Path(row['image']).stem}.png"
            _save_visual(image, truth, prediction, sam_masks, row_metrics,
                         class_names, palette, target)
            visual_paths.append(target.relative_to(out_dir).as_posix())
        if index % 5 == 0 or index == len(dev_rows):
            print(f"WED segmentation DEV: {index}/{len(dev_rows)} views", flush=True)

    report = {
        "stage": "wed_native_semantic_segmentation",
        "tier": "dev",
        "split": "fixed seed-42 10% physical-group carve from WED TRAIN",
        "locked_accessed": False,
        "aruco_accessed": False,
        "test_split_accessed": False,
        "data_sha256": _sha(input_files),
        "dev_group_sha256": hashlib.sha256(
            "\n".join(sorted(dev_groups)).encode()).hexdigest(),
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
        "training_report": "experiments/wed_native_segmentation/training_report.json",
        "training_report_sha256": hashlib.sha256(
            (out_dir / "training_report.json").read_bytes()).hexdigest(),
        "architecture": checkpoint["architecture"],
        "n_classes": checkpoint["n_classes"],
        "sam_candidate": "dense_grid_box; 25 seed prompts, no output cap",
        "sam2_revision": SAM2_REVISION,
        "sam2_segmenter_definition_sha256": hashlib.sha256(
            (ROOT / "models/dish_segmenter.py").read_bytes()).hexdigest(),
        "evaluation_script_sha256": hashlib.sha256(
            Path(__file__).resolve().read_bytes()).hexdigest(),
        "metrics": _summarize(rows, confusions, class_names),
        "per_view": rows,
    }
    report["visuals"] = visual_paths
    (out_dir / "dev_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_markdown(report, out_dir / "dev_report.md")
    return report


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    metrics = report["metrics"]
    pixel = metrics["pixel"]
    model_regions = metrics["semantic_regions_class_aware"]
    comparisons = metrics["regions_class_agnostic_comparison"]
    sam = comparisons["sam2_dense_grid_candidate"]
    model_agnostic = comparisons["wed_semantic_model"]
    lines = [
        "# WED-native semantic segmentation DEV baseline", "",
        "The model predicts WED semantic classes directly. WED does not supply instance IDs; region counts below use derived 8-connected class components.", "",
        f"- Views / groups: {metrics['n_views']} / {metrics['n_groups']}",
        f"- Architecture: `{report['architecture']}` ({report['n_classes']} labels)",
        f"- Model checkpoint SHA-256: `{report['checkpoint_sha256']}`",
        f"- LOCKED / ArUco / WED test accessed: `{report['locked_accessed']}` / `{report['aruco_accessed']}` / `{report['test_split_accessed']}`",
        "", "## Pixel segmentation", "",
        "| Metric | WED model |", "|---|---:|",
        f"| Macro food IoU | {pixel['macro_food_iou']:.4f} |",
        f"| Macro food Dice | {pixel['macro_food_dice']:.4f} |",
        f"| Foreground union IoU | {pixel['foreground_union']['iou']:.4f} |",
        f"| Foreground union Dice | {pixel['foreground_union']['dice']:.4f} |",
        "", "## Region detection", "",
        "For a direct detector comparison, both methods use class-agnostic one-to-one IoU matching at 0.5 over the same DEV views.", "",
        "| Metric | WED model regions | SAM2 dense-grid |",
        "|---|---:|---:|",
        f"| Precision (95% group CI) | {model_agnostic['precision']:.4f} [{model_agnostic['group_bootstrap_95ci']['precision'][0]:.4f}, {model_agnostic['group_bootstrap_95ci']['precision'][1]:.4f}] | {sam['precision']:.4f} [{sam['group_bootstrap_95ci']['precision'][0]:.4f}, {sam['group_bootstrap_95ci']['precision'][1]:.4f}] |",
        f"| Recall (95% group CI) | {model_agnostic['recall']:.4f} [{model_agnostic['group_bootstrap_95ci']['recall'][0]:.4f}, {model_agnostic['group_bootstrap_95ci']['recall'][1]:.4f}] | {sam['recall']:.4f} [{sam['group_bootstrap_95ci']['recall'][0]:.4f}, {sam['group_bootstrap_95ci']['recall'][1]:.4f}] |",
        f"| F1 (95% group CI) | {model_agnostic['f1']:.4f} [{model_agnostic['group_bootstrap_95ci']['f1'][0]:.4f}, {model_agnostic['group_bootstrap_95ci']['f1'][1]:.4f}] | {sam['f1']:.4f} [{sam['group_bootstrap_95ci']['f1'][0]:.4f}, {sam['group_bootstrap_95ci']['f1'][1]:.4f}] |",
        f"| Duplicate overlapping predictions | {model_agnostic['duplicate_overlapping_predictions']} | {sam['duplicate_overlapping_predictions']} |",
        f"| Spurious non-overlapping predictions | {model_agnostic['spurious_nonoverlapping_predictions']} | {sam['spurious_nonoverlapping_predictions']} |",
        f"| Missed semantic regions | {model_agnostic['missed_semantic_regions']} | {sam['missed_semantic_regions']} |",
        f"| Complete region recovery views | {model_agnostic['complete_region_recovery_views']}/{metrics['n_views']} | {sam['complete_region_recovery_views']}/{metrics['n_views']} |",
        "", "The WED model also has class-aware region scores:", "",
        f"- Class-aware region precision / recall / F1: {model_regions['precision']:.4f} / {model_regions['recall']:.4f} / {model_regions['f1']:.4f}.",
        f"- Exact WED class-set meals: {model_regions['class_set_exact_views']}/{metrics['n_views']}.",
        "", "The SAM2 comparison uses the same DEV images and class-agnostic region matching. SAM2 has no semantic class output, so per-class pixel metrics and class-set accuracy do not apply. The model's class-agnostic region comparison is also recorded in `dev_report.json`.",
        "", "## Per-class metrics", "",
        f"Macro food IoU averages over {sum(v['dev_views_present'] > 0 for v in pixel['per_class'].values())} classes present in DEV; three taxonomy classes have no DEV examples.", "",
        "| WED class | Pixel precision | Pixel recall | IoU (95% group CI) | Dice | DEV views present |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for item in pixel["per_class"].values():
        iou_ci = item["iou_group_bootstrap_95ci"]
        iou_ci_text = ("n/a" if iou_ci is None else
                       f"[{iou_ci[0]:.4f}, {iou_ci[1]:.4f}]")
        lines.append(
            f"| {item['class']} | {item['pixel_precision']:.4f} | "
            f"{item['pixel_recall']:.4f} | {item['iou']:.4f} "
            f"{iou_ci_text} | "
            f"{item['dice']:.4f} | {item['dev_views_present']} |")
    lines.extend(["", "## Representative multi-item views", ""])
    for relative in report.get("visuals", []):
        lines.append(f"![WED ground truth, model, and SAM2 comparison]({relative})")
        lines.append("")
    lines.extend([
        "## Limitations", "",
        "Connected components are semantic-region proxies, not authoritative physical instances. Same-class portions that touch can merge in WED labels; annotation gaps can split one food region. Exact class-set and complete-region results should be interpreted with this annotation contract in mind. This report is a segmentation baseline only and makes no depth or weight-estimation claim.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--wed-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--checkpoint", type=Path,
                        default=ROOT / "experiments/wed_native_segmentation/model_best.pt")
    parser.add_argument("--out-dir", type=Path,
                        default=ROOT / "experiments/wed_native_segmentation")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    report = evaluate(manifest=args.manifest, wed_root=args.wed_root,
                      checkpoint_path=args.checkpoint, out_dir=args.out_dir,
                      device_name=args.device)
    print(json.dumps({
        "n_views": report["metrics"]["n_views"],
        "macro_food_iou": report["metrics"]["pixel"]["macro_food_iou"],
        "model_region_f1": report["metrics"]["semantic_regions_class_aware"]["f1"],
        "sam_region_f1": report["metrics"]["regions_class_agnostic_comparison"][
            "sam2_dense_grid_candidate"]["f1"],
        "report": str(args.out_dir / "dev_report.md"),
    }, indent=2))


if __name__ == "__main__":
    main()
