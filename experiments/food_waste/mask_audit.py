"""Pairwise SAM item-mask diagnostics for a saved Food Waste JSONL run."""
from __future__ import annotations

import json
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import torch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RAW = HERE / "raw.jsonl"
OUT = HERE / "mask_audit.jsonl"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    union = int(np.logical_or(a, b).sum())
    return float(np.logical_and(a, b).sum() / union) if union else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=RAW)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; refusing CPU fallback")
    from models import registry
    from models.dish_segmenter import segment_food, segment_items

    rows = [json.loads(line) for line in args.input.read_text().splitlines()
            if line.strip()]
    run_metadata = next((row for row in rows if row.get("event") == "run_metadata"), {})
    rows = [row for row in rows if row.get("event") == "image_result"
            and len(row.get("items") or []) > 1]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    header = {"event": "run_metadata", "dataset": "AI-ServicesBB/food-waste-dataset",
              "dataset_revision": "f008d0c7b41ea4408b66bd1b7bb9ecd58b70349d",
              "split_read": run_metadata.get("split_read", "unknown"),
              "official_test_evaluation_only": bool(
                  run_metadata.get("official_test_evaluation_only", False)),
              "device": torch.cuda.get_device_name(0), "torch": torch.__version__,
              "cuda_version": torch.version.cuda, "images": len(rows),
              "dedupe_iou_threshold": 0.70, "overlap_flag_iou_threshold": 0.50}
    with args.output.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(header, sort_keys=True) + "\n")
    print(json.dumps({"event": "mask_audit_started", "images": len(rows),
                      "device": torch.cuda.get_device_name(0)}), flush=True)
    for index, row in enumerate(rows, start=1):
        path = Path(row["path"])
        image = cv2.imread(str(path))
        if image is None:
            raise RuntimeError(f"unreadable image: {path}")
        top = np.asarray(segment_food(image)["mask"], dtype=bool)
        found = segment_items(image).get("items") or []
        if len(found) != len(row["items"]):
            record = {
                "event": "image_mask_result",
                "receipt_id": row["receipt_id"],
                "source_row_idx": row["source_row_idx"],
                "predicted_total_g": row.get("predicted_total_g"),
                "output_item_count": len(row["items"]),
                "replayed_mask_count": len(found),
                "mapping_error": "item count differs on deterministic segmentation replay",
            }
        else:
            masks = [np.asarray(item["mask"], dtype=bool) for item in found]
            grams = [
                (float((item.get("portion") or {})["grams"])
                 if (item.get("portion") or {}).get("grams") is not None else None)
                for item in row["items"]
            ]
            pair_rows = []
            overlap_indices: set[int] = set()
            drop_indices: set[int] = set()
            for i in range(len(masks)):
                for j in range(i + 1, len(masks)):
                    value = _iou(masks[i], masks[j])
                    pair_rows.append({"i": i, "j": j, "iou": value,
                                      "dedupe_pass_band_0.50_to_0.70": 0.50 <= value < 0.70})
                    if value > 0.50:
                        overlap_indices.update((i, j))
                        if grams[i] is None or grams[j] is None:
                            drop_indices.add(j)
                        else:
                            drop_indices.add(j if grams[i] >= grams[j] else i)
            top_area = int(top.sum())
            areas = [int(mask.sum()) for mask in masks]
            exceeds = {i for i, area in enumerate(areas)
                       if area > top_area}
            flagged = overlap_indices | exceeds
            flagged_known_grams = sum(grams[i] for i in flagged
                                      if grams[i] is not None)
            flagged_unknown_count = sum(grams[i] is None for i in flagged)
            flagged_grams = (None if flagged_unknown_count else flagged_known_grams)
            dropped_grams = [grams[i] for i in range(len(grams))
                             if i not in drop_indices]
            dropped_total = (sum(dropped_grams)
                             if all(value is not None for value in dropped_grams)
                             else None)
            record = {
                "event": "image_mask_result",
                "receipt_id": row["receipt_id"],
                "source_row_idx": row["source_row_idx"],
                "predicted_total_g": row.get("predicted_total_g"),
                "ground_truth_food_g": row.get("ground_truth_food_g"),
                "top_food_area_px": top_area,
                "item_mask_areas_px": areas,
                "sum_item_mask_area_px": sum(areas),
                "item_area_sum_to_top_area_ratio": sum(areas) / top_area if top_area else None,
                "item_area_exceeds_top_indices": sorted(exceeds),
                "pairwise_iou": pair_rows,
                "pairs_in_0.50_to_0.70_band": sum(
                    pair["dedupe_pass_band_0.50_to_0.70"] for pair in pair_rows),
                "overlap_flagged_indices_iou_gt_0.50": sorted(overlap_indices),
                "all_flagged_indices": sorted(flagged),
                "flagged_items_grams": flagged_grams,
                "flagged_known_grams": flagged_known_grams,
                "flagged_unknown_item_count": flagged_unknown_count,
                "flagged_items_pct_of_total": (
                    100.0 * flagged_grams / float(row["predicted_total_g"])
                    if flagged_grams is not None and row.get("predicted_total_g") else None),
                "duplicate_drop_indices_hypothetical": sorted(drop_indices),
                "hypothetical_total_after_duplicate_drop_g": dropped_total,
                "hypothetical_delta_g": (
                    dropped_total - float(row["predicted_total_g"])
                    if dropped_total is not None and row.get("predicted_total_g") is not None
                    else None),
                "item_grams": grams,
                "mapping_error": None,
            }
        with args.output.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        print(json.dumps({
            "event": "image_complete",
            "index": index,
            "receipt_id": record["receipt_id"],
            "source_row_idx": record["source_row_idx"],
            "pairs_in_0.50_to_0.70_band": record.get("pairs_in_0.50_to_0.70_band"),
            "flagged_indices": record.get("all_flagged_indices"),
            "mapping_error": record.get("mapping_error"),
        }, sort_keys=True), flush=True)
    registry.unload()
    torch.cuda.synchronize()
    print(json.dumps({"event": "mask_audit_complete", "raw_jsonl": str(args.output)}), flush=True)


if __name__ == "__main__":
    main()
