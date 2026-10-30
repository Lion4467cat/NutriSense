"""Summarize the opt-in ArUco mask and geometry capture (read-only)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "aruco_mask_capture.jsonl"


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    union = int(np.logical_or(a, b).sum())
    return float(np.logical_and(a, b).sum() / union) if union else 0.0


def _load_rows() -> list[dict]:
    return [json.loads(line) for line in RAW.read_text().splitlines()
            if json.loads(line).get("event") == "image_result"
            and json.loads(line).get("mode") == "default"]


def main() -> None:
    rows = _load_rows()
    print(f"image_rows={len(rows)}")
    pair_band_total = 0
    item_total = visual_proxy_inside = visual_proxy_outside = visual_proxy_mixed = 0
    crop_food = crop_mixed = crop_context = 0
    mask_inside60 = mask_mixed40_60 = mask_outside40 = 0
    for row in rows:
        path = Path(row["image"])
        result = row["result"]
        item_rows = result.get("items") or []
        artifact = row.get("mask_artifacts") or {}
        npz_path = Path(artifact["npz"])
        with np.load(npz_path) as z:
            top = z["top_mask"].astype(bool) if "top_mask" in z else None
            masks = [z[f"item_mask_{i}"].astype(bool)
                     for i in range(len(item_rows))
                     if f"item_mask_{i}" in z]
            heights = {k.removeprefix("item_height_mm_"): z[k].copy()
                       for k in z.files if k.startswith("item_height_mm_")}
        if len(masks) != len(item_rows):
            print(f"MASK_MAPPING_ERROR {path.name}: masks={len(masks)} rows={len(item_rows)}")
            continue
        pairs = []
        band_pairs = 0
        for i in range(len(masks)):
            for j in range(i + 1, len(masks)):
                value = _iou(masks[i], masks[j])
                pairs.append((i, j, value))
                if 0.50 <= value < 0.70:
                    band_pairs += 1
        pair_band_total += band_pairs
        print(f"\nIMAGE {row['plate']} | {path.name} | anchor={row['anchor_tier']} "
              f"| path={result.get('path_used')} | item_count={len(item_rows)} "
              f"| pairs_iou_0.50_to_0.70={band_pairs}")
        if not item_rows:
            cls = result.get("classification") or {}
            top2 = (artifact.get("classifier_calls") or [{}])[0].get("top2", [])
            print(f"  NO_PORTION_ITEMS classifier={cls.get('dish')} "
                  f"confidence={cls.get('confidence')} top2={top2}")
        for i, (item, mask) in enumerate(zip(item_rows, masks)):
            item_total += 1
            area = int(mask.sum())
            inside = (int(np.logical_and(mask, top).sum()) / area
                      if top is not None and area else None)
            if inside is None:
                visual_proxy_mixed += 1
            elif inside >= 0.5:
                visual_proxy_inside += 1
            else:
                visual_proxy_outside += 1
            if inside is None:
                pass
            elif inside >= 0.60:
                mask_inside60 += 1
            elif inside <= 0.40:
                mask_outside40 += 1
            else:
                mask_mixed40_60 += 1
            cls = item.get("classification") or {}
            portion = item.get("portion") or {}
            item_top2 = (artifact.get("item_classifier_top2") or [])
            top2 = item_top2[i] if i < len(item_top2) else None
            geom_rows = artifact.get("item_geometry_telemetry") or []
            geom = next((g for g in geom_rows if g.get("mask_index") == i), None)
            x0, y0, x1, y1 = item.get("bbox") or [0, 0, 0, 0]
            pad_x, pad_y = int((x1 - x0) * 0.10), int((y1 - y0) * 0.10)
            crop = top[max(0, y0 - pad_y):min(top.shape[0], y1 + pad_y),
                       max(0, x0 - pad_x):min(top.shape[1], x1 + pad_x)] if top is not None else np.zeros((0, 0), dtype=bool)
            crop_frac = float(crop.mean()) if crop.size else None
            if crop_frac is None:
                crop_mixed += 1
            elif crop_frac >= 0.60:
                crop_food += 1
            elif crop_frac <= 0.40:
                crop_context += 1
            else:
                crop_mixed += 1
            print("  ITEM %d label=%s grams=%s area_px=%d inside_top_fraction=%s "
                  "classifier_crop_top_mask_fraction=%s top2=%s geometry=%s" % (
                      i, cls.get("dish"), portion.get("grams"), area,
                      "n/a" if inside is None else f"{inside:.6f}",
                      "n/a" if crop_frac is None else f"{crop_frac:.6f}",
                      top2,
                      "n/a" if geom is None else json.dumps(geom, sort_keys=True)))
        for i, j, value in pairs:
            print(f"  PAIR {i}-{j} IoU={value:.8f}" +
                  (" PASS_DEDUP_THRESHOLD_BAND" if 0.50 <= value < 0.70 else ""))
        diag = row.get("mask_diagnostics") or {}
        print(f"  MASK_SUM_PX={diag.get('sum_item_mask_area_px')} "
              f"TOP_PX={diag.get('top_food_area_px')} "
              f"SUM_TO_TOP={diag.get('item_area_sum_to_top_ratio')}")

    print(f"\nTOTAL_ITEM_ROWS={item_total}")
    print(f"COMPUTED_ITEM_MASK_FRACTION_BANDS mostly_inside>=0.6:{mask_inside60} "
          f"mixed_0.4_to_0.6:{mask_mixed40_60} mostly_outside<=0.4:{mask_outside40}")
    print(f"COMPUTED_ITEM_MASK_FRACTION_COUNTS inside>=0.5:{visual_proxy_inside} "
          f"outside<0.5:{visual_proxy_outside} unavailable:{visual_proxy_mixed}")
    print(f"COMPUTED_CLASSIFIER_CROP_TOP_MASK_COUNTS food_dominant>=0.6:{crop_food} "
          f"mixed:0.4_to_0.6:{crop_mixed} context_dominant<=0.4:{crop_context}")
    print(f"TOTAL_PAIRS_IOU_0.50_TO_0.70={pair_band_total}")
    print("PLATE_AREA_METHOD=unavailable; see report for failed Hough/edge-contour trial")


if __name__ == "__main__":
    main()
