"""Measure the production monocular depth model against analytic renderer GT.

This is a renderer-only baseline probe, not a food corpus. It writes a
quantitative report and no training examples or model checkpoints.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.depth import (MonocularDepth, calibrate_depth_scale,
                          normalized_intrinsics_to_pixel_K)
from config import load_anchor_config
from models.model_revisions import MOGE2_REVISION
from nutrisense_synth.evaluation import group_bootstrap_ci, metric_depth_metrics
from nutrisense_synth.parameters import load_class_registry, observed_portion_ranges
from nutrisense_synth.scene import build_class_scene, render_card_pair


def _horizontal_fov_x(K: np.ndarray, width: int) -> float:
    """Compute MoGe's horizontal FOV input from pixel camera intrinsics."""
    fx = float(np.asarray(K, dtype=np.float64)[0, 0])
    if not np.isfinite(fx) or fx <= 0 or width < 1:
        raise ValueError("camera intrinsics require positive finite fx and width")
    return float(np.degrees(2.0 * np.arctan(width / (2.0 * fx))))


def _metrics_by_region(records: list[dict], region: str | None = None) -> dict:
    selected = [row for row in records if region is None or row["region"] == region]
    if not selected:
        return {"n_scenes": 0, "metrics": {}}
    keys = ("mae_m", "rmse_m", "abs_rel", "silog_pct", "delta_1_25",
            "median_prediction_to_target_scale", "median_prediction_m",
            "median_target_m", "valid_prediction_fraction")
    metrics = {key: float(np.mean([row["metrics"][key] for row in selected]))
               for key in keys}
    grouped: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in selected:
        grouped[row["group"]]["abs_rel"].append(row["metrics"]["abs_rel"])
        grouped[row["group"]]["rmse_m"].append(row["metrics"]["rmse_m"])
    uncertainty = {
        key: group_bootstrap_ci({group: [float(np.mean(values[key]))
                                         for _ in [0]]
                                 for group, values in grouped.items()})
        for key in ("abs_rel", "rmse_m")
    }
    return {"n_scenes": len(selected), "group_count": len(grouped),
            "metrics": metrics, "uncertainty_group_bootstrap_95ci": uncertainty}


def evaluate(*, portion_levels: int = 3, class_limit: int | None = None,
             device: str | None = None) -> dict:
    if portion_levels < 1:
        raise ValueError("portion_levels must be positive")
    registry = load_class_registry()
    ranges = observed_portion_ranges()
    class_ids = sorted(registry)
    if class_limit is not None:
        if class_limit < 1:
            raise ValueError("class_limit must be positive")
        class_ids = class_ids[:class_limit]
    provider = MonocularDepth(device=device)
    object_names = {0: "table", 1: "vessel", 2: "card", 3: "food"}
    records: list[dict] = []
    marker_scales: list[float] = []
    digest = hashlib.sha256()
    start = time.time()
    scene_count = 0

    for class_id in class_ids:
        params = registry[class_id]
        if params.class_name not in ranges:
            raise ValueError(f"No WED TRAIN portion range for {params.class_name}")
        low, high = ranges[params.class_name]
        portions = np.linspace(low, high, portion_levels).tolist()
        for portion_index, grams in enumerate(portions):
            scene_seed = 730_000 + class_id * 100 + portion_index
            cfg = build_class_scene(class_id, params.class_name, float(grams),
                                    params.density_g_ml, seed=scene_seed,
                                    card_present=True, size=(640, 480))
            # The render pair holds all scene parameters fixed except card presence.
            scenes = render_card_pair(cfg)
            pair_group = f"class-{class_id:02d}-portion-{portion_index:02d}"
            for scene in scenes:
                image = scene["image_bgr"]
                target = np.asarray(scene["depth_m"], dtype=np.float32)
                object_ids = np.asarray(scene["obj_ids"], dtype=np.uint8)
                camera = scene.get("camera") or {}
                fov_x = _horizontal_fov_x(camera["K"], target.shape[1])
                depth_out = provider(image, fov_x=fov_x)
                predicted = np.asarray(depth_out["depth_m"], dtype=np.float32)
                if predicted.shape != target.shape:
                    raise ValueError(
                        f"MoGe output shape {predicted.shape} != renderer depth {target.shape}")
                card_present = bool(scene["cfg"]["anchor"]["card"])
                depth_K = normalized_intrinsics_to_pixel_K(
                    depth_out.get("intrinsics"), target.shape[1], target.shape[0])
                intrinsics_source = "moge" if depth_K is not None else "renderer_camera_fallback"
                if depth_K is None:
                    depth_K = camera["K"]
                if card_present:
                    marker_mm = float(load_anchor_config()["card"]["marker_mm"])
                    marker_anchor = {
                        "method": "card_aruco", "marker_mm": marker_mm,
                        "extras": {"marker_corners_px":
                                   np.asarray(scene["anchor_gt"][
                                       "marker_corners_px"]).tolist()}}
                    calibrated, scale, _source = calibrate_depth_scale(
                        predicted, marker_anchor, depth_K)
                    marker_scales.append(float(scale))
                else:
                    calibrated = None
                digest.update(image.tobytes())
                digest.update(target.tobytes())
                digest.update(object_ids.tobytes())
                digest.update(json.dumps(scene["cfg"], sort_keys=True,
                                         default=str).encode())
                region_masks = [("all_visible", np.ones(target.shape, dtype=bool))]
                region_masks.extend((name, object_ids == object_id)
                                    for object_id, name in object_names.items())
                for region, mask in region_masks:
                    if not mask.any():
                        continue
                    metrics = metric_depth_metrics(predicted, target, mask)
                    records.append({"group": pair_group, "class_id": class_id,
                                    "class_name": params.class_name,
                                    "portion_g": float(grams),
                                    "card_present": card_present,
                                    "intrinsics_source": intrinsics_source,
                                    "region": region, "metrics": metrics})
                    if calibrated is not None:
                        records.append({"group": pair_group,
                                        "class_id": class_id,
                                        "class_name": params.class_name,
                                        "portion_g": float(grams),
                                        "card_present": "card_calibrated",
                                        "intrinsics_source": intrinsics_source,
                                        "region": region,
                                        "metrics": metric_depth_metrics(
                                            calibrated, target, mask)})
                scene_count += 1
        if class_id % 5 == 0 or class_id == class_ids[-1]:
            print(f"depth baseline: class {class_id}/{class_ids[-1]} "
                  f"({scene_count} rendered views)", flush=True)

    by_card = {}
    for card_present, label in ((False, "no_card"), (True, "card"),
                                ("card_calibrated", "card_calibrated")):
        rows = [r for r in records if r["card_present"] == card_present]
        by_card[label] = {
            "all_visible": _metrics_by_region(rows, "all_visible"),
            "food": _metrics_by_region(rows, "food"),
            "vessel": _metrics_by_region(rows, "vessel"),
            "table": _metrics_by_region(rows, "table"),
            "card": _metrics_by_region(rows, "card"),
        }
    return {
        "feature": "real_pipeline_baseline",
        "created_at": datetime.now(UTC).isoformat(),
        "stage": "depth_geometry",
        "baseline_kind": "renderer_grounded_metric_depth",
        "ground_truth": "analytic_renderer_camera_z_metres",
        "model": {"id": MonocularDepth().model_id, "revision": MOGE2_REVISION,
                  "source_sha256": hashlib.sha256(
                      (ROOT / "engine/depth.py").read_bytes()
                      + (ROOT / "models/model_revisions.py").read_bytes()).hexdigest()},
        "configuration": {"renderer": "analytic-heightfield-v1",
                          "class_count": len(class_ids),
                          "portion_levels_per_class": portion_levels,
                          "portion_source": (
                              "minimum observed WED TRAIN mass per class"
                              if portion_levels == 1 else
                              "evenly spaced WED TRAIN observed min-to-max by class"),
                          "card_conditions": ["card", "no_card"],
                          "marker_calibration": "renderer-known marker corners and configured physical size",
                          "calibration_intrinsics": "MoGe predicted pixel K; renderer K fallback only when absent/invalid",
                          "camera_resolution": [640, 480],
                          "depth_fov": "exact renderer camera K",
                          "depth_device": device},
        "data_sha256": digest.hexdigest(),
        "groups": len(class_ids) * portion_levels,
        "rendered_views": scene_count,
        "metrics_by_condition": by_card,
        "marker_scale_factor_summary": {
            "n": len(marker_scales),
            "median": float(np.median(marker_scales)) if marker_scales else None,
            "p10": float(np.percentile(marker_scales, 10)) if marker_scales else None,
            "p90": float(np.percentile(marker_scales, 90)) if marker_scales else None,
        },
        "real_depth_accuracy_claim": False,
        "locked_accessed": False,
        "aruco_accessed": False,
        "elapsed_s": round(time.time() - start, 2),
        "record_count": len(records),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT /
                        "experiments/real_pipeline_baseline/renderer_metric_depth.json")
    parser.add_argument("--portion-levels", type=int, default=3)
    parser.add_argument("--class-limit", type=int, default=None,
                        help="development smoke run; omit for all 41 classes")
    parser.add_argument("--device", choices=("cuda", "cpu"), default=None)
    args = parser.parse_args()
    try:
        report = evaluate(portion_levels=args.portion_levels,
                          class_limit=args.class_limit, device=args.device)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        parser.error(str(exc))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"report": str(args.out), "views": report["rendered_views"],
                      "data_sha256": report["data_sha256"],
                      "no_card_abs_rel": report["metrics_by_condition"]["no_card"]["all_visible"]["metrics"].get("abs_rel")},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
