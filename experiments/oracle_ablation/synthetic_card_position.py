"""Measure global measured-scale sensitivity to card position on synthetic scenes.

The food scene, exact food mask, metric depth, and camera are held fixed while
the card is rendered at three positions. A homography-only area measurement is
reported as an experiment; serving code is untouched.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from config import load_anchor_config, load_params
from experiments.oracle_ablation.synthetic_mask_spill import SCENES
from models.portion_estimator import estimate_portion
from models.scale_anchor import estimate_anchor
from tests.synth.scene import render_scene


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name("synthetic_card_position.jsonl")
POSITIONS = [(0.0, -170.0), (170.0, 15.0), (0.0, 180.0)]


def _food_area_from_homography(mask: np.ndarray, H: np.ndarray) -> float:
    """Map exact image-mask contours through H^-1 and sum planar area in cm²."""
    contours, hierarchy = cv2.findContours(mask.astype(np.uint8), cv2.RETR_CCOMP,
                                           cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise RuntimeError("exact food mask has no contours")
    inverse = np.linalg.inv(np.asarray(H, dtype=np.float64))
    area_mm2 = 0.0
    for idx, contour in enumerate(contours):
        points = contour.reshape(-1, 2).astype(np.float64).reshape(-1, 1, 2)
        mapped = cv2.perspectiveTransform(points, inverse).reshape(-1, 2)
        signed_area = cv2.contourArea(mapped.astype(np.float32))
        # RETR_CCOMP marks child contours as holes.
        parent = hierarchy[0, idx, 3]
        area_mm2 += -signed_area if parent >= 0 else signed_area
    return area_mm2 / 100.0


def _measure(scene: dict, mask: np.ndarray, anchor: dict, params: dict) -> dict:
    density = float(scene["cfg"]["food"]["density_g_ml"])
    dish = {"components": {"synthetic_food": {
        "share": 1.0, "density_g_ml": density,
    }}}
    return estimate_portion(
        scene["image_bgr"], mask, scene["depth_m"], anchor,
        {"K": scene["camera"]["K"]}, dish, params=params,
    )


def _planted_anchor(scene: dict) -> dict:
    planted = scene["anchor_gt"]
    cm_per_px = float(planted["cm_per_px"])
    return {
        "label": "measured",
        "cm_per_px": cm_per_px,
        "interval": (cm_per_px * 0.99, cm_per_px * 1.01),
        "tilt_deg": float(planted["tilt_deg"]),
    }


def _render(spec: dict, position: tuple[float, float]) -> dict:
    return render_scene({
        "vessel": spec["vessel"],
        "seed": spec["seed"],
        "camera": spec["camera"],
        "anchor": {"card": True, "card_center": position,
                   "card_angle_deg": 10.0},
        "food": {
            "radius_mm": spec["radius_mm"],
            "grams": spec["grams"],
            "density_g_ml": 0.95,
            "kappa": spec["kappa"],
            "layout": "whole",
            "components": [{"name": "synthetic_food", "material": "rice",
                            "share_g": spec["grams"]}],
        },
    })


def run() -> list[dict]:
    params = load_params()
    anchor_cfg = load_anchor_config()
    records = []
    for spec in SCENES:
        scene_records = []
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
                scene_records.append({
                    "card_center_mm": list(position),
                    "measurement_status": "unavailable",
                    "anchor_label": anchor["label"],
                    "anchor_reason": anchor["reason"],
                })
                continue
            result = _measure(scene, mask, _planted_anchor(scene), params)
            detected_result = _measure(scene, mask, anchor, params)
            area_h = _food_area_from_homography(mask, np.asarray(anchor["H"]))
            scale_baseline_area = float(result["area_cm2"])
            homography_grams = float(result["grams"]) * area_h / scale_baseline_area
            truth = float(scene["grams_gt_total"])
            scene_records.append({
                "card_center_mm": list(position),
                "measurement_status": "measured",
                "food_mask_pixels": int(mask.sum()),
                "anchor_cm_per_px": float(anchor["cm_per_px"]),
                "detected_marker_side_px": float(anchor["extras"]["marker_side_px"]),
                "planted_marker_side_px": float(scene["anchor_gt"]["marker_side_px"]),
                "detected_marker_corners_px": anchor["extras"]["marker_corners_px"],
                "planted_marker_corners_px": np.asarray(
                    scene["anchor_gt"]["marker_corners_px"], dtype=float,
                ).tolist(),
                "mean_abs_corner_delta_px": float(np.mean(np.abs(
                    np.asarray(anchor["extras"]["marker_corners_px"], dtype=float)
                    - np.asarray(scene["anchor_gt"]["marker_corners_px"], dtype=float)
                ))),
                "anchor_tilt_deg": anchor["tilt_deg"],
                "anchor_reason": anchor["reason"],
                "detected_global_scale": {
                    "grams": float(detected_result["grams"]),
                    "cm_per_px": float(anchor["cm_per_px"]),
                    "signed_error_pct": 100.0 * (float(detected_result["grams"]) - truth) / truth,
                },
                "anchor_H": np.asarray(anchor["H"]).tolist(),
                "global_scale": {
                    "grams": float(result["grams"]),
                    "area_cm2": scale_baseline_area,
                    "signed_error_pct": 100.0 * (float(result["grams"]) - truth) / truth,
                },
                "homography_area_cm2": area_h,
                "homography_area_scaled_grams": homography_grams,
                "homography_signed_error_pct": 100.0 * (homography_grams - truth) / truth,
                "base_method": result["base_method"],
                "flags": result["flags"],
            })
        measured = [x for x in scene_records if x["measurement_status"] == "measured"]
        base_values = [x["global_scale"]["grams"] for x in measured]
        candidate_values = [x["homography_area_scaled_grams"] for x in measured]
        median_base = float(np.median(base_values)) if base_values else None
        median_candidate = float(np.median(candidate_values)) if candidate_values else None
        records.append({
            "scene": spec["name"],
            "truth_g": float(spec["grams"]),
            "food_mask_depth_invariant": True,
            "positions": scene_records,
            "measured_position_count": len(measured),
            "global_spread_pct_of_median": (
                100.0 * (max(base_values) - min(base_values)) / median_base
                if len(base_values) == len(POSITIONS) else None
            ),
            "homography_spread_pct_of_median": (
                100.0 * (max(candidate_values) - min(candidate_values)) / median_candidate
                if len(candidate_values) == len(POSITIONS) else None
            ),
        })
    OUTPUT.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    return records


def main() -> None:
    records = run()
    sensitive = [r for r in records if r["global_spread_pct_of_median"] is not None
                 and r["global_spread_pct_of_median"] >= 5.0]
    corrected = [r for r in sensitive if r["homography_spread_pct_of_median"] is not None
                 and r["homography_spread_pct_of_median"] <= 2.0]
    assessable = sum(r["global_spread_pct_of_median"] is not None for r in records)
    print(f"scenes={len(records)} card_positions_per_scene={len(POSITIONS)}")
    print(f"food_mask_and_depth_invariant={all(r['food_mask_depth_invariant'] for r in records)}")
    print(f"scenes_with_all_positions_measured={assessable}/{len(records)}")
    print(f"global_spread_ge_5pct={len(sensitive)}/{len(records)}")
    print(f"homography_spread_le_2pct_among_sensitive={len(corrected)}/{len(sensitive)}")
    print(f"preregistered_criterion_met={len(sensitive) >= 4 and len(corrected) >= 4}")
    for record in records:
        print(
            f"{record['scene']}: truth={record['truth_g']:.2f}g "
            f"measured_positions={record['measured_position_count']}/{len(POSITIONS)} "
            f"global_spread={record['global_spread_pct_of_median']} "
            f"homography_spread={record['homography_spread_pct_of_median']}"
        )
        for item in record["positions"]:
            if item["measurement_status"] != "measured":
                print(
                    f"  card={item['card_center_mm']} unavailable: "
                    f"{item['anchor_reason']}"
                )
                continue
            print(
                f"  card={item['card_center_mm']} scale={item['global_scale']['grams']:.2f}g "
                f"({item['global_scale']['signed_error_pct']:+.2f}%) "
                f"H_area={item['homography_area_scaled_grams']:.2f}g "
                f"({item['homography_signed_error_pct']:+.2f}%) "
                f"marker_corner_delta={item['mean_abs_corner_delta_px']:.2f}px "
                f"base={item['base_method']} flags={item['flags']}"
            )
    print(f"raw_jsonl={OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
