"""Run the current production pipeline on original WED DEV images.

The run ends at net food-mass predictions. It uses a clean TRAIN-only
classifier gallery, the product segmenter/depth/weight components, and the
fixed seed-42 DEV plate carve. LOCKED and ArUco image files are never read.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
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

from engine.depth import MonocularDepth
from config import load_wed_dishes
from models.food_classifier import MODEL_ID, classify_dish
from models.model_revisions import MOGE2_REVISION, SAM2_REVISION, SIGLIP2_REVISION
from models.weight_head import WeightHead
from nutrisense_synth.e2e import (compare_regions_to_semantic_mask,
                                  extract_food_mass_g, summarize_end_to_end,
                                  summarize_segmentation)
from nutrisense_synth.evaluation import sha256_file
from nutrisense_synth.parameters import (read_wed_train_manifest,
                                         wed_dev_group_ids, wed_group_id)
from tools.run_synthetic_baselines import _clean_gallery


def _sha(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        digest.update(path.as_posix().encode())
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def _gallery_payload(embeddings: np.ndarray, labels: np.ndarray,
                     index_map_path: Path) -> dict:
    name_map = {int(key): str(value) for key, value in
                json.loads(index_map_path.read_text(encoding="utf-8")).items()
                if str(value).lower() != "background"}
    return {"emb": embeddings, "labels": np.asarray(
        [name_map[int(class_id)] for class_id in labels], dtype=str),
        "model": MODEL_ID}


def evaluate(*, manifest: Path, wed_root: Path, gallery_cap: int = 24,
             limit: int | None = None, n_mc: int = 64,
             device: str = "cuda") -> dict:
    import torch
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable to this Python runtime")
    train_rows = read_wed_train_manifest(manifest)
    dev_groups = wed_dev_group_ids(train_rows)
    dev_rows = [row for row in train_rows if wed_group_id(row) in dev_groups]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        dev_rows = dev_rows[:limit]
    eligible_train = [row for row in train_rows if wed_group_id(row) not in dev_groups]

    embeddings, numeric_labels, gallery_paths, gallery_groups = _clean_gallery(
        eligible_train, wed_root, gallery_cap)
    gallery = _gallery_payload(embeddings, numeric_labels,
                               ROOT / "data/wed/index_map.json")
    from models.dish_segmenter import segment_food, segment_items
    depth = MonocularDepth(device=device)
    weight_checkpoint = ROOT / "data/weight_head.pt"
    weight_head = WeightHead.load(weight_checkpoint, device=device)
    from engine.pipeline import analyze

    def classifier(image):
        return classify_dish(image, gallery=gallery)

    serving_map = load_wed_dishes().get("serving") or {}

    def canonical_serving(raw_name):
        return (serving_map.get(raw_name) or {}).get("dish", raw_name)

    deps = {"classify": classifier, "segment": segment_food,
            "segment_items": segment_items, "depth": depth,
            "weight_head": weight_head}
    file_paths = [manifest, weight_checkpoint]
    rows_out = []
    start = time.time()
    for index, row in enumerate(dev_rows, start=1):
        image_path = wed_root / row["image"]
        mask_path = wed_root / row["mask"]
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        label_mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise FileNotFoundError(f"Unable to decode WED DEV image {row['image']}")
        if label_mask is None:
            raise FileNotFoundError(f"Unable to decode WED DEV mask {row['mask']}")
        gt_mass = float(sum(float(dish["weight_g"]) for dish in row["dishes"]))
        gt_classes = [int(dish["class_id"]) for dish in row["dishes"]]
        detector_error = None
        try:
            detector_output = segment_items(image)
        except Exception as exc:
            detector_output = {"items": [], "strategy": "detector_failed",
                               "candidate_count": 0, "truncated_count": 0}
            detector_error = f"{type(exc).__name__}: {exc}"
        item_masks = [np.asarray(item["mask"], dtype=bool)
                      for item in detector_output.get("items", [])]
        segmentation_metrics = compare_regions_to_semantic_mask(
            label_mask, gt_classes, item_masks)
        deps["segment_items"] = lambda _image, result=detector_output: result
        try:
            # Pipeline input gates require a known school day/band even in
            # General mode; these fixed context values do not affect grams.
            wire = analyze(image, day="mon", band="1-5", exif=None, deps=deps,
                           n_mc=n_mc, seed=42 + index, mode="general")
            predicted_mass = extract_food_mass_g(wire)
            items = wire.get("items") if isinstance(wire.get("items"), list) else []
            if not items and wire.get("portion") and predicted_mass is not None:
                items = [{"portion": wire.get("portion"),
                          "classification": wire.get("classification")}]
            predicted_classes = [item.get("classification", {}).get("dish")
                                 for item in items
                                 if isinstance(item, dict)]
            expected_classes = [canonical_serving(str(dish["name"]))
                                for dish in row["dishes"]]
            canonical_predictions = [canonical_serving(name)
                                     for name in predicted_classes
                                     if name is not None]
            complete_items = (
                len(items) == len(gt_classes)
                and all(item.get("portion") is not None
                        and (item.get("classification") or {}).get("dish") is not None
                        for item in items)
                and Counter(canonical_predictions) == Counter(expected_classes)
            )
            error = None if predicted_mass is None else predicted_mass - gt_mass
            critical_failure = (predicted_mass is None or not complete_items
                                or bool(wire.get("failures")))
            rows_out.append({
                "group": wed_group_id(row), "image": row["image"],
                "ground_truth_mass_g": gt_mass,
                "predicted_mass_g": predicted_mass,
                "error_g": error,
                "ground_truth_components": len(gt_classes),
                "predicted_components": len(items),
                "ground_truth_class_ids": gt_classes,
                "predicted_classes": predicted_classes,
                "expected_serving_classes": expected_classes,
                "canonical_predicted_classes": canonical_predictions,
                "class_multiset_match": (
                    Counter(canonical_predictions) == Counter(expected_classes)),
                "complete_items": bool(complete_items),
                "critical_failure": bool(critical_failure),
                "verdict": wire.get("verdict"),
                "grams_source": (wire.get("portion") or {}).get("grams_source"),
                "degradations": wire.get("degradations") or [],
                "failure_count": len(wire.get("failures") or []),
                "failures": wire.get("failures") or [],
                "reasons": wire.get("reasons") or [],
                "classification": wire.get("classification"),
                "segmentation": wire.get("segmentation"),
                "anchor": wire.get("anchor"),
                "detector_error": detector_error,
                "detector_strategy": detector_output.get("strategy"),
                "detector_candidate_count": int(
                    detector_output.get("candidate_count") or 0),
                "detector_seed_prompts": int(
                    detector_output.get("seed_prompt_count") or 0),
                "segmentation_metrics": segmentation_metrics,
                "predicted_item_diagnostics": [
                    {"dish": (item.get("classification") or {}).get("dish"),
                     "confidence": (item.get("classification") or {}).get("confidence"),
                     "match_score": (item.get("classification") or {}).get("match_score"),
                     "sam_score": item.get("sam_score"),
                     "area_frac": item.get("area_frac"),
                     "grams": (item.get("portion") or {}).get("grams")}
                    for item in items if isinstance(item, dict)],
            })
        except Exception as exc:
            rows_out.append({
                "group": wed_group_id(row), "image": row["image"],
                "ground_truth_mass_g": gt_mass, "predicted_mass_g": None,
                "error_g": None, "ground_truth_components": len(gt_classes),
                "predicted_components": 0, "ground_truth_class_ids": gt_classes,
                "predicted_classes": [], "complete_items": False,
                "expected_serving_classes": [canonical_serving(str(dish["name"]))
                                             for dish in row["dishes"]],
                "canonical_predicted_classes": [],
                "class_multiset_match": False,
                "critical_failure": True, "verdict": "runner_exception",
                "grams_source": None, "degradations": [],
                "failure_count": 1, "exception_type": type(exc).__name__,
                "exception": str(exc),
                "detector_error": detector_error,
                "detector_strategy": detector_output.get("strategy"),
                "detector_candidate_count": int(
                    detector_output.get("candidate_count") or 0),
                "detector_seed_prompts": int(
                    detector_output.get("seed_prompt_count") or 0),
                "segmentation_metrics": segmentation_metrics,
                "predicted_item_diagnostics": [],
            })
        file_paths.extend((image_path, mask_path))
        if index % 5 == 0 or index == len(dev_rows):
            print(f"end-to-end baseline: {index}/{len(dev_rows)} DEV views "
                  f"({time.time() - start:.0f}s)", flush=True)

    report = {
        "feature": "009-synthetic-training-data",
        "created_at": datetime.now(UTC).isoformat(),
        "stage": "end_to_end",
        "tier": "dev",
        "split": "fixed seed-42 10% carve from WED TRAIN physical groups",
        "split_sha256": hashlib.sha256(
            "\n".join(sorted(dev_groups)).encode()).hexdigest(),
        "model_revisions": {"classifier": SIGLIP2_REVISION,
                            "segmenter": SAM2_REVISION,
                            "depth": MOGE2_REVISION},
        "model_sha256": {
            "classifier_definition": _sha([ROOT / "models/food_classifier.py",
                                            ROOT / "models/model_revisions.py"]),
            "segmenter_definition": _sha([ROOT / "models/dish_segmenter.py",
                                           ROOT / "models/model_revisions.py"]),
            "weight_checkpoint": sha256_file(weight_checkpoint),
            "weight_definition": _sha([ROOT / "models/weight_head.py"]),
            "depth_definition": _sha([ROOT / "engine/depth.py"]),
        },
        "data_sha256": _sha(file_paths),
        "classifier_gallery_sha256": _sha(gallery_paths + [manifest]),
        "classifier_gallery_source_groups": len(gallery_groups),
        "configuration": {"classifier_gallery_cap_per_class": gallery_cap,
                          "portion_estimation": "current production pipeline",
                          "pipeline_mode": "general",
                          "fixed_pipeline_context": {"day": "mon", "band": "1-5",
                                                      "mass_independent": True},
                          "device": device, "n_mc": n_mc,
                          "seed_base": 42, "limit": limit,
                          "food_mass_semantics": "net food mass; tare excluded"},
        "metrics": summarize_end_to_end(rows_out),
        "segmentation_metrics": summarize_segmentation([
            {"group": item["group"], **item["segmentation_metrics"]}
            for item in rows_out]),
        "per_view": rows_out,
        "elapsed_s": round(time.time() - start, 2),
        "locked_accessed": False,
        "aruco_accessed": False,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--wed-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "experiments/synthetic_food/e2e_dev_baseline.json")
    parser.add_argument("--gallery-cap", type=int, default=24)
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke run only; omit for the complete DEV carve")
    parser.add_argument("--n-mc", type=int, default=64)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    try:
        report = evaluate(manifest=args.manifest, wed_root=args.wed_root,
                          gallery_cap=args.gallery_cap, limit=args.limit,
                          n_mc=args.n_mc, device=args.device)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        parser.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"report": str(args.out), "metrics": report["metrics"],
                      "locked_accessed": report["locked_accessed"],
                      "aruco_accessed": report["aruco_accessed"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
