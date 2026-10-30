"""Audit card-plane versus food-base-plane area on renderer ground truth.

Oracle camera/base-plane geometry is used only to diagnose plane mismatch; no
oracle quantity enters the serving estimator.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from config import load_anchor_config
from experiments.oracle_ablation.synthetic_card_position import (
    _food_area_from_homography,
    _render,
)
from experiments.oracle_ablation.synthetic_card_position_replication import POSITIONS
from experiments.oracle_ablation.synthetic_mask_spill import SCENES
from models.scale_anchor import estimate_anchor
from tests.synth.scene import VESSELS


OUTPUT = Path(__file__).with_name("audit_card_food_plane_height.jsonl")


def _world_plane_homography(scene: dict, plane_z_mm: float) -> np.ndarray:
    camera = scene["camera"]
    rotation = np.asarray(camera["R_wc"], dtype=np.float64)
    center = np.asarray(camera["C"], dtype=np.float64).reshape(3)
    intrinsics = np.asarray(camera["K"], dtype=np.float64)
    translation = rotation @ np.array([0.0, 0.0, plane_z_mm]) - rotation @ center
    return intrinsics @ np.column_stack((rotation[:, 0], rotation[:, 1], translation))


def run() -> list[dict]:
    anchor_cfg = load_anchor_config()
    records = []
    for spec in SCENES:
        positions = []
        analytic_area_cm2 = float(np.pi * float(spec["radius_mm"]) ** 2 / 100.0)
        scene_cfg = _render(spec, POSITIONS[0])["cfg"]
        vessel = scene_cfg["vessel"]
        vessel_floor = vessel["floor"] if isinstance(vessel, dict) else VESSELS[vessel]["floor"]
        food_base_mm = float(scene_cfg["food"].get("base_mm", vessel_floor))
        for position in POSITIONS:
            scene = _render(spec, position)
            mask = np.asarray(scene["mask_food"], dtype=bool)
            anchor = estimate_anchor(
                scene["image_bgr"], config=anchor_cfg,
                exif={"focal_mm": None, "focal_length_35mm": None,
                      "subject_distance_cm": None, "digital_zoom": None,
                      "camera": None},
            )
            if anchor["label"] != "measured" or anchor["H"] is None:
                positions.append({
                    "card_center_mm": list(position),
                    "measurement_status": "unavailable",
                    "anchor_label": anchor["label"],
                    "anchor_reason": anchor["reason"],
                })
                continue

            area_detected_card = _food_area_from_homography(mask, np.asarray(anchor["H"]))
            H_card_truth = _world_plane_homography(scene, 0.6)
            H_food_base_truth = _world_plane_homography(scene, food_base_mm)
            area_card_truth = _food_area_from_homography(mask, H_card_truth)
            area_food_base_truth = _food_area_from_homography(mask, H_food_base_truth)
            positions.append({
                "card_center_mm": list(position),
                "measurement_status": "measured",
                "food_base_height_mm": food_base_mm,
                "analytic_footprint_area_cm2": analytic_area_cm2,
                "detected_card_plane_area_cm2": area_detected_card,
                "renderer_card_plane_area_cm2": area_card_truth,
                "renderer_food_base_plane_area_cm2": area_food_base_truth,
                "detected_card_plane_abs_error_pct": 100.0 * abs(area_detected_card - analytic_area_cm2) / analytic_area_cm2,
                "renderer_card_plane_abs_error_pct": 100.0 * abs(area_card_truth - analytic_area_cm2) / analytic_area_cm2,
                "renderer_food_base_plane_abs_error_pct": 100.0 * abs(area_food_base_truth - analytic_area_cm2) / analytic_area_cm2,
                "anchor_reason": anchor["reason"],
            })

        measured = [x for x in positions if x["measurement_status"] == "measured"]
        records.append({
            "scene": spec["name"],
            "analytic_footprint_area_cm2": analytic_area_cm2,
            "food_base_height_mm": food_base_mm,
            "detected_card_plane_mean_abs_error_pct": (
                float(np.mean([x["detected_card_plane_abs_error_pct"] for x in measured]))
                if measured else None
            ),
            "renderer_card_plane_mean_abs_error_pct": (
                float(np.mean([x["renderer_card_plane_abs_error_pct"] for x in measured]))
                if measured else None
            ),
            "renderer_food_base_plane_mean_abs_error_pct": (
                float(np.mean([x["renderer_food_base_plane_abs_error_pct"] for x in measured]))
                if measured else None
            ),
            "positions": positions,
        })

    OUTPUT.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    return records


def main() -> None:
    records = run()
    detected_errors = [r["detected_card_plane_mean_abs_error_pct"] for r in records]
    base_errors = [r["renderer_food_base_plane_mean_abs_error_pct"] for r in records]
    all_measured = all(
        sum(p["measurement_status"] == "measured" for p in r["positions"]) == len(POSITIONS)
        for r in records
    )
    relative_reduction = (
        1.0 - float(np.mean(base_errors)) / float(np.mean(detected_errors))
        if all(x is not None for x in detected_errors + base_errors)
        and float(np.mean(detected_errors)) > 0 else None
    )
    scenes_with_base_error_le_2 = sum(x is not None and x <= 2.0 for x in base_errors)
    criterion_met = (
        all_measured and relative_reduction is not None
        and relative_reduction >= 0.50 and scenes_with_base_error_le_2 >= 5
    )
    print(f"scenes={len(records)} positions_per_scene={len(POSITIONS)}")
    print(f"all_18_positions_measured={all_measured}")
    print(f"mean_abs_area_error_pct_detected_card_plane={float(np.mean(detected_errors)):.6f}")
    print(f"mean_abs_area_error_pct_renderer_card_plane={float(np.mean([r['renderer_card_plane_mean_abs_error_pct'] for r in records])):.6f}")
    print(f"mean_abs_area_error_pct_renderer_food_base_plane={float(np.mean(base_errors)):.6f}")
    print(f"food_base_plane_error_reduction_pct={100.0 * relative_reduction:.6f}")
    print(f"scenes_food_base_error_le_2pct={scenes_with_base_error_le_2}/{len(records)}")
    print(f"preregistered_criterion_met={criterion_met}")
    for record in records:
        print(
            f"{record['scene']}: base_height={record['food_base_height_mm']:.2f}mm "
            f"detected_card_mean_abs_error={record['detected_card_plane_mean_abs_error_pct']}% "
            f"renderer_card_mean_abs_error={record['renderer_card_plane_mean_abs_error_pct']}% "
            f"renderer_food_base_mean_abs_error={record['renderer_food_base_plane_mean_abs_error_pct']}%"
        )
        for item in record["positions"]:
            if item["measurement_status"] != "measured":
                print(f"  card={item['card_center_mm']} unavailable: {item['anchor_reason']}")
                continue
            print(
                f"  card={item['card_center_mm']} analytic_area={item['analytic_footprint_area_cm2']:.4f}cm2 "
                f"detected_card={item['detected_card_plane_area_cm2']:.4f}cm2 "
                f"renderer_card={item['renderer_card_plane_area_cm2']:.4f}cm2 "
                f"renderer_food_base={item['renderer_food_base_plane_area_cm2']:.4f}cm2"
            )
    print(f"raw_jsonl={OUTPUT}")


if __name__ == "__main__":
    main()
