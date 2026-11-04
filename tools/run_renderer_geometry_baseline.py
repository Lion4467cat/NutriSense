"""Evaluate volume and mass geometry against analytic renderer ground truth.

This creates transient controlled validation scenes and writes only aggregate
metrics/metadata; it does not produce a training corpus or fit any models.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.portion_estimator import estimate_portion
from nutrisense_synth.parameters import (load_class_registry,
                                         observed_portion_ranges)
from nutrisense_synth.scene import build_class_scene, render_scene


def _gt_anchor(scene: dict) -> dict:
    truth = scene.get("anchor_gt")
    if truth is None:
        raise ValueError("renderer ground-truth anchor is missing")
    cm_px = float(truth["cm_per_px"])
    return {
        "method": "card_aruco", "label": "measured", "cm_per_px": cm_px,
        "interval": (cm_px * 0.999, cm_px * 1.001),
        "tilt_deg": float(truth["tilt_deg"]), "marker_mm": 60.0,
        "extras": {"marker_corners_px":
                   np.asarray(truth["marker_corners_px"]).tolist()},
    }


def _summary(records: list[dict], field: str) -> dict:
    values = np.asarray([row[field] for row in records], dtype=np.float64)
    return {"mean": float(values.mean()), "median": float(np.median(values)),
            "p90": float(np.percentile(values, 90)),
            "max": float(values.max())}


def evaluate(*, portion_levels: int = 3, size: tuple[int, int] = (640, 480)) -> dict:
    if portion_levels < 1:
        raise ValueError("portion_levels must be positive")
    registry = load_class_registry()
    ranges = observed_portion_ranges()
    records = []
    digest = hashlib.sha256()
    for class_id in sorted(registry):
        cls = registry[class_id]
        if cls.class_name not in ranges:
            raise ValueError(f"No WED TRAIN mass range for {cls.class_name}")
        low, high = ranges[cls.class_name]
        portions = np.linspace(low, high, portion_levels)
        for portion_index, grams_gt in enumerate(portions):
            seed = 810_000 + class_id * 100 + portion_index
            scene = render_scene(build_class_scene(
                class_id, cls.class_name, float(grams_gt), cls.density_g_ml,
                seed=seed, card_present=True, size=size))
            dish = {"components": {cls.class_name: {
                "share": 1.0, "density_g_ml": cls.density_g_ml}}}
            portion = estimate_portion(
                scene["image_bgr"], scene["mask_food"], scene["depth_m"],
                _gt_anchor(scene), {"K": scene["camera"]["K"]}, dish)
            volume_gt = float(grams_gt) / cls.density_g_ml
            sigma = float(portion["sigma_grams_rel"])
            log_sigma = float(np.sqrt(np.log1p(sigma * sigma)))
            log_mean = -0.5 * log_sigma * log_sigma
            lo_factor = float(np.exp(log_mean - 1.645 * log_sigma))
            hi_factor = float(np.exp(log_mean + 1.645 * log_sigma))
            row = {
                "class_id": class_id, "class_name": cls.class_name,
                "portion_index": portion_index, "seed": seed,
                "ground_truth_mass_g": float(grams_gt),
                "ground_truth_volume_ml": volume_gt,
                "density_g_ml": float(cls.density_g_ml),
                "estimated_mass_g": float(portion["grams"]),
                "estimated_volume_ml": float(portion["volume_ml"]),
                "mass_error_g": float(portion["grams"] - grams_gt),
                "mass_abs_error_g": float(abs(portion["grams"] - grams_gt)),
                "mass_abs_rel_error": float(abs(portion["grams"] - grams_gt)
                                             / grams_gt),
                "volume_abs_rel_error": float(abs(portion["volume_ml"]
                                                   - volume_gt) / volume_gt),
                "sigma_grams_rel": sigma,
                "interval_90_g": [float(portion["grams"] * lo_factor),
                                  float(portion["grams"] * hi_factor)],
                "interval_90_covers_truth": bool(
                    portion["grams"] * lo_factor <= grams_gt
                    <= portion["grams"] * hi_factor),
                "base_method": portion["base_method"],
                "flags": portion["flags"],
            }
            records.append(row)
            digest.update(json.dumps(row, sort_keys=True).encode())
            image = scene["image_bgr"]
            digest.update(image.tobytes())
            if class_id % 5 == 0 or class_id == max(registry):
                print(f"geometry baseline: class {class_id}/{max(registry)} "
                      f"({len(records)} scenes)", flush=True)

    errors = np.asarray([row["mass_error_g"] for row in records])
    return {
        "created_at": datetime.now(UTC).isoformat(),
        "stage": "depth_geometry_mass",
        "baseline_kind": "renderer_grounded_geometry_with_ground_truth_depth_and_anchor",
        "renderer": "analytic-heightfield-v1",
        "ground_truth": ["camera-z depth in metres", "marker corners and scale",
                         "food mask", "component mass and volume"],
        "scene_count": len(records),
        "class_count": len(registry),
        "portion_levels_per_class": portion_levels,
        "portion_source": "WED TRAIN observed per-class mass range",
        "scene_resolution": list(size),
        "summary": {
            "mass_mae_g": float(np.mean(np.abs(errors))),
            "mass_bias_g": float(np.mean(errors)),
            "mass_abs_relative_error": _summary(records, "mass_abs_rel_error"),
            "volume_abs_relative_error": _summary(records, "volume_abs_rel_error"),
            "nominal_90pct_interval_coverage": float(np.mean(
                [row["interval_90_covers_truth"] for row in records])),
            "base_method_counts": {
                method: sum(row["base_method"] == method for row in records)
                for method in sorted({row["base_method"] for row in records})},
            "flag_counts": {
                flag: sum(flag in row["flags"] for row in records)
                for flag in sorted({flag for row in records
                                    for flag in row["flags"]})},
        },
        "per_class": [
            {"class_id": class_id, "class_name": registry[class_id].class_name,
             "n": len(group), "mass_mae_g": float(np.mean(
                 [row["mass_abs_error_g"] for row in group])),
             "mass_bias_g": float(np.mean([row["mass_error_g"] for row in group])),
             "mass_mape": float(np.mean([row["mass_abs_rel_error"]
                                          for row in group])),
             "volume_mape": float(np.mean([row["volume_abs_rel_error"]
                                            for row in group]))}
            for class_id in sorted(registry)
            for group in [[row for row in records if row["class_id"] == class_id]]],
        "records": records,
        "data_sha256": digest.hexdigest(),
        "training_examples_written": False,
        "locked_accessed": False,
        "aruco_accessed": False,
        "wed_test_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--portion-levels", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT /
                        "experiments/real_pipeline_baseline/renderer_geometry.json")
    args = parser.parse_args()
    report = evaluate(portion_levels=args.portion_levels)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"report": str(args.out), "scenes": report["scene_count"],
                      "summary": report["summary"],
                      "data_sha256": report["data_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
