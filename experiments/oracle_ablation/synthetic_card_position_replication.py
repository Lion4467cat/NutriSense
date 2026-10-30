"""Preregistered three-position replication of synthetic card-scale sensitivity.

Uses fixed, outside-vessel card locations from ledger 025. Serving code and
production settings remain untouched.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from config import load_anchor_config, load_params
from experiments.oracle_ablation.synthetic_card_position import (
    _food_area_from_homography,
    _measure,
    _planted_anchor,
    _render,
)
from experiments.oracle_ablation.synthetic_mask_spill import SCENES
from models.scale_anchor import estimate_anchor


OUTPUT = Path(__file__).with_name("synthetic_card_position_replication.jsonl")
POSITIONS = [(170.0, -80.0), (170.0, 15.0), (170.0, 100.0)]
MAX_CORNER_ERROR_PX = 3.0


def run() -> list[dict]:
    params = load_params()
    anchor_cfg = load_anchor_config()
    records = []
    for spec in SCENES:
        position_records = []
        invariant_mask = None
        invariant_depth = None
        for position in POSITIONS:
            scene = _render(spec, position)
            mask = np.asarray(scene["mask_food"], dtype=bool)
            if invariant_mask is None:
                invariant_mask = mask.copy()
                invariant_depth = scene["depth_m"].copy()
            elif not (np.array_equal(mask, invariant_mask)
                      and np.array_equal(scene["depth_m"][mask], invariant_depth[mask])):
                raise RuntimeError(f"food mask/depth changed for {spec['name']}")

            anchor = estimate_anchor(
                scene["image_bgr"], config=anchor_cfg,
                exif={"focal_mm": None, "focal_length_35mm": None,
                      "subject_distance_cm": None, "digital_zoom": None,
                      "camera": None},
            )
            if anchor["label"] != "measured" or anchor["H"] is None:
                position_records.append({
                    "card_center_mm": list(position),
                    "measurement_status": "unavailable",
                    "anchor_label": anchor["label"],
                    "anchor_reason": anchor["reason"],
                })
                continue

            planted = _measure(scene, mask, _planted_anchor(scene), params)
            detected = _measure(scene, mask, anchor, params)
            area_h = _food_area_from_homography(mask, np.asarray(anchor["H"]))
            planted_area = float(planted["area_cm2"])
            homography_grams = float(planted["grams"]) * area_h / planted_area
            truth = float(scene["grams_gt_total"])
            detected_corners = np.asarray(anchor["extras"]["marker_corners_px"], dtype=float)
            planted_corners = np.asarray(scene["anchor_gt"]["marker_corners_px"], dtype=float)
            corner_error = float(np.mean(np.abs(detected_corners - planted_corners)))
            position_records.append({
                "card_center_mm": list(position),
                "measurement_status": "measured",
                "food_mask_pixels": int(mask.sum()),
                "planted_cm_per_px": float(scene["anchor_gt"]["cm_per_px"]),
                "detected_cm_per_px": float(anchor["cm_per_px"]),
                "detected_marker_side_px": float(anchor["extras"]["marker_side_px"]),
                "planted_marker_side_px": float(scene["anchor_gt"]["marker_side_px"]),
                "detected_marker_corners_px": detected_corners.tolist(),
                "planted_marker_corners_px": planted_corners.tolist(),
                "mean_absolute_corner_error_px": corner_error,
                "anchor_H": np.asarray(anchor["H"]).tolist(),
                "anchor_reason": anchor["reason"],
                "detected_global_scale": {
                    "grams": float(detected["grams"]),
                    "signed_error_pct": 100.0 * (float(detected["grams"]) - truth) / truth,
                },
                "planted_global_scale": {
                    "grams": float(planted["grams"]),
                    "area_cm2": planted_area,
                    "signed_error_pct": 100.0 * (float(planted["grams"]) - truth) / truth,
                },
                "homography_area_cm2": area_h,
                "homography_area_scaled_grams": homography_grams,
                "homography_signed_error_pct": 100.0 * (homography_grams - truth) / truth,
                "base_method": planted["base_method"],
                "flags": planted["flags"],
            })

        measured = [r for r in position_records if r["measurement_status"] == "measured"]
        global_values = [r["planted_global_scale"]["grams"] for r in measured]
        homography_values = [r["homography_area_scaled_grams"] for r in measured]
        global_median = float(np.median(global_values)) if len(global_values) == len(POSITIONS) else None
        homography_median = float(np.median(homography_values)) if len(homography_values) == len(POSITIONS) else None
        records.append({
            "scene": spec["name"],
            "truth_g": float(spec["grams"]),
            "food_mask_and_food_depth_invariant": True,
            "measured_position_count": len(measured),
            "global_spread_pct_of_median": (
                100.0 * (max(global_values) - min(global_values)) / global_median
                if global_median is not None else None
            ),
            "homography_spread_pct_of_median": (
                100.0 * (max(homography_values) - min(homography_values)) / homography_median
                if homography_median is not None else None
            ),
            "positions": position_records,
        })

    OUTPUT.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    return records


def main() -> None:
    records = run()
    all_positions_measured = all(r["measured_position_count"] == len(POSITIONS) for r in records)
    all_corner_errors_ok = all(
        item.get("mean_absolute_corner_error_px", float("inf")) <= MAX_CORNER_ERROR_PX
        for record in records for item in record["positions"]
    ) and all_positions_measured
    assessable = all_positions_measured and all_corner_errors_ok
    sensitive = [
        r for r in records if r["global_spread_pct_of_median"] is not None
        and r["global_spread_pct_of_median"] >= 5.0
    ]
    corrected = [
        r for r in sensitive if r["homography_spread_pct_of_median"] is not None
        and r["homography_spread_pct_of_median"] <= 2.0
    ]
    criterion_met = assessable and len(sensitive) >= 4 and len(corrected) >= 4
    print(f"scenes={len(records)} fixed_positions={POSITIONS}")
    print(f"food_mask_and_food_depth_invariant={all(r['food_mask_and_food_depth_invariant'] for r in records)}")
    print(f"all_18_positions_measured={all_positions_measured}")
    print(f"all_mean_corner_errors_le_{MAX_CORNER_ERROR_PX:g}px={all_corner_errors_ok}")
    print(f"assessable={assessable}")
    print(f"global_spread_ge_5pct={len(sensitive)}/{len(records)}")
    print(f"homography_spread_le_2pct_among_sensitive={len(corrected)}/{len(sensitive)}")
    print(f"preregistered_criterion_met={criterion_met}")
    for record in records:
        print(
            f"{record['scene']}: truth={record['truth_g']:.2f}g "
            f"measured_positions={record['measured_position_count']}/{len(POSITIONS)} "
            f"global_spread_pct={record['global_spread_pct_of_median']} "
            f"homography_spread_pct={record['homography_spread_pct_of_median']}"
        )
        for item in record["positions"]:
            if item["measurement_status"] != "measured":
                print(f"  card={item['card_center_mm']} unavailable: {item['anchor_reason']}")
                continue
            print(
                f"  card={item['card_center_mm']} global={item['planted_global_scale']['grams']:.2f}g "
                f"({item['planted_global_scale']['signed_error_pct']:+.2f}%) "
                f"detected_global={item['detected_global_scale']['grams']:.2f}g "
                f"H_area={item['homography_area_scaled_grams']:.2f}g "
                f"({item['homography_signed_error_pct']:+.2f}%) "
                f"corner_error={item['mean_absolute_corner_error_px']:.2f}px"
            )
    print(f"raw_jsonl={OUTPUT}")


if __name__ == "__main__":
    main()
