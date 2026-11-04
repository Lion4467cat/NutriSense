"""One-at-a-time geometry sensitivity trace for the WED DEV 9 g chutney ROI.

Reads only the deterministic DEV carve from WED TRAIN rows. It does not train
models, use LOCKED/ArUco images, or write example data outside its JSON report.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import load_anchor_config, load_params
from engine.depth import MonocularDepth
from geo import camera_matrix
from models.portion_estimator import estimate_portion
from models.scale_anchor import prior_anchor
from nutrisense_synth.parameters import (read_wed_train_manifest,
                                         wed_dev_group_ids, wed_group_id)


def _sha(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.as_posix().encode())
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()


def _estimate(image: np.ndarray, mask: np.ndarray, depth: np.ndarray,
              anchor: dict, K: np.ndarray, params: dict,
              base_method: str = "table_prior",
              density_g_ml: float = 1.0) -> dict:
    dish = {"components": {"chutney": {"share": 1.0,
                                         "density_g_ml": density_g_ml}}}
    out = estimate_portion(image, mask, depth, anchor, {"K": K}, dish,
                           params=params, cfg={"base_method": base_method})
    return {key: out[key] for key in (
        "grams", "volume_ml", "density_eff", "mean_h_mm", "area_cm2",
        "cm_per_px", "base_method", "base_sigma_mm", "flags")}


def evaluate(*, manifest: Path, wed_root: Path, device: str = "cuda") -> dict:
    rows = read_wed_train_manifest(manifest)
    dev_groups = wed_dev_group_ids(rows)
    row = next((candidate for candidate in rows
                if wed_group_id(candidate) in dev_groups
                and wed_group_id(candidate) == "20250512_set14"
                and any(str(dish["name"]).casefold() == "chutney"
                        and float(dish["weight_g"]) == 9.0
                        for dish in candidate["dishes"])), None)
    if row is None:
        raise ValueError("The WED DEV 9 g chutney case was not found")

    image_path, mask_path = wed_root / row["image"], wed_root / row["mask"]
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    labels = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if image is None or labels is None:
        raise FileNotFoundError("Unable to decode the WED DEV chutney pair")
    dish = next(dish for dish in row["dishes"]
                if str(dish["name"]).casefold() == "chutney"
                and float(dish["weight_g"]) == 9.0)
    mask = labels == int(dish["class_id"])
    H, W = mask.shape
    anchor_cfg = load_anchor_config()
    cam = anchor_cfg["camera"]
    K = camera_matrix(cam["focal_length_fallback_mm"],
                      cam.get("sensor_width_mm", 6.17), W, H)
    fov_x = float(np.degrees(2.0 * np.arctan(W / (2.0 * K[0, 0]))))
    depth_out = MonocularDepth(device=device)(image, fov_x=fov_x)
    depth = np.asarray(depth_out["depth_m"], dtype=np.float64)
    anchor = prior_anchor("WED DEV sensitivity trace; no card", anchor_cfg)
    base_params = load_params()
    baseline = _estimate(image, mask, depth, anchor, K, base_params)

    depth_scale = []
    for factor in (0.25, 0.5, 0.75, 1.0, 1.5, 2.0):
        try:
            depth_scale.append({"factor": factor,
                                **_estimate(image, mask, depth * factor,
                                            anchor, K, base_params)})
        except Exception as exc:
            depth_scale.append({"factor": factor, "error": str(exc)})

    base_height = []
    for height_mm in (0.0, 8.0, 25.0, 45.0):
        params = copy.deepcopy(base_params)
        params["base_prior_height_mm"]["value"] = height_mm
        try:
            base_height.append({"assumed_base_height_mm": height_mm,
                                **_estimate(image, mask, depth, anchor, K,
                                            params)})
        except Exception as exc:
            base_height.append({"assumed_base_height_mm": height_mm,
                                "error": str(exc)})

    size_prior = []
    for diameter_mm in (30.0, 60.0, 100.0, 170.0, 210.0):
        params = copy.deepcopy(base_params)
        params["size_prior_food_diameter_mm"]["value"] = diameter_mm
        try:
            size_prior.append({"assumed_food_diameter_mm": diameter_mm,
                               **_estimate(image, mask, depth, anchor, K,
                                           params)})
        except Exception as exc:
            size_prior.append({"assumed_food_diameter_mm": diameter_mm,
                               "error": str(exc)})

    base_methods = []
    for method in ("table_prior", "ring"):
        try:
            base_methods.append({"base_method": method,
                                 **_estimate(image, mask, depth, anchor, K,
                                             base_params, method)})
        except Exception as exc:
            base_methods.append({"base_method": method, "error": str(exc)})

    density = []
    for density_g_ml in (0.7, 1.0, 1.3):
        try:
            density.append({"density_g_ml": density_g_ml,
                            **_estimate(image, mask, depth, anchor, K,
                                        base_params,
                                        density_g_ml=density_g_ml)})
        except Exception as exc:
            density.append({"density_g_ml": density_g_ml,
                            "error": str(exc)})

    formula_counterfactuals = [
        {"area_multiplier": area_factor, "height_multiplier": height_factor,
         "grams": baseline["grams"] * area_factor * height_factor}
        for area_factor, height_factor in ((1, 1), (0.5, 1), (0.25, 1),
                                            (1, 0.5), (1, 0.25),
                                            (0.5, 0.5), (0.25, 0.25))]
    return {
        "stage": "geometry_sensitivity",
        "case": {"group": wed_group_id(row), "image": row["image"],
                 "dish": dish["name"], "ground_truth_mass_g": 9.0,
                 "mask_pixels": int(mask.sum()), "view_shape": [H, W]},
        "depth": {"model": depth_out.get("model"), "fov_x_deg": fov_x,
                  "median_m": float(np.median(depth[mask])),
                  "p10_m": float(np.percentile(depth[mask], 10)),
                  "p90_m": float(np.percentile(depth[mask], 90)),
                  "source_sha256": hashlib.sha256(
                      (ROOT / "engine/depth.py").read_bytes()).hexdigest()},
        "baseline": baseline,
        "sensitivity": {"depth_scale": depth_scale,
                        "base_prior_height": base_height,
                        "base_method": base_methods,
                        "size_prior_diameter": size_prior,
                        "density": density,
                        "formula_area_height_counterfactuals": formula_counterfactuals},
        "data_sha256": _sha([manifest, image_path, mask_path]),
        "locked_accessed": False,
        "aruco_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path,
                        default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--wed-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--out", type=Path, default=ROOT /
                        "experiments/synthetic_food/chutney_geometry_sensitivity.json")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    report = evaluate(manifest=args.manifest, wed_root=args.wed_root,
                      device=args.device)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"report": str(args.out), "case": report["case"],
                      "baseline": report["baseline"],
                      "locked_accessed": False, "aruco_accessed": False},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
