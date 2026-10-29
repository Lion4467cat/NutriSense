"""S6: end-to-end analysis pipeline (lint -> anchor -> segment -> classify
-> depth -> portion -> MC -> verdict).

Every stage runs through engine.contract.stage(): fatal stages convert their
exceptions into a Failure (log ERROR, cannot_verify — never a 500), the anchor
stage degrades to the prior tier (log WARNING, continues). Every exit returns
the 18-key wire shape via Analysis.to_wire(), with policy thresholds attached.
Model stages additionally run through _oom_guard(): a CUDA OOM clears the
model registry (unload + cache clear) and retries once, recording the
degradations[] tag gpu_oom_retried; a second OOM becomes a structured Failure.

deps lets tests (and future alternate backends) override any stage:
  deps = {"segment": callable(image_bgr)->dict, "classify": ..., "depth": ...,
          "weight_head": <WeightHead-like or None to disable>}
Depth callables return {"depth_m": (H,W) meters, ...}; the pipeline calibrates
monocular scale against a measured anchor automatically.

Learned weight (ADR-0002): when the anchor is prior tier (no reference card)
and a trained weight head exists (data/weight_head.pt), the portion step asks
the head for grams (WED-trained, class-conditional) instead of size-prior
geometry. A head that fails — or is absent (checkpoint missing or failed to
load) — on a WED-mapped dish raises WeightHeadUnavailable -> cannot_verify
with the weight_head_unavailable reason and no grams; geometry is never
silently substituted. Dishes with no WED mapping never consult the head and
keep the geometry path. No-card plates are scored like any other, leading
their reasons with the no_reference_card estimate disclaimer.
"""
import logging
from pathlib import Path

import numpy as np

from config import (load_anchor_config, load_menu, load_wed_dishes,
                    load_wed_index, load_wed_sigma)
from engine.compliance import assess, no_card_reason
from engine.contract import (Analysis, Reason, ReasonKind, Stage,
                             WeightHeadUnavailable, load_policy, log_analysis,
                             reason_for_failure, register_fallback, stage)
from engine.gates import INPUT_GATES, SCOPE_GATE, admit
from engine.mc import sample_nutrients
from engine.depth import MonocularDepth, calibrate_depth_scale
from geo.pose import camera_matrix
from models.portion_estimator import _components, estimate_portion
from models.scale_anchor import estimate_anchor, prior_anchor

log = logging.getLogger("nutrisense")

# Assumed relative sigma when the head exists but no per-class val sigma is
# on disk yet (pre-training / unmapped class).
LEARNED_SIGMA_REL_FALLBACK = 0.30


def _is_oom(exc: BaseException) -> bool:
    """True for torch.OutOfMemoryError (== torch.cuda.OutOfMemoryError).
    torch is imported lazily so non-GPU paths never pay for it."""
    try:
        import torch
    except Exception:
        return False
    return isinstance(exc, torch.OutOfMemoryError)


def _oom_guard(fn, degradations: list):
    """Wrap a model-stage callable with one OOM retry.

    On a torch.OutOfMemoryError: record degradations["gpu_oom_retried"], drop
    every cached model from the registry (VRAM back to the driver, sticky
    factory failures unstuck), and retry fn once. A second OOM propagates so
    engine.contract.stage() can turn it into a structured Failure — never a
    500, and never a silent substitution of a different model.
    """

    def call():
        try:
            return fn()
        except Exception as e:
            if not _is_oom(e):
                raise
            log.warning("CUDA OOM — clearing the model registry and retrying once",
                        exc_info=True)
            if "gpu_oom_retried" not in degradations:
                degradations.append("gpu_oom_retried")
            from models import registry
            registry.unload()
            registry.clear_cache()
            return fn()

    return call


def _get_depth_provider():
    from models import registry
    return registry.get_or_create("depth_provider", MonocularDepth)


def _make_weight_head():
    from config import DATA_DIR
    from models.weight_head import WeightHead
    import torch
    ckpt = DATA_DIR / "weight_head.pt"
    if not ckpt.is_file():
        raise FileNotFoundError(ckpt)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return WeightHead.load(ckpt, device=device)


def _get_weight_head():
    """Lazy-load data/weight_head.pt once. Missing checkpoint -> None (the
    learned path is simply disabled; geometry prior keeps working)."""
    from models import registry
    try:
        return registry.get_or_create("weight_head", _make_weight_head)
    except FileNotFoundError:
        return None
    except Exception:
        log.exception("weight head checkpoint failed to load — geometry fallback")
        return None


def _wed_slots_for_dish(dish_key: str) -> list[int] | None:
    """Serving key -> WED regression slots (0-based). None when unmapped.
    Menu dishes read data/wed_dishes.yaml `dishes:`; off-menu serving keys
    (spec 002 expansion) read `off_menu:`."""
    for section in ("dishes", "off_menu"):
        mapping = load_wed_dishes().get(section, {}).get(dish_key) or {}
        names = mapping.get("wed_slots") or []
        if names:
            index = load_wed_index()
            slots = [index[n] for n in names if n in index]
            if slots:
                return slots
    return None


def _learned_portion(image_bgr, mask, dish, dish_key, head):
    """Learned-weight portion (no reference card): head predicts grams from
    the segmented region; recipe components share the predicted total. The
    geometry aux fields (height/footprint) are intentionally absent — they
    would only carry the uncalibrated-depth bias the head exists to avoid."""
    slots = _wed_slots_for_dish(dish_key)
    if not slots:
        raise ValueError(f"no WED slots mapped for dish {dish_key!r}")
    out = head.predict(image_bgr, mask, slot_ids=slots)
    grams = float(out["grams"])
    if not np.isfinite(grams) or grams <= 0:
        raise ValueError(f"head returned non-positive grams {grams}")
    shares, _dens, rho_eff = _components(dish)
    sigma_rel_map = load_wed_sigma()
    index = load_wed_index()
    slot_sigmas = []
    for s in slots:
        name = next((n for n, i in index.items() if i == s), None)
        if name in sigma_rel_map:
            slot_sigmas.append(sigma_rel_map[name])
    sigma = max(slot_sigmas) if slot_sigmas else LEARNED_SIGMA_REL_FALLBACK
    return {
        "grams": grams,
        "volume_ml": grams / rho_eff,          # implied, not depth-derived
        "density_eff": rho_eff,
        "components_g": {n: shares[n] * grams for n in shares},
        "base_method": "learned_weight",
        "scale_tier": "prior",
        "mean_h_mm": None,
        "area_cm2": None,
        "sigma_grams_rel": float(sigma),
        "sigma_rel": {"learned": float(sigma)},
        "depth_invalid_frac": 0.0,
        "flags": ["learned_weight_applied"],
        "grams_source": "learned_weight",
        "head_slots": {str(k): round(float(v), 2) for k, v in out["slots"].items()},
    }


def _make_ingredient_head():
    from models.ingredient_head import CKPT_PATH, IngredientHead
    import torch
    if not Path(CKPT_PATH).is_file():
        raise FileNotFoundError(CKPT_PATH)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return IngredientHead.load(device=device)


def _get_ingredient_head():
    """Lazy-load data/ingredient_head.pt once (07e). Missing checkpoint
    -> None: the ingredient route is disabled and the existing off-menu
    path (dish-slot head + generic table) runs byte-for-byte unchanged."""
    from models import registry
    try:
        return registry.get_or_create("ingredient_head",
                                      _make_ingredient_head)
    except FileNotFoundError:
        return None
    except Exception:
        log.exception("ingredient head failed to load — off-menu fallback")
        return None


def _make_prior_anchor():
    return prior_anchor("anchor stage failed — prior tier",
                        load_anchor_config())


register_fallback("prior_anchor", _make_prior_anchor)


def analyze(image_bgr, day, band, exif=None, deps=None, n_mc=4000, seed=1234,
            serving_style=None):
    """Run the full pipeline on one capture. Always returns the 17-key wire
    dict with a top-level `verdict` (PASS | FAIL | BORDERLINE | ESTIMATED |
    cannot_verify | out_of_scope)."""
    from models.dish_segmenter import segment_food
    from models.food_classifier import classify_dish

    deps = deps or {}
    segment = deps.get("segment") or segment_food
    classify = deps.get("classify") or classify_dish
    depth_fn = deps.get("depth") or _get_depth_provider()
    exif = exif or {"focal_mm": None, "subject_distance_cm": None,
                    "digital_zoom": None, "camera": None}
    timings: dict[str, float] = {}
    degradations: list[str] = []
    policy = load_policy()

    def finish(analysis: Analysis) -> dict:
        analysis.degradations = list(degradations)
        if analysis.path_used is None and analysis.portion is not None:
            if (analysis.anchor or {}).get("tier") == "measured":
                analysis.path_used = "card_geometry"
            elif analysis.portion.get("base_method") == "ingredient_compositional":
                analysis.path_used = "ingredient_head"
            elif analysis.portion.get("base_method") == "learned_weight":
                analysis.path_used = "learned_head"
            else:
                analysis.path_used = "prior_geometry"
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
    # horizontal FoV in degrees for the depth model (MoGe expects degrees)
    _H, _W = image_bgr.shape[:2]
    fov_x = float(np.degrees(2.0 * np.arctan(_W / (2.0 * K[0, 0]))))

    # --- segment stage ----------------------------------------------------
    def _segment_step():
        seg = segment(image_bgr)
        return seg, seg["mask"]  # missing key -> stage_failed/segment

    seg_out, failure = stage(Stage.SEGMENT, _oom_guard(_segment_step, degradations),
                             timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info)
    seg, mask = seg_out
    seg_info = _seg_summary(seg)

    # --- classify stage (classification + serving lookup) ------------------
    # Serving keys: menu dish keys via menu["dishes"], off-menu keys via
    # the wed_dishes `serving:`/`off_menu:` expansion (spec 002 decision 3).
    # An unrecognized key (no entry anywhere) still fails the stage.
    def _classify_step():
        cls = classify(image_bgr)
        classification = {
            "dish": cls.get("dish"), "confidence": cls.get("confidence"),
            "method": cls.get("method"), "match_score": cls.get("match_score"),
            "reason": cls.get("reason"),
        }
        if cls.get("dish") is None:
            return classification, None, None, cls.get("reason")
        dish_key = cls["dish"]
        wed = load_wed_dishes()
        off_menu = wed.get("off_menu") or {}
        if dish_key in menu["dishes"] or dish_key in off_menu:
            target = dish_key
        else:
            # a raw WED label routes through the serving map (e.g. phulka
            # -> wheat_product, the menu dish whose verdict path it keeps)
            target = (wed.get("serving") or {}).get(dish_key, {}).get("dish")
            if target is None:
                raise KeyError(
                    f"classified dish {dish_key!r} has no serving entry")
        dish = menu["dishes"].get(target) or off_menu.get(target)
        if dish is None:
            raise KeyError(f"classified dish {dish_key!r} has no serving entry")
        dish_info = {"id": target, "display_name": dish.get("display_name"),
                     "day": day, "band": band, "serving_style": serving_style,
                     "on_day": (not dish.get("days")) or day in dish.get("days", []),
                     "nutrition_source": dish.get("nutrition_source")}
        return classification, dish_info, dish, None

    cls_out, failure = stage(Stage.CLASSIFY, _oom_guard(_classify_step, degradations),
                             timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info)
    classification, dish_info, dish, cls_reason = cls_out
    if dish_info is None:
        # open-set abstain is an outcome, not a hard failure
        return finish(Analysis(
            verdict="cannot_verify",
            reasons=[Reason(ReasonKind.UNRECOGNIZED,
                            f"dish unrecognized: {cls_reason}")],
            lint=lint, anchor=anchor_info, segmentation=seg_info,
            classification=classification))

    outcome = admit(SCOPE_GATE, dish=dish)
    if not outcome.admitted:
        return finish(Analysis(verdict=SCOPE_GATE.verdict,
                               reasons=[outcome.reason],
                               failures=[outcome.failure], lint=lint,
                               anchor=anchor_info, segmentation=seg_info,
                               classification=classification, dish=dish_info))

    # --- general-mode ingredient route (ledger 013, ticket 07e) -----------
    # OFF-MENU dishes only. Head checkpoint absent/failed -> None and the
    # flow below runs byte-for-byte unchanged (fallback criterion); a route
    # that cannot match a recipe returns None through the stage Failure and
    # also falls through, with a machine-readable degradation tag.
    ing_head = (deps["ingredient_head"] if "ingredient_head" in deps
                else _get_ingredient_head())
    if (ing_head is not None
            and (anchor or {}).get("label") != "measured"
            and dish_info["id"] not in ((menu or {}).get("dishes") or {})):
        def _ingredient_step():
            from engine import general_mode as gm
            return gm.ingredient_route(image_bgr, ing_head, dish, dish_info)

        route, ing_failure = stage(Stage.PORTION,
                                   _oom_guard(_ingredient_step, degradations),
                                   timings=timings)
        if route is not None and ing_failure is None:
            portion = route["portion"]
            reasons = [Reason(
                ReasonKind.OFF_MENU,
                f"recognized off-menu dish "
                f"{dish.get('display_name') or dish_info['id']} — not on the "
                "school menu, so no compliance verdict; grams and nutrients "
                "are provided from the ingredient-compositional route")]
            if (anchor or {}).get("label") != "measured":
                reasons.append(no_card_reason(portion))
            return finish(Analysis(
                verdict="cannot_verify",
                reasons=reasons,
                lint=lint,
                anchor=anchor_info,
                segmentation=seg_info,
                classification=classification,
                dish=dish_info,
                portion=_portion_wire_block(portion),
                nutrition=route["nutrition"],
                model_versions=_model_versions(None, ing_head),
            ))
        if ing_failure is not None:
            if "ingredient_head_route_failed" not in degradations:
                degradations.append("ingredient_head_route_failed")
            log.warning("ingredient route unavailable (%s) — existing off-menu "
                        "path continues", ing_failure.error)

    # --- depth stage (monocular depth + anchor calibration) ---------------
    def _depth_step():
        depth_out = depth_fn(image_bgr, fov_x=fov_x)
        depth_m = np.asarray(depth_out["depth_m"], dtype=np.float64)
        scale_factor, scale_source = 1.0, "none"
        if anchor.get("label") == "measured":
            depth_m, scale_factor, scale_source = calibrate_depth_scale(
                depth_m, anchor, K)
        return depth_out, depth_m, scale_factor, scale_source

    depth_result, failure = stage(Stage.DEPTH, _oom_guard(_depth_step, degradations),
                                  timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info, classification=classification,
                    dish=dish_info)
    depth_out, depth_m, scale_factor, scale_source = depth_result

    # --- portion stage ----------------------------------------------------
    # Learned path (prior tier only): head.predict -> grams. An absent head
    # (checkpoint missing/load failed) and a failing head are treated the
    # same on a WED-mapped dish: WeightHeadUnavailable -> cannot_verify with
    # the weight_head_unavailable reason, no grams, path_used null. Unmapped
    # dishes and the measured tier keep the geometry path.
    head = deps["weight_head"] if "weight_head" in deps else _get_weight_head()

    def _portion_step():
        if (anchor.get("label") != "measured"
                and _wed_slots_for_dish(dish_info["id"]) is not None):
            if head is None:
                raise WeightHeadUnavailable(
                    f"weight head unavailable for {dish_info['id']}: "
                    "checkpoint missing or failed to load")
            try:
                return _learned_portion(image_bgr, mask, dish,
                                        dish_info["id"], head)
            except Exception as e:
                if _is_oom(e):
                    raise  # _oom_guard retries; a second OOM is a Failure
                raise WeightHeadUnavailable(
                    f"learned weight head failed: {type(e).__name__}: {e}"
                ) from e
        return estimate_portion(image_bgr, mask, depth_m, anchor, {"K": K}, dish)

    portion, failure = stage(Stage.PORTION, _oom_guard(_portion_step, degradations),
                             timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info, classification=classification,
                    dish=dish_info)
    portion_block = _portion_wire_block(portion)

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

    # --- off-menu serving path (spec 002 decision 3 + ADR 0003) -----------
    # A recognized off-menu dish IS recognized (ledger 003 interpretation):
    # grams + nutrients ride the wire like any plate; school compliance
    # scoring does not apply, so the verdict is cannot_verify with the
    # off_menu_dish reason LEADING the reasons (no-card disclaimer follows
    # on the prior tier, spec story 22). out_of_scope stays only for
    # explicitly-scoped menu dishes (SCOPE gate) and unrecognized captures.
    if dish_info["id"] not in ((menu or {}).get("dishes") or {}):
        anchor_info = anchor_info or {}
        anchor_info["depth_scale_factor"] = round(float(scale_factor), 4)
        anchor_info["depth_scale_source"] = scale_source
        name = dish.get("display_name") or dish_info["id"]
        reasons = [Reason(
            ReasonKind.OFF_MENU,
            f"recognized off-menu dish {name} — not on the school menu, so "
            "no compliance verdict; grams and nutrients are provided")]
        if (anchor or {}).get("label") != "measured":
            reasons.append(no_card_reason(portion))
        return finish(Analysis(
            verdict="cannot_verify",
            reasons=reasons,
            lint=lint,
            anchor=anchor_info,
            segmentation=seg_info,
            classification=classification,
            dish=dish_info,
            portion=portion_block,
            nutrition=nutrition_block,
            model_versions=_model_versions(depth_out, head),
        ))

    # --- compliance stage (verdict) ---------------------------------------
    score, failure = stage(Stage.COMPLIANCE, assess, mc, portion, dish, band,
                           anchor.get("label", "prior"), day=day,
                           depth_scale_source=scale_source,
                           timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info, classification=classification,
                    dish=dish_info, portion=portion_block,
                    nutrition=nutrition_block)

    anchor_info["depth_scale_factor"] = round(float(scale_factor), 4)
    anchor_info["depth_scale_source"] = scale_source

    return finish(Analysis(
        verdict=score.verdict,
        reasons=list(score.reasons),
        failures=list(score.failures),
        lint=lint,
        anchor=anchor_info,
        segmentation=seg_info,
        classification=classification,
        dish=dish_info,
        portion=portion_block,
        nutrition=nutrition_block,
        coverage=score.coverage,
        assumptions=score.assumptions,
        advisory=score.advisory,
        compliance={
            "day": score.day,
            "band": score.band,
            "probs": score.probs,
            "nutrients": score.nutrients,
        },
        model_versions=_model_versions(depth_out, head),
    ))


def _anchor_summary(anchor):
    if not anchor:
        return None
    return {
        "method": anchor.get("method"), "tier": anchor.get("label"),
        "cm_per_px": anchor.get("cm_per_px"),
        "interval": anchor.get("interval"),
        "tilt_deg": anchor.get("tilt_deg"),
        "reason": anchor.get("reason"),
    }


def _portion_wire_block(portion: dict) -> dict:
    """portion estimator dict -> the wire `portion` block (S3 contract key
    order; optional head_slots / recipe_match appended)."""
    block = {
        "grams": round(portion["grams"], 1),
        "volume_ml": round(portion["volume_ml"], 1),
        "density_eff": round(portion["density_eff"], 3),
        "components_g": {k: round(v, 1) for k, v in portion["components_g"].items()},
        "base_method": portion["base_method"],
        "scale_tier": portion["scale_tier"],
        "grams_source": portion.get("grams_source", "geometry"),
        "mean_h_mm": (None if portion.get("mean_h_mm") is None
                      else round(portion["mean_h_mm"], 2)),
        "area_cm2": (None if portion.get("area_cm2") is None
                     else round(portion["area_cm2"], 1)),
        "sigma_grams_rel": round(portion["sigma_grams_rel"], 4),
        "sigma_rel": {k: round(v, 4) for k, v in portion["sigma_rel"].items()},
        "flags": portion["flags"],
    }
    if "head_slots" in portion:
        block["head_slots"] = portion["head_slots"]
    if "recipe_match" in portion:
        block["recipe_match"] = portion["recipe_match"]
    return block


def _seg_summary(seg):
    if not seg:
        return None
    return {k: seg.get(k) for k in ("strategy", "sam_score", "area_frac", "n_candidates")}


def _model_versions(depth_out, head=None, ingredient_head=None):
    versions = {
        "segmenter": "facebook/sam2.1-hiera-large",
        "classifier": "google/siglip2-base-patch16-224",
        "depth": depth_out.get("model", "gt") if depth_out is not None
                 else "not_run",
    }
    if head is not None:
        meta = getattr(head, "meta", {}) or {}
        recipe = meta.get("recipe", "wed-baseline-resnet50")
        mae = meta.get("test_mae_g")
        versions["weight_head"] = (f"{recipe} (test MAE {mae}g)" if mae is not None
                                   else str(recipe))
    if ingredient_head is not None:
        meta = getattr(ingredient_head, "meta", {}) or {}
        enc = getattr(ingredient_head, "encoder", meta.get("encoder", "?"))
        mae = meta.get("test_grams_mae")
        versions["ingredient_head"] = (
            f"n5k-ingredient-{enc} (test MAE {mae}g)" if mae is not None
            else f"n5k-ingredient-{enc}")
    return versions
