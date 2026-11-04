"""Isolate physical and prior effects in renderer-grounded geometry mass.

Uses one controlled chutney recipe and analytic GT depth/mask/anchor. It writes
diagnostics only; it does not build a model-training corpus.
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

from config import load_params
from models.portion_estimator import estimate_portion
from nutrisense_synth.parameters import load_class_registry
from nutrisense_synth.scene import build_class_scene, render_scene


def _scene(cls, *, grams=9.0, density=None, radius=70.0, kappa=0.55,
           seed=8813, card=True):
    rho = cls.density_g_ml if density is None else float(density)
    cfg = build_class_scene(cls.class_id, cls.class_name, grams, rho,
                            seed=seed, card_present=card,
                            size=(640, 480))
    cfg["food"]["radius_mm"] = float(radius)
    cfg["food"]["kappa"] = float(kappa)
    cfg["food"]["density_g_ml"] = rho
    return render_scene(cfg)


def _gt_anchor(scene):
    truth = scene["anchor_gt"]
    cm_px = float(truth["cm_per_px"])
    return {"method": "card_aruco", "label": "measured",
            "cm_per_px": cm_px,
            "interval": (cm_px * .999, cm_px * 1.001),
            "tilt_deg": float(truth["tilt_deg"]), "marker_mm": 60.0,
            "extras": {"marker_corners_px":
                       np.asarray(truth["marker_corners_px"]).tolist()}}


def _run(scene, cls, *, anchor=None, depth_factor=1.0, base_method="ring",
         base_prior_mm=None, density_g_ml=None):
    rho = cls.density_g_ml if density_g_ml is None else float(density_g_ml)
    dish = {"components": {cls.class_name: {
        "share": 1.0, "density_g_ml": rho}}}
    params = load_params()
    if base_prior_mm is not None:
        params["base_prior_height_mm"]["value"] = float(base_prior_mm)
    try:
        portion = estimate_portion(
            scene["image_bgr"], scene["mask_food"],
            np.asarray(scene["depth_m"], dtype=np.float64) * depth_factor,
            anchor or _gt_anchor(scene), {"K": scene["camera"]["K"]}, dish,
            params=params, cfg={"base_method": base_method})
        return {"grams": portion["grams"], "volume_ml": portion["volume_ml"],
                "area_cm2": portion["area_cm2"],
                "mean_h_mm": portion["mean_h_mm"],
                "density_eff": portion["density_eff"],
                "sigma_grams_rel": portion["sigma_grams_rel"],
                "base_method": portion["base_method"],
                "flags": portion["flags"]}
    except (ValueError, KeyError) as exc:
        return {"abstained": True, "reason": str(exc)}


def evaluate() -> dict:
    cls = next(value for value in load_class_registry().values()
               if value.class_name.casefold() == "chutney")
    baseline_scene = _scene(cls)
    truth = {"mass_g": 9.0,
             "volume_ml": 9.0 / cls.density_g_ml,
             "density_g_ml": cls.density_g_ml}
    baseline = _run(baseline_scene, cls)
    records = [{"experiment": "baseline_gt_depth_card_ring",
                "variable": "none", "value": 1.0, "truth": truth,
                "result": baseline}]

    for factor in (0.5, 0.75, 1.25, 1.5):
        records.append({"experiment": "metric_depth_scale",
                        "variable": "depth_multiplier", "value": factor,
                        "truth": truth,
                        "result": _run(baseline_scene, cls,
                                       depth_factor=factor)})
    for method in ("table_prior",):
        for height_mm in (0.0, 8.0, 25.0):
            records.append({"experiment": "base_plane_assumption",
                            "variable": "base_prior_height_mm",
                            "value": height_mm, "truth": truth,
                            "result": _run(baseline_scene, cls,
                                           base_method=method,
                                           base_prior_mm=height_mm)})
    for kappa in (0.35, 0.55, 0.75):
        scene = _scene(cls, kappa=kappa, seed=8813)
        records.append({"experiment": "food_height_profile",
                        "variable": "kappa", "value": kappa,
                        "truth": truth, "result": _run(scene, cls)})
    for radius_mm in (55.0, 70.0, 85.0):
        scene = _scene(cls, radius=radius_mm, seed=8813)
        records.append({"experiment": "food_footprint_shape",
                        "variable": "radius_mm", "value": radius_mm,
                        "truth": truth, "result": _run(scene, cls)})
    for density in (0.7, cls.density_g_ml, 1.3):
        scene = _scene(cls, density=density, seed=8813)
        records.append({"experiment": "density_conversion",
                        "variable": "density_g_ml", "value": density,
                        "truth": {"mass_g": 9.0,
                                  "volume_ml": 9.0 / density,
                                  "density_g_ml": density},
                        "result": _run(scene, cls,
                                       density_g_ml=density)})

    no_card_scene = _scene(cls, card=False)
    prior = {"method": "prior", "label": "prior", "cm_per_px": None,
             "interval": None, "H": None, "tilt_deg": None,
             "reason": "controlled no-card diagnostic", "extras": {}}
    records.append({"experiment": "no_card_size_prior_with_gt_depth",
                    "variable": "scale_source", "value": "size_prior",
                    "truth": truth,
                    "result": _run(no_card_scene, cls, anchor=prior)})

    digest = hashlib.sha256(json.dumps(records, sort_keys=True,
                                       default=str).encode()).hexdigest()
    return {"created_at": datetime.now(UTC).isoformat(),
            "stage": "depth_geometry_failure_analysis",
            "case": "renderer-generated 9 g chutney; analytic GT depth/mask",
            "scene_seed": 8813,
            "marker": "ID 7, 60 mm, renderer GT corners for card geometry",
            "class_density_source": "WED TRAIN class registry assumption",
            "records": records, "data_sha256": digest,
            "training_examples_written": False,
            "locked_accessed": False, "aruco_accessed": False,
            "wed_test_accessed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT /
                        "experiments/real_pipeline_baseline/renderer_geometry_sensitivity.json")
    args = parser.parse_args()
    report = evaluate()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"report": str(args.out), "case": report["case"],
                      "experiments": len(report["records"]),
                      "baseline": report["records"][0]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
