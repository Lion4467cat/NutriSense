"""Frozen, matched DEV comparison for WED semantic segmentation candidates."""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.wed_segmentation_variants import build_variant
from models.wed_semantic_segmenter import load_checkpoint
from nutrisense_synth.parameters import (
    read_wed_train_manifest, wed_dev_group_ids, wed_group_id,
)
from nutrisense_synth.wed_segmentation import (
    N_CLASSES, class_metrics, confusion_matrix, group_bootstrap_ci,
)
from tools.analyze_wed_semantic_errors import _class_errors

PRIORITY_CLASSES = ("steamed rice", "papad", "salad", "leaf-dal",
                    "muskmelon", "tomato-pappu")
SIZE_BINS = ("tiny_lt_0.10pct", "small_0.10_to_0.25pct",
             "medium_0.25_to_0.50pct", "large_ge_0.50pct")


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha_data(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.as_posix().encode())
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _boundary(mask: np.ndarray) -> np.ndarray:
    binary = mask.astype(np.uint8)
    eroded = cv2.erode(binary, np.ones((3, 3), np.uint8), iterations=1)
    return (binary != eroded)


def _boundary_counts(truth: np.ndarray, pred: np.ndarray,
                     radius: int = 3) -> tuple[int, int, int, int]:
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                       (2 * radius + 1, 2 * radius + 1))
    tp_pred = fp_pred = tp_truth = fn_truth = 0
    class_ids = (set(map(int, np.unique(truth)))
                 | set(map(int, np.unique(pred)))) - {0}
    for class_id in class_ids:
        gt_edge = _boundary(truth == class_id)
        pred_edge = _boundary(pred == class_id)
        dilated_gt = cv2.dilate(gt_edge.astype(np.uint8), kernel) > 0
        dilated_pred = cv2.dilate(pred_edge.astype(np.uint8), kernel) > 0
        tp_pred += int(np.count_nonzero(pred_edge & dilated_gt))
        fp_pred += int(np.count_nonzero(pred_edge & ~dilated_gt))
        tp_truth += int(np.count_nonzero(gt_edge & dilated_pred))
        fn_truth += int(np.count_nonzero(gt_edge & ~dilated_pred))
    return tp_pred, fp_pred, tp_truth, fn_truth


def _load_candidate(path: Path, *, device: torch.device
                    ) -> tuple[torch.nn.Module, tuple[int, int], dict[str, Any]]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    architecture = checkpoint.get("architecture_id")
    if architecture not in {"deeplabv3", "deeplabv3plus", "segformer_b0"}:
        raise ValueError(f"Unrecognized candidate architecture in {path}")
    model = build_variant(architecture, pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device).eval()
    size = (int(checkpoint["input_width"]), int(checkpoint["input_height"]))
    return model, size, checkpoint


def _predict(model: torch.nn.Module, image_bgr: np.ndarray,
             size: tuple[int, int], device: torch.device
             ) -> tuple[np.ndarray, float, torch.Tensor]:
    height, width = image_bgr.shape[:2]
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    resized = cv2.resize(rgb, size, interpolation=cv2.INTER_LINEAR)
    array = resized.astype(np.float32) / 255.0
    mean = np.asarray((0.485, 0.456, 0.406), np.float32)[None, None, :]
    std = np.asarray((0.229, 0.224, 0.225), np.float32)[None, None, :]
    tensor = torch.from_numpy(np.ascontiguousarray(
        ((array - mean) / std).transpose(2, 0, 1))).unsqueeze(0).to(device)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    start = time.perf_counter()
    with torch.inference_mode():
        logits = model(tensor)["out"]
        logits = F.interpolate(logits, size=(height, width), mode="bilinear",
                               align_corners=False)
        labels = logits.argmax(dim=1)[0].to(torch.uint8)
    if device.type == "cuda":
        torch.cuda.synchronize(device)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return labels.cpu().numpy(), elapsed_ms, logits


def _aggregate(candidate: dict[str, Any], view_rows: list[dict[str, Any]],
               confusions: list[np.ndarray], class_names: dict[int, str]
               ) -> dict[str, Any]:
    pixel = class_metrics(confusions, class_names)
    classes = pixel["per_class"]
    region_tp = sum(x["regions"]["one_to_one_iou_matched_regions"]
                    for x in view_rows)
    region_gt = sum(x["regions"]["ground_truth_semantic_regions"]
                    for x in view_rows)
    region_pred = sum(x["regions"]["predicted_semantic_regions"]
                      for x in view_rows)
    precision = region_tp / max(1, region_pred)
    recall = region_tp / max(1, region_gt)
    region_f1 = 2 * precision * recall / max(1e-12, precision + recall)
    sizes = {}
    for name in SIZE_BINS:
        total = {key: 0 for key in (
            "gt_regions", "matched_iou_at_0_5", "missed_no_overlap",
            "gt_pixels", "recalled_pixels", "fragmented_gt_regions")}
        for row in view_rows:
            for key, value in row["regions"]["size_bins"][name].items():
                if key in total:
                    total[key] += int(value)
        total["region_recall_iou_0_5"] = (
            total["matched_iou_at_0_5"] / total["gt_regions"]
            if total["gt_regions"] else None)
        total["no_overlap_miss_rate"] = (
            total["missed_no_overlap"] / total["gt_regions"]
            if total["gt_regions"] else None)
        total["pixel_recall"] = (
            total["recalled_pixels"] / total["gt_pixels"]
            if total["gt_pixels"] else None)
        sizes[name] = total
    boundary_pred = sum(x["boundary"][0] for x in view_rows)
    boundary_pred_fp = sum(x["boundary"][1] for x in view_rows)
    boundary_gt = sum(x["boundary"][2] for x in view_rows)
    boundary_gt_fn = sum(x["boundary"][3] for x in view_rows)
    boundary_precision = boundary_pred / max(1, boundary_pred + boundary_pred_fp)
    boundary_recall = boundary_gt / max(1, boundary_gt + boundary_gt_fn)
    boundary_f1 = (2 * boundary_precision * boundary_recall
                   / max(1e-12, boundary_precision + boundary_recall))
    total_ms = [row["inference_ms"] for row in view_rows]
    return {
        "macro_food_iou": pixel["macro_food_iou"],
        "foreground_iou": pixel["foreground_union"]["iou"],
        "per_class_iou": classes,
        "region_precision": precision,
        "region_recall": recall,
        "region_f1": region_f1,
        "ground_truth_semantic_regions": region_gt,
        "predicted_semantic_regions": region_pred,
        "region_matches_iou_0_5": region_tp,
        "size_bins": sizes,
        "merge_proxy_total": sum(x["regions"][
            "predicted_components_overlapping_multiple_gt_components_same_class"]
                                 for x in view_rows),
        "fragmentation_proxy_total": sum(x["regions"][
            "fragmented_gt_regions_overlapping_multiple_predicted_components"]
                                          for x in view_rows),
        "mean_merge_proxy_per_view": float(np.mean([
            x["regions"]["predicted_components_overlapping_multiple_gt_components_same_class"]
            for x in view_rows])),
        "mean_fragmentation_proxy_per_view": float(np.mean([
            x["regions"]["fragmented_gt_regions_overlapping_multiple_predicted_components"]
            for x in view_rows])),
        "boundary_f1_tolerance_3px": boundary_f1,
        "boundary_precision_tolerance_3px": boundary_precision,
        "boundary_recall_tolerance_3px": boundary_recall,
        "inference_latency_ms_batch1": {
            "mean": float(np.mean(total_ms)),
            "median": float(np.median(total_ms)),
            "p90": float(np.quantile(total_ms, 0.9)),
        },
        "peak_inference_vram_mb": candidate["peak_inference_vram_mb"],
        "parameter_count": candidate["parameter_count"],
        "checkpoint_mb": candidate["checkpoint_mb"],
        "complete_class_set_views": int(sum(x["class_set_exact"] for x in view_rows)),
        "n_views": len(view_rows),
        "per_view": view_rows,
    }


def _group_sufficient_counts(view_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in view_rows:
        group = row["group"]
        state = grouped.setdefault(group, {
            "class_counts": np.zeros((N_CLASSES, 3), dtype=np.int64),
            "foreground_counts": np.zeros(3, dtype=np.int64),
            "region_tp": 0, "region_gt": 0, "region_pred": 0,
            "tiny_pixel_recalled": 0, "tiny_pixel_gt": 0,
            "tiny_region_tp": 0, "tiny_region_gt": 0,
            "merge": 0, "fragmentation": 0, "views": 0,
            "boundary": np.zeros(4, dtype=np.int64),
        })
        state["class_counts"] += np.asarray(row["pixel_class_counts"], dtype=np.int64)
        state["foreground_counts"] += np.asarray(row["foreground_counts"], dtype=np.int64)
        component = row["regions"]
        state["region_tp"] += component["one_to_one_iou_matched_regions"]
        state["region_gt"] += component["ground_truth_semantic_regions"]
        state["region_pred"] += component["predicted_semantic_regions"]
        tiny = component["size_bins"][SIZE_BINS[0]]
        state["tiny_pixel_recalled"] += tiny["recalled_pixels"]
        state["tiny_pixel_gt"] += tiny["gt_pixels"]
        state["tiny_region_tp"] += tiny["matched_iou_at_0_5"]
        state["tiny_region_gt"] += tiny["gt_regions"]
        state["merge"] += component[
            "predicted_components_overlapping_multiple_gt_components_same_class"]
        state["fragmentation"] += component[
            "fragmented_gt_regions_overlapping_multiple_predicted_components"]
        state["views"] += 1
        state["boundary"] += np.asarray(row["boundary"], dtype=np.int64)
    return grouped


def _metric_from_counts(states: list[dict[str, Any]], metric: str,
                        present_classes: list[int]) -> float:
    classes = sum((state["class_counts"] for state in states),
                  start=np.zeros((N_CLASSES, 3), dtype=np.int64))
    if metric == "macro_food_iou":
        ious = []
        for class_id in present_classes:
            tp, fp, fn = map(int, classes[class_id])
            ious.append(tp / (tp + fp + fn) if tp + fp + fn else 0.0)
        return float(np.mean(ious)) if ious else 0.0
    if metric == "foreground_iou":
        tp, pred_food, gt_food = map(int, sum(
            (state["foreground_counts"] for state in states),
            start=np.zeros(3, dtype=np.int64)))
        return tp / max(1, pred_food + gt_food - tp)
    if metric == "region_f1":
        tp = sum(state["region_tp"] for state in states)
        gt = sum(state["region_gt"] for state in states)
        pred = sum(state["region_pred"] for state in states)
        return 2 * tp / max(1, gt + pred)
    if metric == "tiny_pixel_recall":
        return sum(state["tiny_pixel_recalled"] for state in states) / max(
            1, sum(state["tiny_pixel_gt"] for state in states))
    if metric == "tiny_region_recall_iou_0_5":
        return sum(state["tiny_region_tp"] for state in states) / max(
            1, sum(state["tiny_region_gt"] for state in states))
    if metric == "mean_merge_proxy_per_view":
        return sum(state["merge"] for state in states) / max(
            1, sum(state["views"] for state in states))
    if metric == "mean_fragmentation_proxy_per_view":
        return sum(state["fragmentation"] for state in states) / max(
            1, sum(state["views"] for state in states))
    if metric == "boundary_f1_tolerance_3px":
        counts = sum((state["boundary"] for state in states),
                     start=np.zeros(4, dtype=np.int64))
        precision = counts[0] / max(1, counts[0] + counts[1])
        recall = counts[2] / max(1, counts[2] + counts[3])
        return float(2 * precision * recall / max(1e-12, precision + recall))
    raise KeyError(metric)


def _paired_bootstrap(candidate_rows: list[dict[str, Any]],
                      baseline_rows: list[dict[str, Any]], metric: str,
                      *, reps: int = 10_000, seed: int = 42
                      ) -> list[float] | None:
    current = _group_sufficient_counts(candidate_rows)
    reference = _group_sufficient_counts(baseline_rows)
    groups = sorted(set(current) & set(reference))
    if not groups:
        return None
    all_class_counts = sum((current[group]["class_counts"] for group in groups),
                           start=np.zeros((N_CLASSES, 3), dtype=np.int64))
    present_classes = [class_id for class_id in range(1, N_CLASSES)
                       if all_class_counts[class_id, 2] > 0]
    point = (_metric_from_counts([current[group] for group in groups], metric,
                                 present_classes)
             - _metric_from_counts([reference[group] for group in groups], metric,
                                   present_classes))
    if len(groups) == 1:
        return [float(point), float(point)]
    rng = np.random.default_rng(seed)
    sample = np.empty(reps, dtype=np.float64)
    for index in range(reps):
        selected = rng.integers(0, len(groups), size=len(groups))
        sampled_groups = [groups[int(i)] for i in selected]
        sample[index] = (
            _metric_from_counts([current[group] for group in sampled_groups],
                                metric, present_classes)
            - _metric_from_counts([reference[group] for group in sampled_groups],
                                  metric, present_classes))
    low, high = np.quantile(sample, (0.025, 0.975))
    return [float(low), float(high)]


def _paired_differences(rows: dict[str, dict[str, Any]],
                        baseline_name: str) -> dict[str, Any]:
    baseline = rows[baseline_name]
    differences: dict[str, Any] = {}
    metric_names = ("macro_food_iou", "foreground_iou", "region_f1",
                    "mean_merge_proxy_per_view",
                    "mean_fragmentation_proxy_per_view",
                    "boundary_f1_tolerance_3px")
    for name, result in rows.items():
        if name == baseline_name:
            continue
        diff: dict[str, Any] = {}
        for metric in metric_names:
            diff[metric] = {
                "point": result[metric] - baseline[metric],
                "group_bootstrap_95ci": _paired_bootstrap(
                    result["per_view"], baseline["per_view"], metric),
            }
        candidate_tiny = result["size_bins"][SIZE_BINS[0]]
        baseline_tiny = baseline["size_bins"][SIZE_BINS[0]]
        for metric in ("pixel_recall", "region_recall_iou_0_5"):
            lhs, rhs = candidate_tiny[metric], baseline_tiny[metric]
            diff[f"tiny_{metric}"] = {
                "point": (lhs - rhs) if lhs is not None and rhs is not None else None,
                "group_bootstrap_95ci": _paired_bootstrap(
                    result["per_view"], baseline["per_view"],
                    f"tiny_{metric}"),
            }
        per_class = {}
        for class_id in range(1, N_CLASSES):
            name_label = result["per_class_iou"][str(class_id)]["class"]
            a = result["per_class_iou"][str(class_id)]["iou"]
            b = baseline["per_class_iou"][str(class_id)]["iou"]
            per_class[str(class_id)] = {"class": name_label, "iou_delta": a - b}
        diff["per_class_iou_delta"] = per_class
        differences[name] = diff
    return differences


def _visuals(images: list[np.ndarray], truths: list[np.ndarray],
             prediction_sets: dict[str, list[np.ndarray]], rows: list[dict[str, Any]],
             output: Path, palette: np.ndarray, reference_name: str,
             best_candidate_name: str) -> list[str]:
    selected = [0, len(images) // 2, len(images) - 1]
    output.mkdir(parents=True, exist_ok=True)
    paths = []
    for index in selected:
        panels = [images[index], truths[index],
                  prediction_sets[reference_name][index],
                  prediction_sets[best_candidate_name][index]]
        titles = ["Original", "WED semantic GT", "Frozen DeepLabV3 reference",
                  best_candidate_name]
        fig, axes = plt.subplots(1, len(panels), figsize=(5 * len(panels), 5))
        for axis, panel, title in zip(axes, panels, titles):
            rgb = cv2.cvtColor(panel, cv2.COLOR_BGR2RGB) if panel.ndim == 3 else None
            if rgb is None:
                axis.imshow(palette[panel])
            else:
                axis.imshow(rgb)
            axis.set_title(title, fontsize=8)
            axis.axis("off")
        fig.suptitle(rows[index]["image"], fontsize=8)
        fig.tight_layout()
        path = output / f"comparison_{index:03d}.png"
        fig.savefig(path, dpi=130)
        plt.close(fig)
        paths.append(path.name)
    return paths


def evaluate_study(*, manifest: Path, wed_root: Path, study_dir: Path,
                   frozen_checkpoint: Path, out_dir: Path,
                   device_name: str = "cuda") -> dict[str, Any]:
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; use the approved GPU runtime")
    device = torch.device(device_name)
    manifest_rows = read_wed_train_manifest(manifest)
    dev_groups = wed_dev_group_ids(manifest_rows)
    dev_rows = [r for r in manifest_rows if wed_group_id(r) in dev_groups]
    if len(dev_rows) != 108 or len(dev_groups) != 21:
        raise ValueError(f"Expected fixed 108-view / 21-group DEV carve, got {len(dev_rows)} / {len(dev_groups)}")

    training_report = json.loads((study_dir / "training_study_report.json").read_text())
    baseline_manifest = json.loads((frozen_checkpoint.parent / "baseline_manifest.json").read_text())
    if _sha(frozen_checkpoint) != baseline_manifest["checkpoint_sha256"]:
        raise ValueError("Frozen baseline checkpoint hash differs from baseline manifest")
    id_map = json.loads((ROOT / "data/wed/index_map.json").read_text())
    class_names = {int(k): str(v) for k, v in id_map.items() if int(k) > 0}
    # Include every stage-A candidate and the two alternate architectures.
    candidate_paths = {
        entry["candidate"]["name"]: study_dir / "candidates" / entry["candidate"]["name"] / "model_best.pt"
        for entry in training_report["stage_a_runs"]
    }
    for entry in training_report["architecture_runs"]:
        name = entry["candidate"]["name"]
        candidate_paths[name] = study_dir / "candidates" / name / "model_best.pt"

    model_specs: dict[str, dict[str, Any]] = {}
    baseline_candidate_data = {
        "parameter_count": None,
        "peak_inference_vram_mb": None,
        "checkpoint_mb": frozen_checkpoint.stat().st_size / (1024 * 1024),
    }
    model_specs["frozen_deeplabv3_reference"] = {
        "kind": "frozen_baseline", "path": frozen_checkpoint,
        "size": (768, 1024), "metadata": baseline_candidate_data,
    }
    for name, path in candidate_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing candidate checkpoint: {path}")
        ckpt = torch.load(path, map_location="cpu", weights_only=False)
        size = (int(ckpt["input_width"]), int(ckpt["input_height"]))
        model_specs[name] = {"kind": "candidate", "path": path,
                             "size": size, "metadata": {
            "parameter_count": None,
            "peak_inference_vram_mb": None,
            "checkpoint_mb": path.stat().st_size / (1024 * 1024),
            "checkpoint_sha256": _sha(path),
            "architecture_id": ckpt["architecture_id"],
            "input_size_wh": list(size),
        }}

    images, truths = [], []
    for row in dev_rows:
        image = cv2.imread(str(wed_root / row["image"]), cv2.IMREAD_COLOR)
        truth = cv2.imread(str(wed_root / row["mask"]), cv2.IMREAD_GRAYSCALE)
        if image is None or truth is None:
            raise FileNotFoundError(f"Could not decode DEV image/mask: {row['image']}")
        images.append(image)
        truths.append(truth)

    all_results: dict[str, dict[str, Any]] = {}
    all_predictions: dict[str, list[np.ndarray]] = {}
    for model_name, spec in model_specs.items():
        size = spec["size"]
        metadata = spec["metadata"]
        if spec["kind"] == "frozen_baseline":
            model, _ = load_checkpoint(spec["path"], device=device)
        else:
            model, _, checkpoint = _load_candidate(spec["path"], device=device)
            metadata["parameter_count"] = sum(p.numel() for p in model.parameters())
        if device.type == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats(device)
        if metadata["parameter_count"] is None:
            metadata["parameter_count"] = sum(p.numel() for p in model.parameters())
        # Warm up once at batch size one; exclude warmups from reported latency.
        _predict(model, images[0], size, device)
        _predict(model, images[0], size, device)
        prediction_set, rows, confusions = [], [], []
        for index, (image, truth, manifest_row) in enumerate(zip(images, truths, dev_rows)):
            pred, latency, _logits = _predict(model, image, size, device)
            prediction_set.append(pred)
            confusions.append(confusion_matrix(truth, pred))
            component, _ = _class_errors(truth, pred, *truth.shape)
            boundary = _boundary_counts(truth, pred, radius=3)
            tiny = component["size_bins"][SIZE_BINS[0]]
            classes_gt = set(map(int, np.unique(truth))) - {0}
            classes_pred = set(map(int, np.unique(pred))) - {0}
            cm = confusions[-1]
            class_iou_values = []
            for class_id in classes_gt:
                tp = int(cm[class_id, class_id])
                union = int(cm[class_id, :].sum() + cm[:, class_id].sum() - tp)
                class_iou_values.append(tp / union if union else 0.0)
            fg_tp = int(cm[1:, 1:].sum())
            fg_union = int(cm[1:, :].sum() + cm[:, 1:].sum() - fg_tp)
            row_region_tp = component["one_to_one_iou_matched_regions"]
            row_region_gt = component["ground_truth_semantic_regions"]
            row_region_pred = component["predicted_semantic_regions"]
            row_region_p = row_region_tp / max(1, row_region_pred)
            row_region_r = row_region_tp / max(1, row_region_gt)
            per_view = {
                "group": wed_group_id(manifest_row),
                "image": manifest_row["image"],
                "regions": component,
                "boundary": boundary,
                "inference_ms": latency,
                "class_set_exact": classes_gt == classes_pred,
                "pixel_class_counts": [[
                    int(confusions[-1][class_id, class_id]),
                    int(confusions[-1][:, class_id].sum() - confusions[-1][class_id, class_id]),
                    int(confusions[-1][class_id, :].sum() - confusions[-1][class_id, class_id]),
                ] for class_id in range(N_CLASSES)],
                "foreground_counts": [
                    int(confusions[-1][1:, 1:].sum()),
                    int(confusions[-1][:, 1:].sum()),
                    int(confusions[-1][1:, :].sum()),
                ],
                "macro_food_iou": float(np.mean(class_iou_values)) if class_iou_values else None,
                "foreground_iou": fg_tp / max(1, fg_union),
                "region_f1": 2 * row_region_p * row_region_r / max(1e-12, row_region_p + row_region_r),
                "mean_merge_proxy_per_view": component[
                    "predicted_components_overlapping_multiple_gt_components_same_class"],
                "mean_fragmentation_proxy_per_view": component[
                    "fragmented_gt_regions_overlapping_multiple_predicted_components"],
                "tiny_pixel_recall": tiny["pixel_recall"],
                "tiny_region_recall_iou_0_5": tiny["region_recall_iou_0_5"],
            }
            rows.append(per_view)
            if (index + 1) % 36 == 0:
                print(f"{model_name}: {index + 1}/108 DEV views", flush=True)
        if device.type == "cuda":
            metadata["peak_inference_vram_mb"] = round(
                torch.cuda.max_memory_allocated(device) / (1024 ** 2), 1)
        all_predictions[model_name] = prediction_set
        all_results[model_name] = _aggregate(metadata, rows, confusions, class_names)
        metadata.update({k: v for k, v in all_results[model_name].items()
                         if k in ("peak_inference_vram_mb", "parameter_count", "checkpoint_mb")})
        print(f"completed DEV evaluation: {model_name}", flush=True)
        del model
        if device.type == "cuda":
            torch.cuda.empty_cache()

    differences = _paired_differences(all_results, "frozen_deeplabv3_reference")
    frozen = all_results["frozen_deeplabv3_reference"]
    normalized_priority = {x.casefold().replace("-", " ") for x in PRIORITY_CLASSES}
    priority_ids = {class_id: name for class_id, name in class_names.items()
                    if name.casefold().replace("-", " ") in normalized_priority}
    promotion: dict[str, Any] = {}
    for name, diff in differences.items():
        tiny_p = diff["tiny_pixel_recall"]["point"]
        tiny_r = diff["tiny_region_recall_iou_0_5"]["point"]
        tiny_ci_p = diff["tiny_pixel_recall"]["group_bootstrap_95ci"]
        tiny_ci_r = diff["tiny_region_recall_iou_0_5"]["group_bootstrap_95ci"]
        macro_ci = diff["macro_food_iou"]["group_bootstrap_95ci"]
        fg_ci = diff["foreground_iou"]["group_bootstrap_95ci"]
        region_ci = diff["region_f1"]["group_bootstrap_95ci"]
        merge_ci = diff["mean_merge_proxy_per_view"]["group_bootstrap_95ci"]
        fragmentation_ci = diff["mean_fragmentation_proxy_per_view"]["group_bootstrap_95ci"]
        boundary_delta = diff["boundary_f1_tolerance_3px"]["point"]
        priority_deltas = [diff["per_class_iou_delta"][str(cid)]["iou_delta"]
                           for cid in priority_ids]
        latency_ratio = (all_results[name]["inference_latency_ms_batch1"]["mean"]
                         / max(1e-9, frozen["inference_latency_ms_batch1"]["mean"]))
        conditions = {
            "macro_iou_gain_at_least_0_01_and_ci_above_zero": (
                diff["macro_food_iou"]["point"] >= 0.01 and macro_ci is not None
                and macro_ci[0] > 0),
            "tiny_region_gain_at_least_0_05_with_ci_above_zero": (
                (tiny_p is not None and tiny_p >= 0.05 and tiny_ci_p is not None
                 and tiny_ci_p[0] > 0)
                or (tiny_r is not None and tiny_r >= 0.05 and tiny_ci_r is not None
                    and tiny_ci_r[0] > 0)),
            "foreground_iou_lower_ci_above_minus_0_01": fg_ci is not None and fg_ci[0] > -0.01,
            "region_f1_lower_ci_above_minus_0_01": region_ci is not None and region_ci[0] > -0.01,
            "priority_class_regression_no_worse_than_minus_0_05": (
                not priority_deltas or min(priority_deltas) >= -0.05),
            "merge_increase_upper_ci_at_most_0_25": merge_ci is not None and merge_ci[1] <= 0.25,
            "fragmentation_increase_upper_ci_at_most_0_25": (
                fragmentation_ci is not None and fragmentation_ci[1] <= 0.25),
            "boundary_f1_drop_no_more_than_0_01": boundary_delta >= -0.01,
            "latency_no_more_than_2x_reference": latency_ratio <= 2.0,
        }
        promotion[name] = {"passes": all(conditions.values()), "conditions": conditions,
                           "latency_ratio": latency_ratio,
                           "priority_class_iou_delta_min": min(priority_deltas)
                           if priority_deltas else None}
    passing = [name for name, result in promotion.items() if result["passes"]]
    recommend = (max(passing, key=lambda name: all_results[name]["macro_food_iou"])
                 if passing else None)
    out_dir.mkdir(parents=True, exist_ok=True)
    palette = np.zeros((N_CLASSES, 3), np.uint8)
    for class_id in range(1, N_CLASSES):
        palette[class_id] = (np.asarray(plt.get_cmap("hsv")(
            (class_id * 0.61803398875) % 1.0)[:3]) * 255).astype(np.uint8)
    best_candidate_name = max(
        (name for name in all_results if name != "frozen_deeplabv3_reference"),
        key=lambda name: all_results[name]["macro_food_iou"])
    visuals = _visuals(images, truths, all_predictions, dev_rows,
                       out_dir / "visuals", palette,
                       "frozen_deeplabv3_reference", best_candidate_name)
    candidate_metadata = {}
    for name, checkpoint_path in candidate_paths.items():
        training_report_path = study_dir / "candidates" / name / "training_report.json"
        candidate_training = json.loads(training_report_path.read_text())
        candidate_metadata[name] = {
            "configuration": candidate_training["candidate"],
            "checkpoint": str(checkpoint_path),
            "checkpoint_sha256": _sha(checkpoint_path),
            "selected_epoch": candidate_training["training_budget"]["selected_epoch"],
            "training_report_sha256": _sha(training_report_path),
            "pretrained_weight_sha256": candidate_training.get("pretrained_weight_sha256"),
            "peak_training_vram_mb": candidate_training.get("peak_training_vram_mb"),
        }
    report = {
        "stage": "frozen_dev_wed_segmentation_comparison",
        "created_at": datetime.now(UTC).isoformat(),
        "split": "fixed seed-42 WED TRAIN physical-group DEV carve",
        "dev_views": len(dev_rows),
        "dev_groups": len(dev_groups),
        "dev_group_sha256": hashlib.sha256("\n".join(sorted(dev_groups)).encode()).hexdigest(),
        "dev_data_sha256": _sha_data([wed_root / p for row in dev_rows
                                      for p in (row["image"], row["mask"])]),
        "frozen_baseline_sha256": _sha(frozen_checkpoint),
        "baseline_manifest_sha256": _sha(frozen_checkpoint.parent / "baseline_manifest.json"),
        "training_study_report_sha256": _sha(study_dir / "training_study_report.json"),
        "candidate_metadata": candidate_metadata,
        "class_names": {str(k): v for k, v in class_names.items()},
        "priority_classes_found": {str(k): v for k, v in priority_ids.items()},
        "metrics": all_results,
        "paired_differences_vs_frozen_reference": differences,
        "promotion_gate": promotion,
        "recommendation": recommend if passing else None,
        "recommendation_note": ("Candidate passes every predeclared promotion criterion."
                                if passing else "No candidate passes every predeclared criterion; keep the frozen reference."),
        "execution_notes": [
            "An initial launch completed the matched DeepLabV3 control, then exited at the high-resolution run because the ASPP global-pooling BatchNorm received a singleton batch.",
            "The high-resolution run completed on retry with physical batch size 1, gradient accumulation 2, and ASPP global-pooling BatchNorm held in evaluation mode; it therefore has this documented training-side adjustment in addition to resolution and is not a perfectly isolated resolution-only ablation.",
            "No GPU out-of-memory event occurred; all seven final candidates completed 10 epochs and were frozen before DEV inference.",
        ],
        "visuals": visuals,
        "definitions": {
            "per_class_iou": "global confusion-matrix IoU; absent GT classes retain IoU 0 but are excluded from macro food IoU",
            "region_matching": "8-connected components per semantic class; one-to-one Hungarian IoU >= 0.5",
            "merge_fragmentation": "semantic raster connected-component proxies only; WED has no instance IDs",
            "small_region_bins": "GT component area as fraction of full image: <0.10%, 0.10-0.25%, 0.25-0.50%, >=0.50%",
            "boundary": "class-wise binary boundaries with 3-pixel tolerance at original DEV resolution",
            "latency": "batch-1 FP32 synchronized model forward plus logits resize; two warmups excluded",
        "bootstrap": "10,000 paired physical-meal-group bootstrap resamples, seed 42; each resample recomputes pooled metric sufficient counts",
        },
        "locked_accessed": False,
        "aruco_accessed": False,
        "wed_test_split_accessed": False,
        "synthetic_data_used": False,
        "geometry_or_weight_estimation_changed": False,
    }
    (out_dir / "comparison_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    _write_markdown(report, out_dir / "comparison_report.md")
    return report


def _write_markdown(report: dict[str, Any], path: Path) -> None:
    metrics = report["metrics"]
    baseline = metrics["frozen_deeplabv3_reference"]
    lines = [
        "# Controlled WED segmentation improvement study", "",
        f"DEV: {report['dev_views']} views / {report['dev_groups']} physical meal groups. Frozen baseline SHA-256: `{report['frozen_baseline_sha256']}`.",
        "LOCKED / ArUco / WED test accessed: **No**. Synthetic data used: **No**.", "",
        "All candidate checkpoints were trained and selected on eligible WED TRAIN groups before this single frozen DEV evaluation. Region and merge/fragmentation figures refer to connected components of semantic rasters; they are not serving-level instance metrics.", "",
        "Training budget was 10 epochs × 928 sampled TRAIN views per epoch (464 effective optimizer updates per epoch at batch 2), with the same 110-view internal group holdout for checkpoint selection. The selected Stage A recipe by internal-validation macro food IoU was boundary-aware loss.", "",
        "## Candidate comparison", "",
        "| Candidate | Macro food IoU | Foreground IoU | Region P / R / F1 | Tiny pixel / region recall | Merge / fragmentation per view | Boundary F1 (3 px) | latency ms | inference / training VRAM MB |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    ordered = ["frozen_deeplabv3_reference"] + [x for x in metrics if x != "frozen_deeplabv3_reference"]
    for name in ordered:
        row = metrics[name]
        tiny = row["size_bins"][SIZE_BINS[0]]
        vram = row["peak_inference_vram_mb"]
        train_vram = report["candidate_metadata"].get(name, {}).get("peak_training_vram_mb")
        lines.append(
            f"| {name} | {row['macro_food_iou']:.4f} | {row['foreground_iou']:.4f} | "
            f"{row['region_precision']:.3f} / {row['region_recall']:.3f} / {row['region_f1']:.3f} | "
            f"{tiny['pixel_recall']:.3f} / {tiny['region_recall_iou_0_5']:.3f} | "
            f"{row['mean_merge_proxy_per_view']:.2f} / {row['mean_fragmentation_proxy_per_view']:.2f} | "
            f"{row['boundary_f1_tolerance_3px']:.3f} | "
            f"{row['inference_latency_ms_batch1']['mean']:.1f} | "
            f"{vram if vram is not None else 'n/a'} / {train_vram if train_vram is not None else 'n/a'} |"
        )
    lines.extend(["", "## Per-class IoU", "", "| ID | Class | Frozen reference | Best macro candidate | Δ |", "|---:|---|---:|---:|---:|"])
    best_name = max((x for x in metrics if x != "frozen_deeplabv3_reference"),
                    key=lambda x: metrics[x]["macro_food_iou"])
    for class_id in range(1, N_CLASSES):
        base_class = baseline["per_class_iou"][str(class_id)]
        candidate_class = metrics[best_name]["per_class_iou"][str(class_id)]
        delta = candidate_class["iou"] - base_class["iou"]
        if base_class["ground_truth_pixels"] == 0:
            base_display = candidate_display = delta_display = "n/a"
        else:
            base_display = f"{base_class['iou']:.3f}"
            candidate_display = f"{candidate_class['iou']:.3f}"
            delta_display = f"{delta:+.3f}"
        lines.append(f"| {class_id} | {base_class['class']} | {base_display} | {candidate_display} | {delta_display} |")
    lines.extend(["", f"Best macro-IoU candidate for class table: `{best_name}`. Classes with no DEV ground-truth pixels show `n/a` and are excluded from macro food IoU.", "", "## Candidate changes versus frozen baseline", "", "| Candidate | Δ macro IoU [95% group CI] | Δ foreground IoU [95% CI] | Δ region F1 [95% CI] | Δ tiny pixel recall [95% CI] | Δ tiny region recall [95% CI] | Gate |", "|---|---:|---:|---:|---:|---:|---|"])
    for name, diff in report["paired_differences_vs_frozen_reference"].items():
        def fmt(key: str, *, result: dict[str, Any] = diff) -> str:
            item = result[key]
            ci = item["group_bootstrap_95ci"]
            if item["point"] is None or ci is None:
                return "n/a"
            return f"{item['point']:+.3f} [{ci[0]:+.3f}, {ci[1]:+.3f}]"
        lines.append(f"| {name} | {fmt('macro_food_iou')} | {fmt('foreground_iou')} | {fmt('region_f1')} | {fmt('tiny_pixel_recall')} | {fmt('tiny_region_recall_iou_0_5')} | {'PASS' if report['promotion_gate'][name]['passes'] else 'no'} |")
    priority_ids = {int(class_id): class_name
                    for class_id, class_name in report["priority_classes_found"].items()}
    lines.extend(["", "## Priority classes across candidates", "",
                  "| Class | Frozen | 10-epoch control | High resolution* | Class-balanced | Food augmentation | Boundary loss | DeepLabV3+ | SegFormer-B0 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|"])
    candidate_order = [
        "frozen_deeplabv3_reference", "dlv3_control", "dlv3_highres",
        "dlv3_class_balanced", "dlv3_food_augmentation", "dlv3_boundary_loss",
        "architecture_deeplabv3plus", "architecture_segformer_b0",
    ]
    for class_id, class_name in priority_ids.items():
        values = []
        for candidate in candidate_order:
            class_result = metrics[candidate]["per_class_iou"][str(class_id)]
            values.append("n/a" if class_result["ground_truth_pixels"] == 0
                          else f"{class_result['iou']:.3f}")
        lines.append(f"| {class_name} | " + " | ".join(values) + " |")
    lines.append("\n*High-resolution run also held ASPP global-pooling BatchNorm in evaluation mode; see execution note below.")
    lines.extend(["", "## Small-region metrics by size", "", "Candidate values below are for the highest macro-IoU candidate; full candidate values are in the JSON report.", "", "| GT size bin | GT regions | Pixel recall | IoU≥0.5 region recall | No-overlap miss rate |", "|---|---:|---:|---:|---:|"])
    for name in SIZE_BINS:
        row = metrics[best_name]["size_bins"][name]
        lines.append(f"| {name} | {row['gt_regions']} | {row['pixel_recall'] if row['pixel_recall'] is not None else 'n/a'} | {row['region_recall_iou_0_5'] if row['region_recall_iou_0_5'] is not None else 'n/a'} | {row['no_overlap_miss_rate'] if row['no_overlap_miss_rate'] is not None else 'n/a'} |")
    lines.extend(["", "## Execution note", "", *[f"- {note}" for note in report["execution_notes"]], "", "The high-resolution result has an ASPP pooled-BatchNorm adjustment, so interpret it as a practical high-resolution candidate rather than a perfectly isolated resolution-only ablation.", "", "## Recommendation", "", f"**{report['recommendation'] or 'No promotion'}** — {report['recommendation_note']}", "", "Visual comparisons are in the `visuals/` directory. The JSON report contains all class IoUs, checkpoint and candidate hashes, uncertainty intervals, per-view component counts, runtime and peak memory.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--wed-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--study-dir", type=Path,
                        default=ROOT / "experiments/wed_segmentation_study")
    parser.add_argument("--baseline", type=Path,
                        default=ROOT / "experiments/wed_native_segmentation/model_wed_semantic_baseline.pt")
    parser.add_argument("--out-dir", type=Path,
                        default=ROOT / "experiments/wed_segmentation_study/dev_comparison")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    result = evaluate_study(manifest=args.manifest, wed_root=args.wed_root,
                            study_dir=args.study_dir,
                            frozen_checkpoint=args.baseline,
                            out_dir=args.out_dir, device_name=args.device)
    print(json.dumps({"recommendation": result["recommendation"],
                      "report": str(args.out_dir / "comparison_report.md")}, indent=2))


if __name__ == "__main__":
    main()
