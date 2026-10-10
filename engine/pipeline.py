"""S6: end-to-end analysis pipeline (lint -> anchor -> segment -> classify
-> depth -> portion -> MC -> verdict).

Every stage runs through engine.contract.stage(): fatal stages convert their
exceptions into a Failure (log ERROR, cannot_verify — never a 500), the anchor
stage degrades to the prior tier (log WARNING, continues). Every exit returns
the 16-key wire shape via Analysis.to_wire(), with policy thresholds attached.

deps lets tests (and future alternate backends) override any stage:
  deps = {"segment": callable(image_bgr)->dict, "classify": ..., "depth": ...}
Depth callables return {"depth_m": (H,W) meters, ...}; the pipeline calibrates
monocular scale against a measured anchor automatically.
"""
import numpy as np

from config import load_anchor_config, load_menu
from engine.compliance import assess
from engine.contract import (Analysis, Reason, ReasonKind, Stage,
                             load_policy, log_analysis,
                             reason_for_failure, register_fallback, stage)
from engine.gates import INPUT_GATES, SCOPE_GATE, admit
from engine.mc import sample_nutrients
from engine.depth import MonocularDepth, calibrate_depth_scale
from geo.pose import camera_matrix
from models.portion_estimator import estimate_portion
from models.scale_anchor import estimate_anchor, prior_anchor

_default_depth = None


def _get_depth_provider():
    global _default_depth
    if _default_depth is None:
        _default_depth = MonocularDepth()
    return _default_depth


def _make_prior_anchor():
    return prior_anchor("anchor stage failed — prior tier",
                        load_anchor_config())


register_fallback("prior_anchor", _make_prior_anchor)


def analyze(image_bgr, day, band, exif=None, deps=None, n_mc=4000, seed=1234,
            serving_style=None):
    """Run the full pipeline on one capture. Always returns the 16-key wire
    dict with a top-level `verdict` (PASS | FAIL | BORDERLINE | cannot_verify |
    out_of_scope)."""
    from models.dish_segmenter import segment_food
    from models.food_classifier import classify_dish

    deps = deps or {}
    segment = deps.get("segment") or segment_food
    classify = deps.get("classify") or classify_dish
    depth_fn = deps.get("depth") or _get_depth_provider()
    exif = exif or {"focal_mm": None, "subject_distance_cm": None,
                    "digital_zoom": None, "camera": None}
    timings: dict[str, float] = {}
    policy = load_policy()

    def finish(analysis: Analysis) -> dict:
        log_analysis(str(analysis.verdict), day, band, timings)
        return analysis.to_wire()

    def fail(failure, **blocks) -> dict:
        analysis = Analysis(verdict="cannot_verify",
                            reasons=[reason_for_failure(failure)],
                            failures=[failure], **blocks)
        return finish(analysis)

    # --- input stage: menu config ----------------------------------------
    menu, failure = stage(Stage.INPUT, load_menu, timings=timings)
    if failure:
        return fail(failure)

    H, W = image_bgr.shape[:2]
    lint = {
        "digital_zoom": exif.get("digital_zoom"),
        "focal_mm": exif.get("focal_mm"),
        "min_side_px": int(min(H, W)),
        "resolution_ok": bool(min(H, W) >= policy.lint_min_side_px),
        "notes": [],
    }
    if not lint["resolution_ok"]:
        lint["notes"].append(f"min side {min(H, W)} < {policy.lint_min_side_px}px "
                             "(marker tier may fall back to prior)")

    # --- hard gates: one table, consulted once each -----------------------
    for gate in INPUT_GATES:
        outcome = admit(gate, lint=lint, day=day, band=band, menu=menu)
        if not outcome.admitted:
            return finish(Analysis(verdict=gate.verdict,
                                   reasons=[outcome.reason],
                                   failures=[outcome.failure], lint=lint))

    # --- anchor stage (degrade to prior tier on failure) ------------------
    anchor, failure = stage(Stage.ANCHOR, estimate_anchor, image_bgr,
                            exif=exif, timings=timings)
    if failure:
        return fail(failure, lint=lint)
    anchor_info = _anchor_summary(anchor)

    # --- input stage: camera intrinsics -----------------------------------
    def _intrinsics():
        cfg = load_anchor_config()
        cam = cfg["camera"]
        focal = exif.get("focal_mm") or cam["focal_length_fallback_mm"]
        return camera_matrix(focal, cam.get("sensor_width_mm", 6.17), W, H)

    K, failure = stage(Stage.INPUT, _intrinsics, timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info)

    # --- segment stage ----------------------------------------------------
    def _segment_step():
        seg = segment(image_bgr)
        return seg, seg["mask"]  # missing key -> stage_failed/segment

    seg_out, failure = stage(Stage.SEGMENT, _segment_step, timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info)
    seg, mask = seg_out
    seg_info = _seg_summary(seg)

    # --- classify stage (classification + menu lookup) --------------------
    def _classify_step():
        cls = classify(image_bgr)
        classification = {
            "dish": cls.get("dish"), "confidence": cls.get("confidence"),
            "method": cls.get("method"), "match_score": cls.get("match_score"),
            "reason": cls.get("reason"),
        }
        if cls.get("dish") is None:
            return classification, None, cls.get("reason")
        dish_key = cls["dish"]
        dish = menu["dishes"][dish_key]  # KeyError -> stage_failed/classify
        dish_info = {"id": dish_key, "display_name": dish.get("display_name"),
                     "day": day, "band": band, "serving_style": serving_style,
                     "on_day": (not dish.get("days")) or day in dish.get("days", []),
                     "nutrition_source": dish.get("nutrition_source")}
        return classification, dish_info, None

    cls_out, failure = stage(Stage.CLASSIFY, _classify_step, timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info)
    classification, dish_info, cls_reason = cls_out
    if dish_info is None:
        # open-set abstain is an outcome, not a hard failure
        return finish(Analysis(
            verdict="cannot_verify",
            reasons=[Reason(ReasonKind.UNRECOGNIZED,
                            f"dish unrecognized: {cls_reason}")],
            lint=lint, anchor=anchor_info, segmentation=seg_info,
            classification=classification))

    dish = menu["dishes"][dish_info["id"]]
    outcome = admit(SCOPE_GATE, dish=dish)
    if not outcome.admitted:
        return finish(Analysis(verdict=SCOPE_GATE.verdict,
                               reasons=[outcome.reason],
                               failures=[outcome.failure], lint=lint,
                               anchor=anchor_info, segmentation=seg_info,
                               classification=classification, dish=dish_info))

    # --- depth stage (monocular depth + anchor calibration) ---------------
    def _depth_step():
        depth_out = depth_fn(image_bgr)
        depth_m = np.asarray(depth_out["depth_m"], dtype=np.float64)
        scale_factor, scale_source = 1.0, "none"
        if anchor.get("label") == "measured":
            depth_m, scale_factor, scale_source = calibrate_depth_scale(
                depth_m, anchor, K)
        return depth_out, depth_m, scale_factor, scale_source

    depth_result, failure = stage(Stage.DEPTH, _depth_step, timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info, classification=classification,
                    dish=dish_info)
    depth_out, depth_m, scale_factor, scale_source = depth_result

    # --- portion stage ----------------------------------------------------
    portion, failure = stage(Stage.PORTION, estimate_portion, image_bgr, mask,
                             depth_m, anchor, {"K": K}, dish, timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info, classification=classification,
                    dish=dish_info)
    portion_block = {
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
    }

    # --- nutrition stage (Monte Carlo) ------------------------------------
    mc, failure = stage(Stage.NUTRITION, sample_nutrients, portion, dish, band,
                        n=n_mc, seed=seed, timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info, classification=classification,
                    dish=dish_info, portion=portion_block)
    nutrition_block = {
        "kcal": mc["kcal"], "protein_g": mc["protein_g"],
        "grams": mc["grams"],
        "n": mc["n"], "seed": mc["seed"],
        "diagnostics": mc["diagnostics"],
        "assumed_nutrients": mc["assumed_nutrients"],
        "wider_ranges": mc["wider_ranges"],
    }

    # --- compliance stage (verdict) ---------------------------------------
    verdict, failure = stage(Stage.COMPLIANCE, assess, mc, portion, dish, band,
                             anchor.get("label", "prior"), day=day,
                             timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info, classification=classification,
                    dish=dish_info, portion=portion_block,
                    nutrition=nutrition_block)

    anchor_info["depth_scale_factor"] = round(float(scale_factor), 4)
    anchor_info["depth_scale_source"] = scale_source

    return finish(Analysis(
        verdict=verdict["verdict"],
        reasons=list(verdict["reasons"]),
        lint=lint,
        anchor=anchor_info,
        segmentation=seg_info,
        classification=classification,
        dish=dish_info,
        portion=portion_block,
        nutrition=nutrition_block,
        coverage=verdict.get("coverage"),
        assumptions=verdict.get("assumptions", []),
        advisory=verdict.get("advisory"),
        compliance={
            "day": verdict.get("day", day),
            "band": verdict.get("band", band),
            "probs": verdict.get("probs", {}),
            "nutrients": verdict.get("nutrients", {}),
        },
        model_versions=_model_versions(depth_out),
    ))


def _anchor_summary(anchor, depth_scale=None):
    if not anchor:
        return None
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
