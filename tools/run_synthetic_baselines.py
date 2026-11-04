"""Evaluate clean WED DEV classifier/segmenter baselines and report readiness.

Classifier gallery examples come only from TRAIN physical groups outside the
fixed seed-42 DEV carve. Segmentation uses the WED DEV semantic masks as truth.
This command never reads LOCKED or ArUco image data and does not freeze an
incomplete all-stage baseline.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nutrisense_synth.evaluation import baseline_preflight, group_bootstrap_ci
from nutrisense_synth.parameters import (eligible_wed_train_rows,
                                         read_wed_train_manifest,
                                         wed_dev_group_ids,
                                         wed_group_id)


def _sha(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.as_posix().encode())
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def _crop(image: np.ndarray, mask: np.ndarray, class_id: int) -> np.ndarray | None:
    ys, xs = np.nonzero(mask == class_id)
    if not len(xs):
        return None
    return np.ascontiguousarray(image[ys.min():ys.max() + 1,
                                     xs.min():xs.max() + 1])


def _clean_gallery(rows: list[dict], root: Path, cap: int
                   ) -> tuple[np.ndarray, np.ndarray, list[Path], set[str]]:
    """Create deterministic, group-spread 41-class image embeddings."""
    from models.food_classifier import embed_image
    from nutrisense_synth.parameters import load_class_registry

    registry = load_class_registry()
    pools: dict[int, list[dict]] = defaultdict(list)
    for row in sorted(rows, key=lambda item: (wed_group_id(item), item["image"])):
        for dish in row["dishes"]:
            pools[int(dish["class_id"])].append(row)

    embeddings: list[np.ndarray] = []
    labels: list[int] = []
    source_paths: list[Path] = []
    source_groups: set[str] = set()
    for class_id in sorted(registry):
        candidates = pools.get(class_id, [])
        # Pick at most one view from each physical plate, spread deterministically.
        by_group: dict[str, dict] = {}
        for row in candidates:
            by_group.setdefault(wed_group_id(row), row)
        groups = sorted(by_group)
        n = min(cap, len(groups))
        selected = sorted({round(i * (len(groups) - 1) / max(n - 1, 1))
                           for i in range(n)})
        for index in selected:
            row = by_group[groups[index]]
            source_groups.add(groups[index])
            image_path, mask_path = root / row["image"], root / row["mask"]
            image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
            if image is None or mask is None:
                raise FileNotFoundError(f"Unable to read TRAIN source pair: {row['image']}")
            crop = _crop(image, mask, class_id)
            if crop is None:
                continue
            embeddings.append(embed_image(crop))
            labels.append(class_id)
            source_paths.extend((image_path, mask_path))
    if set(labels) != set(registry):
        raise RuntimeError(f"Clean TRAIN gallery does not cover all 41 classes: {sorted(set(registry) - set(labels))}")
    return (np.stack(embeddings), np.asarray(labels, dtype=np.int64),
            source_paths, source_groups)


def _classify_dev(rows: list[dict], root: Path, gallery: np.ndarray,
                  gallery_labels: np.ndarray) -> dict:
    from models.food_classifier import embed_image
    from nutrisense_synth.parameters import load_class_registry

    registry = load_class_registry()
    scores: list[dict] = []
    input_paths: list[Path] = []
    for row in rows:
        image_path, mask_path = root / row["image"], root / row["mask"]
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if image is None or mask is None:
            raise FileNotFoundError(f"Unable to read DEV source pair: {row['image']}")
        group = wed_group_id(row)
        for dish in row["dishes"]:
            class_id = int(dish["class_id"])
            crop = _crop(image, mask, class_id)
            if crop is None:
                continue
            query = embed_image(crop)
            similarities = gallery @ query
            by_class = {}
            for candidate in registry:
                vals = similarities[gallery_labels == candidate]
                if vals.size:
                    by_class[candidate] = float(np.sort(vals)[-min(3, vals.size):].mean())
            prediction = max(by_class, key=by_class.get)
            scores.append({"group": group, "target": class_id,
                           "prediction": prediction})
        input_paths.extend((image_path, mask_path))
    if not scores:
        raise RuntimeError("No WED DEV food regions were classified")

    classes = sorted(registry)
    per_class = {}
    f1s = []
    for class_id in classes:
        tp = sum(x["target"] == class_id and x["prediction"] == class_id for x in scores)
        fp = sum(x["target"] != class_id and x["prediction"] == class_id for x in scores)
        fn = sum(x["target"] == class_id and x["prediction"] != class_id for x in scores)
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
        f1s.append(f1)
        per_class[class_id] = {"name": registry[class_id].class_name,
                               "n": sum(x["target"] == class_id for x in scores),
                               "f1": f1}
    by_group: dict[str, list[float]] = defaultdict(list)
    for item in scores:
        by_group[item["group"]].append(float(item["target"] == item["prediction"]))
    group_means = {group: [float(np.mean(values))] for group, values in by_group.items()}
    y_true = np.asarray([x["target"] for x in scores])
    y_pred = np.asarray([x["prediction"] for x in scores])
    return {
        "stage": "classification",
        "metrics": {"top1_accuracy": float(np.mean(y_true == y_pred)),
                    "macro_f1": float(np.mean(f1s)), "n_food_regions": len(scores)},
        "uncertainty": {"group_bootstrap_95ci_top1": group_bootstrap_ci(group_means)},
        "group_count": len(by_group), "per_class": per_class,
        "data_sha256": _sha(list(set(input_paths))),
        "predictions": scores,
    }


def _segment_dev(rows: list[dict], root: Path) -> dict:
    from models.dish_segmenter import segment_items

    values: list[dict] = []
    input_paths: list[Path] = []
    failures = 0
    for row in rows:
        image_path, mask_path = root / row["image"], root / row["mask"]
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        labels = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if image is None or labels is None:
            raise FileNotFoundError(f"Unable to read DEV source pair: {row['image']}")
        truth = np.isin(labels, [int(d["class_id"]) for d in row["dishes"]])
        item_masks: list[np.ndarray] = []
        predicted_items: list[dict] = []
        detector_report: dict = {}
        try:
            detector_report = segment_items(image)
            predicted_items = detector_report["items"]
            item_masks = [np.asarray(item["mask"], dtype=bool)
                          for item in predicted_items]
            item_masks = [cv2.resize(item.astype(np.uint8),
                                     (truth.shape[1], truth.shape[0]),
                                     interpolation=cv2.INTER_NEAREST).astype(bool)
                          if item.shape != truth.shape else item
                          for item in item_masks]
            pred = np.logical_or.reduce(item_masks) if item_masks else np.zeros_like(truth)
        except Exception:
            failures += 1
            item_masks = []
            predicted_items = []
            pred = np.zeros_like(truth)
        intersection = int(np.count_nonzero(pred & truth))
        union = int(np.count_nonzero(pred | truth))
        denom = int(pred.sum() + truth.sum())
        per_dish_covered = 0
        per_dish_recalled = 0
        dish_iou_details = []
        for dish in row["dishes"]:
            dish_truth = labels == int(dish["class_id"])
            if not dish_truth.any():
                continue
            best_iou = 0.0
            best_gt_recall = 0.0
            for item_mask in item_masks:
                inter = int(np.count_nonzero(item_mask & dish_truth))
                uni = int(np.count_nonzero(item_mask | dish_truth))
                best_iou = max(best_iou, inter / uni if uni else 1.0)
                best_gt_recall = max(best_gt_recall,
                                     inter / int(dish_truth.sum()))
            per_dish_covered += int(best_iou >= 0.5)
            per_dish_recalled += int(best_gt_recall >= 0.5)
            dish_iou_details.append({"class_id": int(dish["class_id"]),
                                     "class_name": str(dish["name"]),
                                     "ground_truth_area_fraction": float(dish_truth.mean()),
                                     "best_item_iou": best_iou,
                                     "best_gt_area_recall": best_gt_recall})
        n_dishes = len(row["dishes"])
        values.append({"group": wed_group_id(row),
                       "iou": intersection / union if union else 1.0,
                       "dice": 2 * intersection / denom if denom else 1.0,
                       "item_coverage": per_dish_covered / n_dishes if n_dishes else 0.0,
                       "semantic_region_recall_at_gt_cover_0_5": (
                           per_dish_recalled / n_dishes if n_dishes else 0.0),
                       "predicted_items": len(predicted_items),
                       "seed_prompt_count": int(detector_report.get(
                           "seed_prompt_count", 0)),
                       "truncated_count": int(detector_report.get(
                           "truncated_count", 0)),
                       "predicted_item_area_fractions": [float(m.mean()) for m in item_masks],
                       "ground_truth_dish_count": n_dishes,
                       "ground_truth_union_area_fraction": float(truth.mean()),
                       "per_dish_iou": dish_iou_details})
        input_paths.extend((image_path, mask_path))
    by_group_iou: dict[str, list[float]] = defaultdict(list)
    by_group_dice: dict[str, list[float]] = defaultdict(list)
    by_group_coverage: dict[str, list[float]] = defaultdict(list)
    by_group_recall: dict[str, list[float]] = defaultdict(list)
    for item in values:
        by_group_iou[item["group"]].append(item["iou"])
        by_group_dice[item["group"]].append(item["dice"])
        by_group_coverage[item["group"]].append(item["item_coverage"])
        by_group_recall[item["group"]].append(
            item["semantic_region_recall_at_gt_cover_0_5"])
    ci_iou = group_bootstrap_ci({k: [float(np.mean(v))] for k, v in by_group_iou.items()})
    ci_dice = group_bootstrap_ci({k: [float(np.mean(v))] for k, v in by_group_dice.items()})
    return {
        "stage": "segmentation",
        "metrics": {"mean_iou": float(np.mean([x["iou"] for x in values])),
                    "mean_dice": float(np.mean([x["dice"] for x in values])),
                    "item_coverage_at_iou_0_5": float(np.mean(
                        [x["item_coverage"] for x in values])),
                    "semantic_region_recall_at_gt_cover_0_5": float(np.mean(
                        [x["semantic_region_recall_at_gt_cover_0_5"]
                         for x in values])),
                    "mean_predicted_items": float(np.mean(
                        [x["predicted_items"] for x in values])),
                    "view_coverage": 1 - failures / len(values),
                    "n_views": len(values), "failed_views": failures},
        "uncertainty": {"group_bootstrap_95ci_iou": ci_iou,
                        "group_bootstrap_95ci_dice": ci_dice,
                        "group_bootstrap_95ci_item_coverage": group_bootstrap_ci(
                            {k: [float(np.mean(v))] for k, v in by_group_coverage.items()}),
                        "group_bootstrap_95ci_semantic_region_recall": group_bootstrap_ci(
                            {k: [float(np.mean(v))] for k, v in by_group_recall.items()})},
        "group_count": len(by_group_iou), "data_sha256": _sha(list(set(input_paths))),
        "per_view": values,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "data/reports/synthetic_baseline_preflight.json")
    parser.add_argument("--stages", default="all", choices=("all",))
    parser.add_argument("--tier", default="dev", choices=("dev",))
    parser.add_argument("--wed-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--gallery-cap", type=int, default=24,
                        help="maximum clean TRAIN gallery crops per class")
    args = parser.parse_args()
    if args.gallery_cap < 1:
        parser.error("--gallery-cap must be positive")
    report = baseline_preflight()
    all_train_rows = read_wed_train_manifest(args.manifest)
    dev_groups = wed_dev_group_ids(all_train_rows)
    train_rows = eligible_wed_train_rows(all_train_rows)
    dev_rows = [row for row in all_train_rows if wed_group_id(row) in dev_groups]
    start = time.time()
    gallery, gallery_labels, gallery_paths, gallery_groups = _clean_gallery(
        train_rows, args.wed_root, args.gallery_cap)
    classifier = _classify_dev(dev_rows, args.wed_root, gallery, gallery_labels)
    from models.registry import unload
    unload("siglip2")  # Free classifier weights before loading the SAM2 segmenter.
    segmentation = _segment_dev(dev_rows, args.wed_root)
    classifier["model_sha256"] = _sha([ROOT / "models/food_classifier.py",
                                       ROOT / "models/model_revisions.py"])
    classifier["gallery_data_sha256"] = _sha(list(set(gallery_paths + [args.manifest])))
    classifier["gallery_source_group_count"] = len(gallery_groups)
    classifier["gallery_class_counts"] = {
        str(class_id): int((gallery_labels == class_id).sum())
        for class_id in sorted(set(gallery_labels.tolist()))}
    classifier["configuration"] = {"gallery_cap_per_class": args.gallery_cap,
                                    "dev_carve_seed": 42,
                                    "dev_carve_fraction": 0.10,
                                    "top_k": 3,
                                    "gallery_source_split": "wed_train_excluding_dev_carve"}
    classifier["split_sha256"] = hashlib.sha256(
        "\n".join(sorted(wed_group_id(row) for row in dev_rows)).encode()).hexdigest()
    segmentation["model_sha256"] = _sha([ROOT / "models/dish_segmenter.py",
                                          ROOT / "models/model_revisions.py"])
    segmentation["split_sha256"] = classifier["split_sha256"]
    report["stages"]["classification"].update(classifier)
    report["stages"]["classification"]["status"] = "measured_reference_not_frozen"
    report["stages"]["classification"]["limitation"] = (
        "Uses isolated ground-truth food crops and a clean TRAIN-only gallery; "
        "this is a component baseline, not end-to-end classification.")
    report["stages"]["segmentation"].update(segmentation)
    report["stages"]["segmentation"]["status"] = "measured_reference_not_frozen"
    report["stages"]["segmentation"]["limitation"] = (
        "Uses deployed multi-item masks; label identity is not inferred by SAM2, "
        "so item coverage is the fraction of GT dish regions matched at IoU >= 0.5.")
    report["model_evaluation"] = "WED DEV only; LOCKED and ArUco inputs not opened"
    report["elapsed_s"] = round(time.time() - start, 2)
    report["frozen"] = False
    report["candidate_generation_allowed"] = False
    report["reason"] = ("Measured component baselines do not constitute a complete "
                        "five-stage freeze; depth/geometry and end-to-end remain gated.")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(args.out), "frozen": report["frozen"],
                      "candidate_generation_allowed": report["candidate_generation_allowed"],
                      "stage_status": {key: value["status"] for key, value in report["stages"].items()}},
                     indent=2))
    return 0 if report["frozen"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
