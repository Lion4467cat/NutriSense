"""S6: end-to-end analysis pipeline (lint -> anchor -> segment -> classify
-> depth -> portion -> MC -> verdict).

deps lets tests (and future alternate backends) override any stage:
  deps = {"segment": callable(image_bgr)->dict, "classify": ..., "depth": ...}
Depth callables return {"depth_m": (H,W) meters, ...}; the pipeline calibrates
monocular scale against a measured anchor automatically.
"""
from pathlib import Path

import numpy as np

from engine.compliance import assess
from engine.mc import sample_nutrients
from engine.depth import MonocularDepth, calibrate_depth_scale
from geo.pose import camera_matrix
from models.portion_estimator import estimate_portion, load_params
from models.scale_anchor import estimate_anchor, load_config as load_anchor_config

_MENU_PATH = Path(__file__).resolve().parents[1] / "data" / "menu.yaml"
_MENU_CACHE = None

_MIN_SIDE_PX = 1280  # protocol lint (note only; anchor tier handles marker size)

_default_depth = None


def load_menu():
    global _MENU_CACHE
    if _MENU_CACHE is None:
        import yaml
        with open(_MENU_PATH) as f:
            _MENU_CACHE = yaml.safe_load(f)
    return _MENU_CACHE


def _get_depth_provider():
    global _default_depth
    if _default_depth is None:
        _default_depth = MonocularDepth()
    return _default_depth


def _base_result(verdict, reasons=None, **kw):
    out = {
        "verdict": verdict,
        "reasons": reasons or [],
        "lint": None, "anchor": None, "segmentation": None,
        "classification": None, "dish": None, "portion": None,
        "nutrition": None, "coverage": None, "assumptions": [],
        "advisory": None, "model_versions": {}, "compliance": None,
    }
    out.update(kw)
    return out


def analyze(image_bgr, day, band, exif=None, deps=None, n_mc=4000, seed=1234,
            serving_style=None):
    """Run the full pipeline on one capture. Always returns a result dict
    with a top-level `verdict` (PASS | FAIL | BORDERLINE | cannot_verify |
    out_of_scope)."""
    from models.dish_segmenter import segment_food
    from models.food_classifier import classify_dish

    deps = deps or {}
    segment = deps.get("segment") or segment_food
    classify = deps.get("classify") or classify_dish
    depth_fn = deps.get("depth") or _get_depth_provider()
    exif = exif or {"focal_mm": None, "subject_distance_cm": None,
                    "digital_zoom": None, "camera": None}
    menu = load_menu()
    H, W = image_bgr.shape[:2]

    lint = {
        "digital_zoom": exif.get("digital_zoom"),
        "focal_mm": exif.get("focal_mm"),
        "min_side_px": int(min(H, W)),
        "resolution_ok": bool(min(H, W) >= _MIN_SIDE_PX),
        "notes": [],
    }
    if not lint["resolution_ok"]:
        lint["notes"].append(f"min side {min(H, W)} < {_MIN_SIDE_PX}px "
                             "(marker tier may fall back to prior)")

    # hard lint gate: digital zoom
    if lint["digital_zoom"] is not None and float(lint["digital_zoom"]) != 1.0:
        return _base_result(
            "cannot_verify",
            [f"digital zoom {lint['digital_zoom']} != 1.0 (protocol requires zoom==1)"],
            lint=lint)

    if day not in menu["days"]:
        return _base_result("cannot_verify", [f"unknown day {day!r}"], lint=lint)
    if band not in {"1-5", "6-8", "9-10"}:
        return _base_result("cannot_verify", [f"unknown class band {band!r}"], lint=lint)

    # S1 anchor
    anchor = estimate_anchor(image_bgr, exif=exif)

    cfg = load_anchor_config()
    cam = cfg["camera"]
    focal = exif.get("focal_mm") or cam["focal_length_fallback_mm"]
    K = camera_matrix(focal, cam.get("sensor_width_mm", 6.17), W, H)

    # S2 segment + classify
    try:
        seg = segment(image_bgr)
    except Exception as e:
        return _base_result("cannot_verify", [f"segmentation failed: {e}"],
                            lint=lint, anchor=_anchor_summary(anchor))
    mask = seg["mask"]

    cls = classify(image_bgr)
    classification = {
        "dish": cls.get("dish"), "confidence": cls.get("confidence"),
        "method": cls.get("method"), "match_score": cls.get("match_score"),
        "reason": cls.get("reason"),
    }
    if cls.get("dish") is None:
        return _base_result(
            "cannot_verify",
            [f"dish unrecognized: {cls.get('reason')}"],
            lint=lint, anchor=_anchor_summary(anchor),
            segmentation=_seg_summary(seg), classification=classification)

    dish_key = cls["dish"]
    dish = menu["dishes"][dish_key]
    dish_info = {"id": dish_key, "display_name": dish.get("display_name"),
                 "day": day, "band": band, "serving_style": serving_style,
                 "on_day": (not dish.get("days")) or day in dish.get("days", []),
                 "nutrition_source": dish.get("nutrition_source")}
    if dish.get("status") == "out_of_scope" or dish.get("nutrition_source") == "out_of_scope":
        return _base_result("out_of_scope",
                            ["dish is out of scope (not portion-scored)"],
                            lint=lint, anchor=_anchor_summary(anchor),
                            segmentation=_seg_summary(seg),
                            classification=classification, dish=dish_info)

    # S3 depth + portion
    try:
        depth_out = depth_fn(image_bgr)
        depth_m = np.asarray(depth_out["depth_m"], dtype=np.float64)
        scale_factor, scale_source = 1.0, "none"
        if anchor.get("label") == "measured":
            depth_m, scale_factor, scale_source = calibrate_depth_scale(depth_m, anchor, K)
        portion = estimate_portion(image_bgr, mask, depth_m, anchor, {"K": K}, dish)
    except Exception as e:
        return _base_result("cannot_verify", [f"portion estimation failed: {e}"],
                            lint=lint, anchor=_anchor_summary(anchor),
                            segmentation=_seg_summary(seg),
                            classification=classification, dish=dish_info)

    # S4 MC
    mc = sample_nutrients(portion, dish, band, n=n_mc, seed=seed)

    # S5 verdict
    verdict = assess(mc, portion, dish, band, anchor.get("label", "prior"),
                     lint=lint, day=day)

    anchor_info = _anchor_summary(anchor)
    anchor_info["depth_scale_factor"] = round(float(scale_factor), 4)
    anchor_info["depth_scale_source"] = scale_source

    return {
        "verdict": verdict["verdict"],
        "reasons": verdict["reasons"],
        "lint": lint,
        "anchor": anchor_info,
        "segmentation": _seg_summary(seg),
        "classification": classification,
        "dish": dish_info,
        "portion": {
            "grams": round(portion["grams"], 1),
            "volume_ml": round(portion["volume_ml"], 1),
            "density_eff": round(portion["density_eff"], 3),
            "components_g": {k: round(v, 1) for k, v in portion["components_g"].items()},
            "base_method": portion["base_method"],
            "scale_tier": portion["scale_tier"],
            "mean_h_mm": round(portion["mean_h_mm"], 2),
            "area_cm2": round(portion["area_cm2"], 1),
            "sigma_grams_rel": round(portion["sigma_grams_rel"], 4),
            "sigma_rel": {k: round(v, 4) for k, v in portion["sigma_rel"].items()},
            "flags": portion["flags"],
        },
        "nutrition": {
            "kcal": mc["kcal"], "protein_g": mc["protein_g"],
            "grams": mc["grams"],
            "n": mc["n"], "seed": mc["seed"],
            "diagnostics": mc["diagnostics"],
            "assumed_nutrients": mc["assumed_nutrients"],
            "wider_ranges": mc["wider_ranges"],
        },
        "coverage": verdict.get("coverage"),
        "assumptions": verdict.get("assumptions", []),
        "advisory": verdict.get("advisory"),
        "compliance": {
            "day": verdict.get("day", day),
            "band": verdict.get("band", band),
            "probs": verdict.get("probs", {}),
            "nutrients": verdict.get("nutrients", {}),
        },
        "model_versions": _model_versions(depth_out),
    }


def _anchor_summary(anchor, depth_scale=None):
    out = {
        "method": anchor.get("method"), "tier": anchor.get("label"),
        "cm_per_px": anchor.get("cm_per_px"),
        "interval": anchor.get("interval"),
        "tilt_deg": anchor.get("tilt_deg"),
        "reason": anchor.get("reason"),
    }
    if depth_scale is not None:
        out["depth_scale_factor"] = depth_scale
    return out


def _seg_summary(seg):
    if not seg:
        return None
    return {k: seg.get(k) for k in ("strategy", "sam_score", "area_frac", "n_candidates")}


def _model_versions(depth_out):
    return {
        "segmenter": "facebook/sam2.1-hiera-large",
        "classifier": "google/siglip2-base-patch16-224",
        "depth": depth_out.get("model", "gt"),
    }
