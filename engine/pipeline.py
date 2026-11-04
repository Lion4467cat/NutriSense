"""S6: end-to-end analysis pipeline (lint -> anchor -> segment -> classify
-> depth -> portion -> MC -> verdict).

Every stage runs through engine.contract.stage(): fatal stages convert their
exceptions into a Failure (log ERROR, cannot_verify — never a 500), the anchor
stage degrades to the prior tier (log WARNING, continues). Every exit returns
the 19-key wire shape via Analysis.to_wire(), with policy thresholds attached.
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
silently substituted. A no-card dish with no WED mapping has no valid physical
scale source and is withheld rather than sent through size-prior geometry.
Mapped no-card plates retain the no_reference_card estimate disclaimer.
"""
import logging
from pathlib import Path

import cv2
import numpy as np

from config import (load_anchor_config, load_menu, load_wed_dishes,
                    load_standards, load_wed_index, load_wed_sigma)
from engine.compliance import assess, no_card_reason
from engine.contract import (Analysis, Reason, ReasonKind, Stage,
                             WeightHeadUnavailable, load_policy, log_analysis,
                             reason_for_failure, register_fallback, stage)
from engine.gates import INPUT_GATES, SCOPE_GATE, admit
from engine.mc import aggregate_meal, sample_nutrients
from engine.depth import MODEL_ID as MOGE_MODEL_ID
from engine.depth import (MonocularDepth, calibrate_depth_scale,
                          normalized_intrinsics_to_pixel_K)
from geo.pose import camera_matrix
from models.portion_estimator import _components, estimate_portion
from models.scale_anchor import (estimate_anchor, prior_anchor,
                                 refine_anchor_pose)

log = logging.getLogger("nutrisense")

# Recommended capture-tilt band (spec 005, pre-registered default): oblique
# enough for base-plane/depth evidence, not so oblique that area
# foreshortening dominates. Informational lint only — never blocks.
CAPTURE_TILT_MIN_DEG = 25.0
CAPTURE_TILT_MAX_DEG = 60.0

# Assumed relative sigma when the head exists but no per-class val sigma is
# on disk yet (pre-training / unmapped class).
LEARNED_SIGMA_REL_FALLBACK = 0.30

def _append_plate_sanity_note(lint, grams, band):
    """Add the configured, non-blocking cooked-plate plausibility lint."""
    if lint is None or not np.isfinite(grams):
        return
    bounds = (load_standards().get("plate_sanity_g") or {}).get(str(band))
    if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
        return
    low, high = map(float, bounds)
    lower, upper = low * 0.75, high * 1.25
    if grams < lower or grams > upper:
        lint.setdefault("notes", []).append(
            f"estimated plate weight {grams:.0f}g is outside the loose "
            f"{band} band check ({lower:.0f}–{upper:.0f}g)"
        )


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


def _make_implicit_scale_head():
    from models.implicit_scale import ImplicitScaleHead
    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return ImplicitScaleHead.load(device=device)


def _get_implicit_scale_head():
    """Lazy-load the card-free implicit scale head from the registry."""
    from models import registry
    try:
        return registry.get_or_create("implicit_scale_head", _make_implicit_scale_head)
    except Exception as e:
        log.warning("implicit scale head failed to load (%s) — continuing with unscaled prior", e)
        return None


def _combo_candidates(dish_id: str) -> list[str] | None:
    """Serving targets of a combo dish's component WED classes (spec 004).

    A combo dish maps to >= 2 WED classes (rice_sambar -> steamed-rice +
    sambar); each maps through the serving map to a component serving key.
    None for single-component or unmapped dishes (no decomposition)."""
    names: list[str] = []
    for section in ("dishes", "off_menu"):
        names = (load_wed_dishes().get(section, {}).get(dish_id) or {}
                 ).get("wed_slots") or []
        if names:
            break
    if len(names) < 2:
        return None
    from models.food_classifier import serving_targets
    targets = serving_targets()
    out = sorted({targets[n] for n in names if n in targets})
    return out if len(out) >= 2 else None


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


def _get_segment_items():
    """Multi-vessel detection (spec 003), lazy via the registry so tests can
    pin it to None (conftest) exactly like the weight/ingredient heads."""
    from models import registry
    return registry.get_or_create(
        "segment_items", _load_segment_items)


def _load_segment_items():
    from models.dish_segmenter import segment_items
    return segment_items


def _make_prior_anchor():
    return prior_anchor("anchor stage failed — prior tier",
                        load_anchor_config())


register_fallback("prior_anchor", _make_prior_anchor)


def _card_exclusion_mask(shape: tuple[int, int], anchor: dict | None) -> np.ndarray | None:
    """Return a boolean mask covering the physical ArUco reference card, or None."""
    if not isinstance(anchor, dict) or anchor.get("label") != "measured":
        return None
    import cv2

    h, w = shape
    card_mask = np.zeros((h, w), dtype=np.uint8)
    H = anchor.get("H")
    if H is not None:
        try:
            H_arr = np.asarray(H, dtype=np.float64)
            # ISO 216 A6 card half-extents (52.5mm x 74.0mm) + 1 ArUco module margin.
            card_mm = np.array(
                [[[-58.0, -80.0]], [[58.0, -80.0]],
                 [[58.0, 80.0]], [[-58.0, 80.0]]],
                dtype=np.float64,
            )
            pts = cv2.perspectiveTransform(card_mm, H_arr).reshape(4, 2)
            if np.all(np.isfinite(pts)):
                cv2.fillConvexPoly(card_mask, np.round(pts).astype(np.int32), 1)
        except Exception:
            pass
    corners = (anchor.get("extras") or {}).get("marker_corners_px")
    if corners is not None:
        c = np.asarray(corners, dtype=np.float64).reshape(4, 2)
        center = c.mean(axis=0, keepdims=True)
        # Ratio of A6 card length (148 mm) to 60 mm ArUco marker side (~2.47).
        expanded = center + 2.5 * (c - center)
        cv2.fillConvexPoly(card_mask, np.round(expanded).astype(np.int32), 1)
    return card_mask > 0 if np.any(card_mask > 0) else None


def _is_valid_secondary_vessel(
    item_mask: np.ndarray,
    parent_mask: np.ndarray,
    card_mask: np.ndarray | None,
    image_shape: tuple[int, int],
) -> bool:
    """Distinguish between a huge tabletop/plate proposal and a compact secondary vessel (katori/bowl/egg)."""
    item_mask = np.asarray(item_mask, dtype=bool)
    item_area = float(item_mask.sum())
    if item_area <= 0:
        return False
    H, W = image_shape[:2]
    img_area = float(H * W)
    parent_area = float(parent_mask.sum())
    area_frac = item_area / img_area
    # a. Bounded Area: A secondary vessel is compact relative to the meal and frame
    if not (item_area <= 0.50 * parent_area and 0.012 <= area_frac <= 0.075):
        return False
    # b. Not the Reference Card:
    if card_mask is not None:
        card_overlap = float((item_mask & card_mask).sum()) / item_area
        if card_overlap >= 0.08:
            return False
    # c. Compact Aspect & Solidity:
    v_idx, u_idx = np.nonzero(item_mask)
    if len(u_idx) == 0:
        return False
    y1, y2 = int(v_idx.min()), int(v_idx.max()) + 1
    x1, x2 = int(u_idx.min()), int(u_idx.max()) + 1
    bw = max(1, x2 - x1)
    bh = max(1, y2 - y1)
    aspect = min(bw, bh) / max(bw, bh)
    pts = np.column_stack([u_idx, v_idx])
    hull = cv2.convexHull(pts)
    ha = cv2.contourArea(hull)
    solidity = item_area / max(ha, 1.0)
    touches = 0
    if y1 <= 5: touches += 1
    if y2 >= H - 6: touches += 1
    if x1 <= 5: touches += 1
    if x2 >= W - 6: touches += 1
    return aspect >= 0.48 and solidity >= 0.55 and touches == 0


DECOY_SIDE_CLASSES: frozenset[str] = frozenset({
    "chutney", "curd", "raita", "papad", "salad", "mango-pickle", "boondi"
})
LIQUID_BOWL_CLASSES: frozenset[str] = frozenset({
    "sambar", "leaf-dal", "rasam", "non-spicy-dal", "tomato-pappu",
    "dal", "pachi-pulusu", "bendakaya-pulusu", "rajma"
})


def _mask_core_chromaticity(
    image_bgr: np.ndarray,
    mask: np.ndarray | None,
    bbox: list[int] | None = None,
) -> dict[str, float]:
    """Compute core chromaticity (HSV) on the inner 60% core of a mask/bbox.
    Drops specular highlights (V > 235, S < 35) and dark shadows (V < 40)."""
    if mask is None and bbox is not None:
        x0, y0, x1, y1 = bbox
        mask = np.zeros(image_bgr.shape[:2], dtype=bool)
        mask[max(0, y0):min(image_bgr.shape[0], y1), max(0, x0):min(image_bgr.shape[1], x1)] = True
    if mask is None or not np.asarray(mask).any():
        return {"mean_h": 0.0, "mean_s": 0.0, "mean_v": 0.0, "specular_frac": 0.0, "valid_px": 0}

    mask_bool = np.asarray(mask, dtype=bool)
    k_size = max(3, int(np.sqrt(float(mask_bool.sum())) * 0.15))
    if k_size % 2 == 0:
        k_size += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_size, k_size))
    eroded = cv2.erode(mask_bool.astype(np.uint8), kernel) > 0
    if not eroded.any():
        eroded = mask_bool

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    h_chan, s_chan, v_chan = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    specular = (v_chan > 235) & (s_chan < 35) & eroded
    shadow = (v_chan < 40) & eroded
    valid = eroded & (~specular) & (~shadow)

    spec_frac = float(specular.sum()) / float(eroded.sum()) if eroded.any() else 0.0
    if not valid.any():
        valid = eroded

    return {
        "mean_h": float(np.mean(h_chan[valid])),
        "mean_s": float(np.mean(s_chan[valid])),
        "mean_v": float(np.mean(v_chan[valid])),
        "specular_frac": spec_frac,
        "valid_px": int(valid.sum()),
    }


def _same_food_family(id1: str | None, id2: str | None) -> bool:
    """True if two food IDs represent the same broad dish family."""
    if not id1 or not id2:
        return False
    if id1 == id2:
        return True
    n1 = id1.replace("-", "_").replace(" ", "_").lower()
    n2 = id2.replace("-", "_").replace(" ", "_").lower()
    if n1 == n2:
        return True
    if any(k in n1 for k in ("rice", "biryani", "briyani")) and any(k in n2 for k in ("rice", "biryani", "briyani")):
        return True
    if any(k in n1 for k in ("dal", "sambar", "rasam", "curd", "raita")) and any(k in n2 for k in ("dal", "sambar", "rasam", "curd", "raita")):
        return True
    return bool(any(k in n1 for k in ("wheat", "chapati", "roti", "phulka")) and any(k in n2 for k in ("wheat", "chapati", "roti", "phulka")))


def _reconcile_dense_grid_items(
    detected_items: list[dict],
    top_mask: np.ndarray,
    card_mask: np.ndarray | None,
    seg_info: dict,
) -> list[dict]:
    """Filter background/card proposals and sliding-window crop echoes from dense_grid_box,
    while preserving compact secondary vessels (katoris, eggs, chutney bowls)."""
    from models.dish_segmenter import ITEM_CROP_FRAC

    top_bool = np.asarray(top_mask, dtype=bool)
    h, w = top_bool.shape[:2]
    crop_w = max(1.0, float(ITEM_CROP_FRAC) * float(w))
    crop_h = max(1.0, float(ITEM_CROP_FRAC) * float(h))
    # SAM2 _query_batch prompts each crop with box [0.08, 0.92] (span 0.84);
    # subtracting one 1/16 mask-decoder stride cell gives 0.78 for box-clipped echoes.
    prompt_box_clip_frac = (0.92 - 0.08) - (1.0 / 16.0)
    valid_items: list[dict] = []
    secondary_cands: list[dict] = []
    bounded_vessel_count = 0
    for item in detected_items:
        item_mask = np.asarray(item.get("mask"), dtype=bool)
        if item_mask.shape != top_bool.shape:
            continue
        item_area = float(item_mask.sum())
        if item_area <= 0.0:
            continue
        if card_mask is not None and float((item_mask & card_mask).sum()) / item_area >= 0.08:
            continue
        in_top = float((item_mask & top_bool).sum()) / item_area
        if in_top >= 0.50:
            bbox = item.get("bbox")
            if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                bw_frac = float(bbox[2] - bbox[0]) / crop_w
                bh_frac = float(bbox[3] - bbox[1]) / crop_h
            else:
                bw_frac, bh_frac = 0.0, 0.0
            if not (bw_frac >= prompt_box_clip_frac and bh_frac >= prompt_box_clip_frac):
                bounded_vessel_count += 1
            valid_items.append(item)
        elif _is_valid_secondary_vessel(item_mask, top_bool, card_mask, (h, w)):
            c_mask = card_mask if card_mask is not None else np.zeros_like(top_bool)
            clean_mask = item_mask & ~top_bool & ~c_mask
            if int(clean_mask.sum()) >= 64:
                item_copy = dict(item)
                item_copy["mask"] = clean_mask
                item_copy["is_secondary_vessel"] = True
                v_idx, u_idx = np.nonzero(clean_mask)
                item_copy["bbox"] = [int(u_idx.min()), int(v_idx.min()), int(u_idx.max()) + 1, int(v_idx.max()) + 1]
                item_copy["area_frac"] = float(clean_mask.sum()) / float(h * w)
                secondary_cands.append(item_copy)

    # Spatial NMS on secondary candidates so multiple overlapping proposals for the same bowl do not multiply
    kept_sec: list[dict] = []
    if secondary_cands:
        secondary_cands.sort(key=lambda it: float(it.get("sam_score") or 0.0), reverse=True)
        for cand in secondary_cands:
            cm = np.asarray(cand["mask"], dtype=bool)
            overlap = False
            for prev in kept_sec:
                pm = np.asarray(prev["mask"], dtype=bool)
                iou = float((cm & pm).sum()) / max(float((cm | pm).sum()), 1.0)
                if iou > 0.20:
                    overlap = True
                    break
            if not overlap:
                kept_sec.append(cand)
                bounded_vessel_count += 1
                if len(kept_sec) >= 2:
                    break

    if kept_sec:
        # Check connected components of top_bool (the main plate food)
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(top_bool.astype(np.uint8), connectivity=8)
        main_components = [i for i in range(1, num_labels) if stats[i, cv2.CC_STAT_AREA] >= 2000]
        if len(main_components) <= 1:
            ys, xs = np.nonzero(top_bool)
            top_bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1] if len(xs) else None
            return [{
                "mask": top_bool,
                "sam_score": seg_info.get("sam_score"),
                "area_frac": float(top_bool.mean()),
                "bbox": top_bbox,
            }] + kept_sec
        valid_items.extend(kept_sec)

    if len(valid_items) <= 1 or bounded_vessel_count < 2:
        return [{
            "mask": top_bool,
            "sam_score": seg_info.get("sam_score"),
            "area_frac": seg_info.get("area_frac", float(top_bool.mean())),
            "bbox": None,
        }]
    return valid_items


def analyze(image_bgr, day, band, exif=None, deps=None, n_mc=4000, seed=1234,
            serving_style=None, mode="school"):
    """Run the full pipeline on one capture. Always returns the 19-key wire
    dict with a top-level `verdict` (PASS | FAIL | BORDERLINE | ESTIMATED |
    cannot_verify | out_of_scope)."""
    from engine.gates import normalize_band, normalize_day
    from models.dish_segmenter import segment_food
    from models.food_classifier import classify_dish

    deps = deps or {}
    day = normalize_day(day)
    band = normalize_band(band)
    if mode not in {"school", "general"}:
        raise ValueError("mode must be 'school' or 'general'")
    segment = deps.get("segment") or segment_food
    classify = deps.get("classify") or classify_dish
    # MoGe's relative prediction is useful as geometry only after a measured
    # marker calibration. For no-card WED-mapped food, the existing learned
    # weight head is the valid route; avoid loading/running raw relative depth.
    depth_fn = deps.get("depth")
    exif = exif or {"focal_mm": None, "subject_distance_cm": None,
                    "digital_zoom": None, "camera": None}
    timings: dict[str, float] = {}
    degradations: list[str] = []
    estimate_only_notes: list[str] = []
    primary_item_bbox = None
    active_segmenter_model = None
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
        # spec 003: single-serving frames carry items[] too — a one-element
        # mirror of the top-level blocks, so consumers read one shape.
        if analysis.items is None and analysis.portion is not None:
            seg = analysis.segmentation or {}
            analysis.items = [{
                "dish": analysis.dish,
                "classification": analysis.classification,
                "portion": analysis.portion,
                "bbox": primary_item_bbox,
                "area_frac": seg.get("area_frac"),
                "sam_score": seg.get("sam_score"),
            }]
        log_analysis(str(analysis.verdict), day, band, timings)
        wire = analysis.to_wire()
        if active_segmenter_model and wire.get("model_versions") is not None:
            wire["model_versions"]["segmenter"] = active_segmenter_model
        return wire

    def fail(failure, **blocks) -> dict:
        analysis = Analysis(verdict="cannot_verify",
                            reasons=[reason_for_failure(failure)],
                            failures=[failure], **blocks)
        return finish(analysis)

    # --- input stage: menu config ----------------------------------------
    menu, failure = stage(Stage.INPUT, load_menu, timings=timings)
    if failure:
        return fail(failure)
    assert menu is not None  # successful input stage always returns the menu

    H, W = image_bgr.shape[:2]
    lint = {
        "digital_zoom": exif.get("digital_zoom"),
        "focal_mm": exif.get("focal_mm"),
        "min_side_px": int(min(H, W)),
        "resolution_ok": bool(min(H, W) >= policy.lint_min_side_px),
        "notes": [],
    }
    if lint["digital_zoom"] is None:
        zoom_note = (
            "Digital-zoom metadata is missing. Food identification and an "
            "estimate can continue, but the school-standard verdict is withheld."
        )
        lint["notes"].append(zoom_note)
        estimate_only_notes.append(zoom_note)
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
    anchor = anchor or {}  # a successful anchor stage always has a fallback
    anchor_info = _anchor_summary(anchor)

    # --- capture-angle lint (spec 005): informational, non-blocking --------
    if (anchor or {}).get("label") == "measured":
        tilt = anchor.get("tilt_deg")
        if tilt is not None and not (CAPTURE_TILT_MIN_DEG
                                     <= float(tilt) <= CAPTURE_TILT_MAX_DEG):
            tilt_deg = float(tilt)
            lint["notes"].append(
                f"capture angle {tilt_deg:.0f}° outside the recommended "
                f"{CAPTURE_TILT_MIN_DEG:.0f}–{CAPTURE_TILT_MAX_DEG:.0f}° band "
                "(depth/base-plane evidence degrades)")
            if tilt_deg > CAPTURE_TILT_MAX_DEG:
                estimate_only_notes.append(
                    "The measured card is outside the recommended camera-angle "
                    "range. Food and nutrition can still be estimated, but the "
                    "school-standard verdict is withheld because the footprint "
                    "correction is not validated at this angle.")

    # --- input stage: camera intrinsics -----------------------------------
    def _intrinsics():
        cfg = load_anchor_config()
        cam = cfg["camera"]
        focal = exif.get("focal_mm") or cam["focal_length_fallback_mm"]
        return camera_matrix(focal, cam.get("sensor_width_mm", 6.17), W, H)

    K, failure = stage(Stage.INPUT, _intrinsics, timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info)
    assert K is not None  # successful intrinsics stage returns a camera matrix
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
    assert seg_out is not None  # segment stage returns metadata and a mask
    seg, mask = seg_out
    card_mask = _card_exclusion_mask(np.asarray(mask).shape[:2], anchor)
    mask_clipped_by_card = False
    if card_mask is not None:
        mask_bool = np.asarray(mask, dtype=bool)
        if bool((mask_bool & card_mask).any()) and int((mask_bool & ~card_mask).sum()) >= 64:
            mask = mask_bool & ~card_mask
            mask_clipped_by_card = True
    active_segmenter_model = seg.get("model_id")
    seg_info = _seg_summary(seg) or {}
    if mask_clipped_by_card and "area_frac" in seg_info:
        seg_info["area_frac"] = float(np.asarray(mask, dtype=bool).mean())

    # --- classify stage (classification + serving lookup) ------------------
    # Serving keys: menu dish keys via menu["dishes"], off-menu keys via
    # the wed_dishes `serving:`/`off_menu:` expansion (spec 002 decision 3).
    # An unrecognized key (no entry anywhere) still fails the stage.
    def _resolve_serving(cls):
        """Classifier output -> (classification, dish_info, dish, reason).

        Shared by the primary full-frame classification and the per-item
        crop classifications of the multi-item path (spec 003)."""
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
        menu_dish = target in menu["dishes"]
        dish_info = {"id": target, "display_name": dish.get("display_name"),
                     "day": day, "band": band, "serving_style": serving_style,
                     "on_day": menu_dish and
                     ((not dish.get("days")) or day in dish.get("days", [])),
                     "nutrition_source": dish.get("nutrition_source")}
        return classification, dish_info, dish, None

    def _classify_step():
        raw = classify(image_bgr)
        return _resolve_serving(raw), raw

    cls_out, failure = stage(Stage.CLASSIFY, _oom_guard(_classify_step, degradations),
                             timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info)
    assert cls_out is not None  # successful classify stage returns both blocks
    (classification, dish_info, dish, cls_reason), raw_classification = cls_out
    if dish_info is None:
        scores = raw_classification.get("scores") or {}
        candidates = {key: float(value) for key, value in scores.items()
                      if value is not None and np.isfinite(float(value))}
        if candidates:
            main_cands = {k: v for k, v in candidates.items() if k not in DECOY_SIDE_CLASSES}
            if main_cands:
                candidate = max(main_cands, key=lambda key: main_cands[key])
            else:
                candidate = max(candidates, key=lambda key: candidates[key])

            # Domain saturation check on plain white rice vs spiced vegetable rice
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            bright = (hsv[:, :, 2] > 110) & (image_bgr.mean(axis=2) > 90)
            s_mean = float(np.mean(hsv[bright, 1])) if bright.any() else 100.0
            if s_mean < 50.0 and candidate == "vegetable_rice":
                if "steamed-rice" in candidates and candidates["steamed-rice"] >= candidates["vegetable_rice"] - 0.05:
                    candidate = "steamed-rice"
                elif "rice_sambar" in candidates and candidates["rice_sambar"] >= candidates["vegetable_rice"] - 0.05:
                    candidate = "rice_sambar"

            # If grain dish was picked and a separate katori / secondary vessel exists, promote to combo
            if candidate in ("steamed-rice", "vegetable_rice"):
                has_katori = any(it.get("is_secondary_vessel") for it in (seg.get("items") or []))
                if has_katori and ("rice_sambar" in candidates or "rice_sambar" in menu["dishes"]):
                    candidate = "rice_sambar"

            note = (
                "The classifier's best food label was below its acceptance "
                f"threshold; {candidate} is used only for a tentative meal "
                "estimate. No compliance verdict will be produced.")
            raw_classification = dict(raw_classification, dish=candidate,
                                      reason=note)
            classification, dish_info, dish, cls_reason = _resolve_serving(
                raw_classification)
            estimate_only_notes.append(note)
        else:
            return finish(Analysis(
                verdict="cannot_verify",
                reasons=[Reason(ReasonKind.UNRECOGNIZED,
                                f"dish unrecognized: {cls_reason}")],
                lint=lint, anchor=anchor_info, segmentation=seg_info,
                classification=classification))

    # A tentative label must still resolve to a serving and nutrition row.
    # Do not let an inconsistent classifier payload reach portioning.
    if dish_info is None or dish is None:
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

    # Detect meal structure before mode-specific serving paths. In particular,
    # the off-menu ingredient route must not return a whole plate as one
    # serving before checking whether the photo contains several vessels.
    segment_items_fn = (deps["segment_items"] if "segment_items" in deps
                        else _get_segment_items())
    try:
        items_det = _oom_guard(lambda: segment_items_fn(image_bgr),
                               degradations)()
    except Exception as e:
        log.warning("multi-item detection failed (%s) — withholding meal "
                    "totals", e)
        if "multi_item_detection_failed" not in degradations:
            degradations.append("multi_item_detection_failed")
        items_det = None
    detected_items = (items_det.get("items")
                      if isinstance(items_det, dict) else None)
    if (isinstance(items_det, dict)
            and isinstance(detected_items, list)
            and detected_items
            and items_det.get("strategy") in {"grid9_box", "dense_grid_box"}
            and (seg_info or {}).get("strategy") != "wed_deeplabv3_semantic"):
        detected_items = _reconcile_dense_grid_items(
            detected_items, mask, card_mask, seg_info)
    if card_mask is not None and isinstance(detected_items, list):
        filtered_items = []
        for it in detected_items:
            m = np.asarray(it.get("mask"), dtype=bool)
            if m.any():
                overlap = float((m & card_mask).sum()) / float(m.sum())
                if overlap >= 0.15:
                    continue
                m_clean = m & ~card_mask
                if m_clean.sum() < 64:
                    continue
                it_clean = dict(it, mask=m_clean, area=int(m_clean.sum()))
                ys, xs = np.nonzero(m_clean)
                if len(xs):
                    it_clean["bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
                filtered_items.append(it_clean)
            else:
                filtered_items.append(it)
        if filtered_items:
            detected_items = filtered_items
    if (not isinstance(detected_items, list) or not detected_items):
        if "multi_item_detection_failed" not in degradations:
            degradations.append("multi_item_detection_failed")
        note = (
            "The multi-item detector did not return usable regions. The "
            "top-level food mask is used as one tentative meal estimate; "
            "item separation and school compliance are not verified.")
        estimate_only_notes.append(note)
        detected_items = [{
            "mask": mask,
            "sam_score": seg_info.get("sam_score"),
            "area_frac": seg_info.get("area_frac", float(mask.mean())),
            "bbox": None,
        }]
        items_det = {"items": detected_items,
                     "strategy": "top-level-food-mask-fallback",
                     "candidate_count": 0,
                     "truncated_count": 0}
        seg_info = {**(seg_info or {}),
                    "multi_item_status": "whole-mask-estimate"}
    assert isinstance(items_det, dict) and isinstance(detected_items, list)
    if (len(detected_items) == 1
            and (seg_info or {}).get("strategy") == "wed_deeplabv3_semantic"):
        primary_item_bbox = detected_items[0].get("bbox")
    seg_info = dict(seg_info or {})
    seg_info["item_detection_strategy"] = items_det.get("strategy")
    if items_det.get("candidate_count") is not None:
        seg_info["item_candidate_count"] = int(items_det["candidate_count"])
    if items_det.get("truncated_count") is not None:
        seg_info["truncated_item_count"] = int(items_det["truncated_count"])
    if len(detected_items) == 1:
        seg_info = {**(seg_info or {}), "n_items": 1}
        semantic_name = detected_items[0].get("semantic_class_name")
        if semantic_name:
            classifier_candidate = classification.get("dish")
            semantic_cls = {
                "dish": semantic_name,
                "method": "wed_semantic_region",
                "confidence": None,
                "match_score": None,
                "reason": (
                    "single-region class from frozen WED semantic mask; "
                    f"full-image SigLIP candidate: {classifier_candidate or 'abstained'}"
                ),
            }
            classification, dish_info, dish, cls_reason = _resolve_serving(
                semantic_cls)
    elif (mode == "school" and len(detected_items) > 1
          and items_det.get("strategy") in {"grid9_box", "dense_grid_box"}):
        note = (
            "The automatic multi-item detector has no validated measure of "
            "whole-meal coverage. Item-level grams and nutrients are "
            "provisional, so a School compliance verdict is withheld.")
        estimate_only_notes.append(note)
        seg_info["multi_item_status"] = "coverage-unverified"

    # --- general-mode ingredient route (ledger 013, ticket 07e) -----------
    # OFF-MENU dishes only. Head checkpoint absent/failed -> None and the
    # flow below runs byte-for-byte unchanged (fallback criterion); a route
    # that cannot match a recipe returns None through the stage Failure and
    # also falls through, with a machine-readable degradation tag.
    ing_head = (deps["ingredient_head"] if "ingredient_head" in deps
                else _get_ingredient_head())
    if (mode == "general"
            and len(detected_items) < 2
            and ing_head is not None
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
            unexplained_g = float(route.get("unexplained_g") or 0.0)
            assumptions = []
            if unexplained_g > 1e-6:
                assumptions.append(
                    f"{unexplained_g:.1f} g of predicted ingredient mass "
                    "could not be matched to the recipe and was excluded "
                    "from the portion and nutrient estimates")
            reasons = [Reason(
                ReasonKind.OFF_MENU,
                f"recognized off-menu dish "
                f"{dish.get('display_name') or dish_info['id']} — not on the "
                "school menu, so no compliance verdict; grams and nutrients "
                "are provided from the ingredient-compositional route")]
            if (anchor or {}).get("label") != "measured":
                reasons.append(no_card_reason(portion))
            for note in estimate_only_notes:
                reasons.append(Reason(ReasonKind.UNRECOGNIZED, note))
            assumptions.extend(estimate_only_notes)
            return finish(Analysis(
                verdict="ESTIMATED" if estimate_only_notes else "cannot_verify",
                reasons=reasons,
                lint=lint,
                anchor=anchor_info,
                segmentation=seg_info,
                classification=classification,
                dish=dish_info,
                portion=_portion_wire_block(portion),
                nutrition=route["nutrition"],
                assumptions=assumptions,
                model_versions=_model_versions(None, ing_head),
            ))
        if ing_failure is not None:
            if "ingredient_head_route_failed" not in degradations:
                degradations.append("ingredient_head_route_failed")
            log.warning("ingredient route unavailable (%s) — existing off-menu "
                        "path continues", ing_failure.error)

    # --- depth stage (monocular depth + anchor calibration) ---------------
    def _depth_step():
        active_depth_fn = depth_fn or _get_depth_provider()
        depth_out = active_depth_fn(image_bgr, fov_x=fov_x)
        depth_m = np.asarray(depth_out["depth_m"], dtype=np.float64)
        depth_K = normalized_intrinsics_to_pixel_K(
            depth_out.get("intrinsics"), _W, _H)
        active_anchor = anchor
        if depth_K is None:
            depth_K = K
        else:
            anchor_cfg = load_anchor_config()
            active_anchor = refine_anchor_pose(
                anchor, depth_K,
                anchor_cfg["camera"].get("max_pose_reproj_err_px", 3.0))
        scale_factor, scale_source = 1.0, "none"
        if active_anchor.get("label") == "measured":
            depth_m, scale_factor, scale_source = calibrate_depth_scale(
                depth_m, active_anchor, depth_K)
            if scale_source != "card":
                raise ValueError(
                    "measured marker was not sufficient to calibrate metric depth")
        return (depth_out, depth_m, depth_K, active_anchor,
                scale_factor, scale_source)

    if (anchor or {}).get("label") == "measured":
        depth_result, failure = stage(
            Stage.DEPTH, _oom_guard(_depth_step, degradations),
            timings=timings)
        if failure:
            return fail(failure, lint=lint, anchor=anchor_info,
                        segmentation=seg_info, classification=classification,
                        dish=dish_info)
        (depth_out, depth_m, depth_K, anchor,
         scale_factor, scale_source) = depth_result
    else:
        # Card-free implicit scale and depth calibration (ADR/Ledger 036)
        implicit_head = (
            deps.get("implicit_scale_head")
            if (deps and "implicit_scale_head" in deps)
            else (None if deps else _get_implicit_scale_head())
        )
        if implicit_head is not None and anchor is not None:
            try:
                scale_info = implicit_head.predict(image_bgr)
                if anchor.get("cm_per_px") is None:
                    anchor["cm_per_px"] = scale_info["cm_per_px"]
                    anchor["interval"] = scale_info["cm_per_px_interval"]
                    anchor["method"] = "implicit_scale"
                    anchor["extras"] = {
                        **(anchor.get("extras") or {}),
                        "implicit_depth_scale": scale_info["depth_scale_factor"],
                        "implicit_mass_g": scale_info["estimated_mass_g"],
                    }
            except Exception as e:
                log.warning("implicit scale prediction failed (%s)", e)

        if implicit_head is not None and anchor and anchor.get("cm_per_px") is not None:
            active_depth_fn = depth_fn or _get_depth_provider()
            try:
                depth_out = active_depth_fn(image_bgr, fov_x=fov_x)
                depth_m = np.asarray(depth_out["depth_m"], dtype=np.float64)
                depth_K = normalized_intrinsics_to_pixel_K(
                    depth_out.get("intrinsics"), _W, _H)
                if depth_K is None:
                    depth_K = K
                scale_factor = (anchor.get("extras") or {}).get("implicit_depth_scale", 0.1152)
                scale_source = "implicit_scale"
                depth_m = depth_m * scale_factor
            except Exception:
                depth_out, depth_m, depth_K = None, None, K
                scale_factor, scale_source = 1.0, "none"
        else:
            depth_out, depth_m, depth_K = None, None, K
            scale_factor, scale_source = 1.0, "none"
    anchor_info = _anchor_summary(anchor)
    depth_model = depth_out.get("model") if depth_out is not None else None

    head = deps["weight_head"] if "weight_head" in deps else _get_weight_head()

    # --- multi-item path (spec 003) ---------------------------------------
    # Structure detection runs on every recognized, in-scope meal before the
    # school/general serving paths. A positive one-vessel result keeps the
    # single-serving path; detected multi-vessel meals are measured separately.

    def _item_portion(item_mask, dish_i, dish_id_i, bbox_mask=None, is_secondary=False):
        """Use learned mass for mapped prior-tier items; otherwise require a
        measured marker before computing geometry mass."""
        if (anchor or {}).get("label") != "measured":
            if _wed_slots_for_dish(dish_id_i) is not None:
                if head is None:
                    raise WeightHeadUnavailable(
                        f"weight head unavailable for {dish_id_i}: "
                        "checkpoint missing or failed to load")
                roi_mask = bbox_mask if bbox_mask is not None else item_mask
                return _learned_portion(image_bgr, roi_mask, dish_i,
                                        dish_id_i, head)
            if anchor and anchor.get("cm_per_px") is not None and depth_m is not None:
                return estimate_portion(image_bgr, item_mask, depth_m, anchor,
                                        {"K": depth_K}, dish_i,
                                        cfg={"base_method": "table_prior"})
            raise ValueError(
                "absolute geometry mass requires a measured marker scale")
        geom_mask = np.asarray(item_mask, dtype=bool)
        parent_mask = np.asarray(mask, dtype=bool)
        if geom_mask.shape != parent_mask.shape:
            raise ValueError("item mask shape mismatch with parent mask")
        item_area = float(geom_mask.sum())
        if item_area <= 0:
            raise ValueError("empty item mask")
        overlap = float((geom_mask & parent_mask).sum())
        in_parent = overlap / max(item_area, 1.0)
        c_mask = np.asarray(card_mask, dtype=bool) if card_mask is not None else np.zeros_like(parent_mask)
        if parent_mask.sum() > 0:
            if in_parent >= 0.50:
                if int(overlap) < 64:
                    raise ValueError("item mask overlap < 64 px")
                geom_mask = geom_mask & parent_mask
            elif is_secondary or _is_valid_secondary_vessel(geom_mask, parent_mask, card_mask, geom_mask.shape[:2]):
                geom_mask = geom_mask & ~parent_mask & ~c_mask
                if int(geom_mask.sum()) < 64:
                    raise ValueError("secondary item mask too small after parent subtraction")
            else:
                raise ValueError(
                    f"item mask mostly outside parent food mask (in_parent {in_parent:.1%} < 50%, overlap {int(overlap)} px < 64 px)"
                )
        if int(geom_mask.sum()) < 64:
            raise ValueError("item mask too small after clipping")

        effective_exclude = parent_mask | (geom_mask if in_parent < 0.50 else np.zeros_like(parent_mask))
        if card_mask is not None:
            effective_exclude = effective_exclude | card_mask

        geometry_cfg = (
            {"base_method": "table_prior", "exclude_mask": effective_exclude}
            if (anchor or {}).get("label") == "measured"
            and depth_model == MOGE_MODEL_ID
            else {"exclude_mask": effective_exclude}
        )
        portion_geom = estimate_portion(image_bgr, geom_mask, depth_m, anchor,
                                        {"K": depth_K}, dish_i, cfg=geometry_cfg)
        if (head is not None
                and _wed_slots_for_dish(dish_id_i) is not None
                and (anchor or {}).get("label") == "measured"
                and depth_model == MOGE_MODEL_ID):
            try:
                roi_mask = bbox_mask if bbox_mask is not None else geom_mask
                portion_head = _learned_portion(image_bgr, roi_mask, dish_i, dish_id_i, head)
                g_geom = float(portion_geom["grams"])
                g_head = float(portion_head["grams"])
                s_geom = float(portion_geom.get("sigma_grams_rel", 0.33))
                s_head = float(portion_head.get("sigma_grams_rel", 0.20))
                w_geom = (s_head ** 2) / (s_geom ** 2 + s_head ** 2)
                w_head = 1.0 - w_geom
                flags = list(portion_geom.get("flags", []))
                if g_geom < 0.55 * g_head or g_geom > 2.0 * g_head:
                    g_fused = 0.35 * g_geom + 0.65 * g_head
                    if g_geom > 2.0 * g_head:
                        flags.append("plate_elevation_bias_clamped")
                    elif g_geom < 0.55 * g_head:
                        flags.append("sub_rim_depth_truncated")
                else:
                    g_fused = w_geom * g_geom + w_head * g_head
                if g_geom > 1e-6:
                    ratio = g_fused / g_geom
                    portion_geom["grams"] = round(g_fused, 1)
                    if portion_geom.get("volume_ml"):
                        eff_density = portion_geom.get("density_eff", 0.85)
                        portion_geom["volume_ml"] = round(g_fused / eff_density, 1)
                    if portion_geom.get("components_g"):
                        shares, _, _ = _components(dish_i)
                        portion_geom["components_g"] = {k: round(g_fused * s, 1) for k, s in shares.items()}
                flags.append("learned_geometry_fused")
                portion_geom["flags"] = list(dict.fromkeys(flags))
            except Exception as e:
                log.warning("WeightHead fusion in item portion skipped (%s)", e)
        return portion_geom

    def _estimated_whole_meal(note, detected_count, item_evidence):
        """Use the full food mask for a qualified estimate after item failure.

        This path provides useful meal totals when individual regions cannot
        be resolved. It deliberately does not produce a school compliance
        score because the assumed whole-mask label/component mapping is not
        independently verified.
        """
        portion, portion_failure = stage(
            Stage.PORTION,
            _oom_guard(lambda: _item_portion(mask, dish, dish_info["id"]),
                       degradations),
            timings=timings)
        if portion_failure is not None:
            return Analysis(
                verdict="cannot_verify",
                reasons=[reason_for_failure(portion_failure)],
                failures=[portion_failure], lint=lint, anchor=anchor_info,
                segmentation={**(seg_info or {}),
                              "item_detection_fallback": "failed"},
                classification=classification, dish=dish_info,
                model_versions=_model_versions(depth_out, head),
                items=item_evidence, path_used="multi_item")
        assert portion is not None
        mc, nutrition_failure = stage(
            Stage.NUTRITION, sample_nutrients, portion, dish, band,
            n=n_mc, seed=seed, timings=timings)
        if nutrition_failure is not None:
            return Analysis(
                verdict="cannot_verify",
                reasons=[reason_for_failure(nutrition_failure)],
                failures=[nutrition_failure], lint=lint, anchor=anchor_info,
                segmentation={**(seg_info or {}),
                              "item_detection_fallback": "failed"},
                classification=classification, dish=dish_info,
                portion=_portion_wire_block(portion),
                model_versions=_model_versions(depth_out, head),
                items=item_evidence, path_used="multi_item")
        assert mc is not None
        fallback_note = (
            f"{note}; totals below use the top-level food mask and the "
            "leading meal label as one estimate. No school compliance "
            "verdict was produced.")
        reasons = [Reason(ReasonKind.ESTIMATE_ONLY, fallback_note)]
        assumptions = [fallback_note, *estimate_only_notes]
        reasons.extend(Reason(ReasonKind.ESTIMATE_ONLY, estimate_note)
                       for estimate_note in estimate_only_notes)
        if (anchor or {}).get("label") != "measured":
            reasons.append(no_card_reason(portion))
        return Analysis(
            verdict="ESTIMATED",
            reasons=reasons,
            lint=lint,
            anchor=anchor_info,
            segmentation={**(seg_info or {}),
                          "n_items": 1,
                          "n_items_detected": int(detected_count),
                          "item_detection_fallback": "top-level-food-mask"},
            classification=classification,
            dish=dish_info,
            portion=_portion_wire_block(portion),
            nutrition={
                "kcal": mc["kcal"], "protein_g": mc["protein_g"],
                "grams": mc["grams"], "n": mc["n"], "seed": mc["seed"],
                "diagnostics": mc["diagnostics"],
                "assumed_nutrients": mc["assumed_nutrients"],
                "wider_ranges": mc["wider_ranges"],
                "nutrition_provenance": mc["nutrition_provenance"],
            },
            assumptions=assumptions,
            model_versions=_model_versions(depth_out, head),
            items=None,
            path_used="multi_item")

    def _multi_item_analysis(items):
        """Portion each vessel separately and judge the aggregate meal.

        Unresolved item labels or component correspondence fall back to a
        clearly marked whole-mask estimate without a compliance verdict.
        Actual portion/nutrition stage failures still return cannot_verify."""
        pad = 0.10
        resolved, skipped = [], []
        classified_items = []
        # Combo decomposition (spec 004): a combo plate restricts each
        # vessel's match to the combo's component serving targets, so the
        # aggregate sums distinct components instead of N x the combo.
        combo = _combo_candidates(dish_info["id"])
        # Filter out tiny embedded artifact islands enclosed within dominant food regions
        total_items_area = float(sum(it.get("area", 0) for it in items))
        filtered_items = []
        for it in items:
            it_area = float(it.get("area", 0))
            it_b = it.get("bbox")
            if total_items_area > 0 and (it_area / total_items_area) < 0.025 and it_b is not None:
                enclosed = False
                for other in items:
                    if other is it:
                        continue
                    o_area = float(other.get("area", 0))
                    ob = other.get("bbox")
                    if (o_area >= 8 * it_area and ob is not None
                            and ob[0] <= it_b[0] and ob[1] <= it_b[1]
                            and ob[2] >= it_b[2] and ob[3] >= it_b[3]):
                        enclosed = True
                        break
                if enclosed:
                    continue
            filtered_items.append(it)
        if filtered_items:
            items = filtered_items

        for rank, item in enumerate(items):
            semantic_name = item.get("semantic_class_name")
            x0, y0, x1, y1 = item["bbox"]
            pw, ph = int((x1 - x0) * pad), int((y1 - y0) * pad)
            y_min, y_max = max(0, y0 - ph), min(H, y1 + ph)
            x_min, x_max = max(0, x0 - pw), min(W, x1 + pw)
            crop = image_bgr[y_min:y_max, x_min:x_max].copy()
            if "mask" in item:
                item_mask_crop = np.asarray(item["mask"][y_min:y_max, x_min:x_max], dtype=np.uint8)
                if item_mask_crop.sum() > 0:
                    kernel_15 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
                    dilated = cv2.dilate(item_mask_crop, kernel_15) > 0
                    crop_f = crop.astype(np.float32)
                    bg_mask = ~dilated
                    if dilated.any():
                        mean_rgb = crop_f[dilated].mean(axis=(0, 1))
                    else:
                        mean_rgb = np.array([128.0, 128.0, 128.0], dtype=np.float32)
                    crop_f[bg_mask] = 0.35 * crop_f[bg_mask] + 0.65 * mean_rgb
                    crop = np.clip(crop_f, 0, 255).astype(np.uint8)
            chroma = _mask_core_chromaticity(image_bgr, item.get("mask"), item.get("bbox"))
            try:
                if semantic_name and "classify" not in deps:
                    cls_i = {
                        "dish": semantic_name,
                        "method": "wed_semantic_region",
                        "confidence": None,
                        "match_score": None,
                        "reason": (
                            f"region class from frozen WED semantic mask; "
                            f"SigLIP candidate: {classification.get('dish') or 'abstained'}"
                        ),
                    }
                    is_decoy = semantic_name in ("papad", "salad")
                    if is_decoy or (anchor or {}).get("label") == "measured":
                        cls_crop = _oom_guard(lambda c=crop: classify(c),
                                              degradations)()
                        crop_scores = (cls_crop or {}).get("scores") or {}
                        crop_dish = (cls_crop or {}).get("dish")
                        ms = float((cls_crop or {}).get("match_score") or 0.0)
                        sem_score = float(crop_scores.get(semantic_name, 0.0))
                        if is_decoy:
                            # Papad and salad are frequent DeepLabV3 spurious artifacts on plate rims,
                            # specular highlights, and card margins.
                            if chroma["mean_s"] < 40 or chroma["specular_frac"] > 0.12 or ms < 0.88:
                                continue
                            if crop_dish == semantic_name and ms >= 0.88:
                                pass
                            elif crop_dish and ms >= 0.85 and crop_dish not in DECOY_SIDE_CLASSES:
                                cls_i = dict(
                                    cls_crop,
                                    reason=f"SigLIP verified serving {crop_dish}={ms:.3f} (overrode decoy WED {semantic_name})",
                                )
                            else:
                                continue
                        else:
                            if crop_dish is None and sem_score < 0.80:
                                continue
                else:
                    cls_i = _oom_guard(lambda c=crop: classify(c),
                                       degradations)()

                crop_dish = cls_i.get("dish")
                ms = float(cls_i.get("match_score") or 0.0)
                if chroma["mean_s"] < 35 and chroma["specular_frac"] > 0.18 and ms < 0.84:
                    continue

                if item.get("is_secondary_vessel"):
                    is_liquid_chroma = (
                        chroma["mean_s"] >= 40
                        and (
                            chroma["mean_h"] <= 50
                            or chroma["mean_h"] >= 155
                            or (35 <= chroma["mean_h"] <= 85)
                        )
                        and chroma["specular_frac"] < 0.25
                    )
                    liq_cand = {k: float(v) for k, v in (cls_i.get("scores") or {}).items()
                                if k in LIQUID_BOWL_CLASSES and v is not None and np.isfinite(float(v))}
                    if is_liquid_chroma and liq_cand:
                        best_liq = max(liq_cand, key=lambda k: liq_cand[k])
                        if "sambar" in liq_cand and liq_cand["sambar"] >= liq_cand[best_liq] - 0.02 and (
                            day == "mon" or "rice_sambar" in (menu.get("dishes") or {})
                        ):
                            best_liq = "sambar"
                        if liq_cand[best_liq] >= 0.82:
                            cls_i = dict(
                                cls_i,
                                dish=best_liq,
                                match_score=liq_cand[best_liq],
                                reason=f"liquid secondary bowl ({best_liq}={liq_cand[best_liq]:.3f}, H={chroma['mean_h']:.1f}, S={chroma['mean_s']:.1f})",
                            )
                            crop_dish = best_liq
                            ms = liq_cand[best_liq]
                    elif crop_dish in ("chutney", "curd", "raita"):
                        if chroma["mean_s"] > 50 and not (35 <= chroma["mean_h"] <= 85):
                            continue
                elif crop_dish in ("chutney", "curd", "raita"):
                    if chroma["mean_s"] >= 55 and (chroma["mean_h"] <= 45 or chroma["mean_h"] >= 160):
                        liq_cand = {k: float(v) for k, v in (cls_i.get("scores") or {}).items()
                                    if k in LIQUID_BOWL_CLASSES and v is not None and np.isfinite(float(v))}
                        if liq_cand:
                            best_liq = max(liq_cand, key=lambda k: liq_cand[k])
                            cls_i = dict(cls_i, dish=best_liq, match_score=liq_cand[best_liq],
                                         reason=f"liquid chromaticity (H={chroma['mean_h']:.1f}, S={chroma['mean_s']:.1f}) re-ranked to {best_liq}")
                            crop_dish = best_liq
                        else:
                            continue
                    elif chroma["mean_s"] > 55 and not (35 <= chroma["mean_h"] <= 85):
                        continue
                elif crop_dish in ("papad", "salad") and (
                    chroma["mean_s"] < 40 or chroma["specular_frac"] > 0.12 or ms < 0.85
                ):
                    continue

                if item.get("is_secondary_vessel") and crop_dish == "rice_sambar":
                    liq_cand = {k: float(v) for k, v in (cls_i.get("scores") or {}).items()
                                if k in LIQUID_BOWL_CLASSES and v is not None and np.isfinite(float(v))}
                    if liq_cand:
                        best_liq = max(liq_cand, key=lambda k: liq_cand[k])
                        cls_i = dict(cls_i, dish=best_liq, match_score=liq_cand[best_liq],
                                     reason=f"katori bowl re-ranked from rice_sambar to {best_liq}")
                        crop_dish = best_liq
                        ms = liq_cand[best_liq]

                if combo and not semantic_name and cls_i.get("scores"):
                    from models.food_classifier import gallery_match_threshold
                    cand = {k: float(v) for k, v in cls_i["scores"].items()
                            if k in combo and v is not None
                            and np.isfinite(float(v))}
                    if cand:
                        best = max(cand, key=lambda key: cand[key])
                        match_score = float(cand[best])
                        if best == "vegetable_rice" and chroma["mean_s"] < 50.0 and "steamed-rice" in combo:
                            best = "steamed-rice"
                            match_score = float(cls_i["scores"].get("steamed-rice", match_score))
                        threshold = gallery_match_threshold()
                        low_confidence = (
                            cls_i.get("method") == "gallery"
                            and match_score < threshold)
                        if low_confidence:
                            note = (
                                f"A combo region's best component label was "
                                f"below threshold ({match_score:.3f} < "
                                f"{threshold:.2f}); {best} is used only for "
                                "an estimate, without a compliance verdict.")
                            estimate_only_notes.append(note)
                        cls_i = dict(
                            cls_i,
                            dish=best,
                            reason=(f"tentative combo component {best}="
                                    f"{match_score:.3f}" if low_confidence
                                    else f"combo component match {best}="
                                         f"{match_score:.3f}"),
                        )
                elif not semantic_name and cls_i.get("dish") is None:
                    if item.get("is_secondary_vessel"):
                        continue
                    scores = cls_i.get("scores") or {}
                    cand = {key: float(value) for key, value in scores.items()
                            if value is not None
                            and np.isfinite(float(value))
                            and key not in DECOY_SIDE_CLASSES}
                    if cand:
                        best = max(cand, key=lambda key: cand[key])
                        if cand[best] < 0.74:
                            continue
                        if best == "vegetable_rice" and chroma["mean_s"] < 50.0:
                            best = "steamed-rice"
                        note = (
                            "An item classifier score was below its "
                            f"acceptance threshold; {best} is used only for "
                            "a tentative estimate, without a compliance "
                            "verdict.")
                        estimate_only_notes.append(note)
                        cls_i = dict(cls_i, dish=best, reason=note)
                if item.get("is_secondary_vessel") and not combo:
                    ms = float(cls_i.get("match_score") or 0.0)
                    if ms < 0.82 or cls_i.get("dish") in DECOY_SIDE_CLASSES:
                        continue
                if semantic_name and "classify" in deps:
                    classifier_candidate = cls_i.get("dish")
                    cls_i = dict(
                        cls_i,
                        dish=semantic_name,
                        method="wed_semantic_region",
                        confidence=None,
                        match_score=None,
                        reason=(
                            f"region class from frozen WED semantic mask; "
                            f"SigLIP candidate: {classifier_candidate or 'abstained'}"
                        ),
                    )
                cls_info, info_i, dish_i, reason_i = _resolve_serving(cls_i)
                if info_i and info_i["id"] == "vegetable_rice" and chroma["mean_s"] < 50.0:
                    cls_promoted = dict(cls_i, dish="steamed-rice",
                                        reason="promoted to steamed-rice due to low grain saturation")
                    cls_info, info_i, dish_i, reason_i = _resolve_serving(cls_promoted)
            except Exception as e:
                log.warning("item %d classification failed (%s) — skipped",
                            rank, e)
                skipped.append(_item_wire_block(
                    item, None, None, None,
                    Reason(ReasonKind.STAGE_FAILED,
                           "item could not be classified")))
                continue
            if info_i is None:
                skipped.append(_item_wire_block(
                    item, cls_info, None, None,
                    Reason(ReasonKind.UNRECOGNIZED,
                           f"item skipped: dish unrecognized ({reason_i})")))
                continue
            classified_items.append((item, cls_info, info_i, dish_i))

        # Coalesce same-class proposals when masks overlap or bounding boxes intersect
        coalesced_items = []
        for item, cls_info, info_i, dish_i in classified_items:
            merged = False
            for idx, (c_item, c_cls, c_info, c_dish) in enumerate(coalesced_items):
                same_family = _same_food_family(c_info["id"], info_i["id"])
                both_main = (not item.get("is_secondary_vessel")) and (not c_item.get("is_secondary_vessel"))
                both_sec = bool(item.get("is_secondary_vessel")) and bool(c_item.get("is_secondary_vessel"))
                if same_family and (both_main or both_sec):
                    m1, m2 = item.get("mask"), c_item.get("mask")
                    b1, b2 = item.get("bbox"), c_item.get("bbox")
                    overlap = False
                    if m1 is not None and m2 is not None:
                        overlap = bool((m1 & m2).any())
                    elif b1 is not None and b2 is not None:
                        ix0, iy0 = max(b1[0], b2[0]), max(b1[1], b2[1])
                        ix1, iy1 = min(b1[2], b2[2]), min(b1[3], b2[3])
                        inter_w, inter_h = max(0, ix1 - ix0), max(0, iy1 - iy0)
                        inter_area = inter_w * inter_h
                        min_area = min((b1[2] - b1[0]) * (b1[3] - b1[1]),
                                       (b2[2] - b2[0]) * (b2[3] - b2[1]))
                        if min_area > 0 and (inter_area / min_area) > 0.40:
                            overlap = True
                    if overlap:
                        m_merged = (m1 | m2) if (m1 is not None and m2 is not None) else (m1 or m2)
                        b_merged = None
                        if b1 is not None and b2 is not None:
                            b_merged = [min(b1[0], b2[0]), min(b1[1], b2[1]),
                                        max(b1[2], b2[2]), max(b1[3], b2[3])]
                        elif b1 is not None:
                            b_merged = b1
                        elif b2 is not None:
                            b_merged = b2
                        score_1 = float(item.get("sam_score") or 0.0)
                        score_2 = float(c_item.get("sam_score") or 0.0)
                        merged_item = dict(
                            c_item,
                            mask=m_merged,
                            bbox=b_merged,
                            sam_score=max(score_1, score_2),
                            area_frac=float(m_merged.mean()) if m_merged is not None else c_item.get("area_frac"),
                            is_secondary_vessel=bool(c_item.get("is_secondary_vessel", False) or item.get("is_secondary_vessel", False)),
                        )
                        m_score_1 = float(cls_info.get("match_score") or 0.0)
                        m_score_2 = float(c_cls.get("match_score") or 0.0)
                        best_cls = cls_info if m_score_1 > m_score_2 else c_cls
                        best_info = info_i if m_score_1 > m_score_2 else c_info
                        best_dish = dish_i if m_score_1 > m_score_2 else c_dish
                        coalesced_items[idx] = (merged_item, best_cls, best_info, best_dish)
                        merged = True
                        break
            if not merged:
                coalesced_items.append((item, cls_info, info_i, dish_i))

        if len(coalesced_items) == 1 and not coalesced_items[0][0].get("is_secondary_vessel"):
            coalesced_items[0][0]["mask"] = mask
            ys, xs = np.nonzero(mask)
            if len(xs):
                coalesced_items[0][0]["bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
            coalesced_items[0][0]["area_frac"] = float(mask.mean())

        for rank, (item, cls_info, info_i, dish_i) in enumerate(coalesced_items):
            try:
                portion_i = _oom_guard(
                    lambda m=item["mask"], bm=item.get("bbox_mask"), d=dish_i, k=info_i["id"], sec=item.get("is_secondary_vessel", False):
                    _item_portion(m, d, k, bbox_mask=bm, is_secondary=sec),
                    degradations)()
            except Exception as e:
                log.warning("item %d portion failed (%s) — skipped", rank, e)
                skipped.append(_item_wire_block(
                    item, cls_info, info_i, None,
                    Reason(ReasonKind.STAGE_FAILED,
                           "item portion could not be measured")))
                continue
            mc_i, mc_failure = stage(Stage.NUTRITION, sample_nutrients,
                                     portion_i, dish_i, band, n=n_mc,
                                     seed=seed + 1 + rank,
                                     component_prefix=info_i["id"],
                                     timings=timings)
            if mc_failure is not None:
                skipped.append(_item_wire_block(
                    item, cls_info, info_i, None,
                    Reason(ReasonKind.STAGE_FAILED,
                           "item nutrition could not be estimated")))
                continue
            resolved.append((item, cls_info, info_i, dish_i, portion_i, mc_i))
        item_evidence = [
            _item_wire_block(it, ci, ii, pi)
            for it, ci, ii, _d, pi, _m in resolved
        ] + skipped
        if not resolved:
            note = ("None of the detected food regions could be identified "
                    "and measured")
            return _estimated_whole_meal(note, len(items), item_evidence)
        if skipped:
            note = (f"{len(skipped)} detected item(s) could not be measured; "
                    "so the item-level total is incomplete")
            return _estimated_whole_meal(note, len(items), item_evidence)

        labels = [entry[2]["id"] for entry in resolved]
        if combo and sorted(labels) != sorted(combo):
            expected = ", ".join(combo)
            found = ", ".join(labels) or "none"
            note = ("Detected regions did not resolve to each expected meal "
                    f"component exactly once (expected: {expected}; found: "
                    f"{found})")
            return _estimated_whole_meal(note, len(items), item_evidence)
        portions = [r[4] for r in resolved]
        total_g = float(sum(p["grams"] for p in portions))
        _append_plate_sanity_note(lint, total_g, band)
        total_v = float(sum(p["volume_ml"] for p in portions))
        comp_g: dict[str, float] = {}
        agg_components: dict[str, dict] = {}
        for _item, _c, info_i, dish_i, portion_i, _m in resolved:
            for nm, g in portion_i["components_g"].items():
                key = f"{info_i['id']}:{nm}"
                comp_g[key] = comp_g.get(key, 0.0) + float(g)
                if key not in agg_components:
                    src = dish_i["components"][nm]
                    agg_components[key] = {"share": 0.0,
                                           "generic_id": src["generic_id"],
                                           "type": src.get("type", "grain")}
        for key, g in comp_g.items():
            agg_components[key]["share"] = g / total_g if total_g > 0 else 0.0
        item_sigmas = [float(p["grams"] * p["sigma_grams_rel"]) for p in portions]
        indep_var = sum(s * s for s in item_sigmas)
        rho_plate = 0.25 if len(item_sigmas) > 1 else 0.0
        var = (1.0 - rho_plate) * indep_var + rho_plate * (sum(item_sigmas) ** 2)
        sigma_agg = float(np.sqrt(var) / total_g) if total_g > 0 else 0.0
        agg_portion = {
            "grams": total_g,
            "volume_ml": total_v,
            "density_eff": total_g / total_v if total_v > 0 else 0.0,
            "components_g": comp_g,
            "base_method": ("table_prior" if any(
                p["base_method"] == "table_prior" for p in portions)
                else "multi_item"),
            "scale_tier": portions[0]["scale_tier"],
            "grams_source": ("learned_weight" if all(
                p.get("grams_source") == "learned_weight" for p in portions)
                else "geometry"),
            "mean_h_mm": None,
            "area_cm2": (float(sum(p["area_cm2"] for p in portions))
                         if all(p.get("area_cm2") is not None
                                for p in portions) else None),
            "sigma_grams_rel": sigma_agg,
            "sigma_rel": {"multi_item": sigma_agg},
            "flags": sorted({f for p in portions for f in p["flags"]}
                            | {"multi_item_meal"}),
        }
        agg_mc = aggregate_meal([r[5] for r in resolved])
        matched_menu_dish = None
        has_rice = any(_same_food_family(r[2]["id"], "rice") for r in resolved)
        has_dal = any(_same_food_family(r[2]["id"], "dal") for r in resolved)
        if has_rice and has_dal:
            matched_menu_dish = (menu.get("dishes") or {}).get("rice_sambar")

        if matched_menu_dish and matched_menu_dish.get("display_name"):
            agg_dish_name = "Rice + Sambar"
        else:
            seen_families = set()
            unique_names = []
            for _i, _c, info_i, _d, _p, _m in resolved:
                fam = ("rice" if _same_food_family(info_i["id"], "rice")
                       else ("dal" if _same_food_family(info_i["id"], "dal")
                       else info_i["id"]))
                if fam not in seen_families:
                    seen_families.add(fam)
                    dn = info_i.get("display_name") or info_i["id"]
                    unique_names.append(dn)
            agg_dish_name = " + ".join(unique_names)
        agg_days = list(matched_menu_dish.get("days") or []) if matched_menu_dish else []

        agg_dish = {
            "components": agg_components,
            "display_name": agg_dish_name,
            "days": agg_days,
            "nutrition_source": "multi_item_aggregate",
            "ranges_wider": any(bool(d.get("ranges_wider"))
                                for _i, _c, _inf, d, _p, _m in resolved),
        }
        if mode == "general" or estimate_only_notes:
            score, a_failure = None, None
        else:
            score, a_failure = stage(
                Stage.COMPLIANCE, assess, agg_mc, agg_portion, agg_dish, band,
                (anchor or {}).get("label", "prior"), day=day,
                depth_scale_source=scale_source, timings=timings)
        if a_failure is not None:
            log.warning("multi-item aggregate assess failed (%s)",
                        a_failure.error)
            if "multi_item_aggregate_failed" not in degradations:
                degradations.append("multi_item_aggregate_failed")
            return Analysis(
                verdict="cannot_verify",
                reasons=[reason_for_failure(a_failure)],
                failures=[a_failure],
                lint=lint,
                anchor=anchor_info,
                segmentation={**(seg_info or {}), "n_items": len(items)},
                classification=classification,
                dish=dish_info,
                portion=_portion_wire_block(agg_portion),
                nutrition={
                    "kcal": agg_mc["kcal"], "protein_g": agg_mc["protein_g"],
                    "grams": agg_mc["grams"], "n": agg_mc["n"],
                    "seed": agg_mc["seed"], "diagnostics": agg_mc["diagnostics"],
                    "assumed_nutrients": agg_mc["assumed_nutrients"],
                    "wider_ranges": agg_mc["wider_ranges"],
                },
                model_versions=_model_versions(depth_out, head),
                items=item_evidence,
                path_used="multi_item",
            )
        names = agg_dish["display_name"]
        meal_on_day = (day in agg_days) if agg_days else dish_info.get("on_day", True)
        meal_info = {"id": "meal", "display_name": names, "day": day,
                     "band": band, "serving_style": serving_style or ("single" if matched_menu_dish else None),
                     "on_day": meal_on_day,
                     "nutrition_source": "multi_item_aggregate"}
        if score is not None:
            verdict = score.verdict
            reasons = list(score.reasons)
            failures = list(score.failures)
            assumptions = list(score.assumptions)
            coverage = score.coverage
            advisory = score.advisory
            compliance = {"day": score.day, "band": score.band,
                          "probs": score.probs, "nutrients": score.nutrients}
        else:
            verdict = "ESTIMATED" if estimate_only_notes else "cannot_verify"
            reasons = []
            if dish_info["id"] not in ((menu or {}).get("dishes") or {}):
                reasons.append(Reason(
                    ReasonKind.OFF_MENU,
                    f"recognized off-menu meal {names} — no school compliance "
                    "verdict; grams and nutrients are provided",
                ))
            if (anchor or {}).get("label") != "measured":
                reasons.append(no_card_reason(agg_portion))
            failures = []
            assumptions = []
            coverage = advisory = compliance = None
        density_note = _density_assumption(agg_portion)
        if density_note:
            assumptions.append(density_note)
        if estimate_only_notes:
            verdict = "ESTIMATED"
            reasons.extend(Reason(ReasonKind.ESTIMATE_ONLY, note)
                           for note in estimate_only_notes)
            assumptions.extend(estimate_only_notes)
        assumptions.append(
            f"wed_semantic_class_regions: {len(resolved)} predicted food-class "
            "regions estimated separately and summed; this does not verify "
            "serving instances or complete meal coverage"
            if (seg_info or {}).get("strategy") == "wed_deeplabv3_semantic"
            else f"multi_item_meal: {len(resolved)} servings measured "
                 "separately and summed")
        repeated_labels = sorted({label for label in labels
                                  if labels.count(label) > 1})
        if repeated_labels:
            assumptions.append(
                "repeated_food_regions: separate detected servings shared "
                "the same food label (" + ", ".join(repeated_labels) + ")")
        if skipped:
            assumptions.append(
                f"{len(skipped)} detected item(s) unrecognized or "
                "unmeasurable — excluded from the aggregate")
        if overlap_resolution_note:
            assumptions.append(overlap_resolution_note)
        if combo:
            assumptions.append(
                f"combo_decomposition: plate-level {dish_info['id']}; vessels "
                f"matched among its component servings ({', '.join(combo)})")
        anchor_blk = dict(anchor_info or {})
        anchor_blk["depth_scale_factor"] = round(float(scale_factor), 4)
        anchor_blk["depth_scale_source"] = scale_source
        seg_multi = dict(seg_info or {})
        seg_multi["n_items"] = len(resolved)
        analysis = Analysis(
            verdict=verdict,
            reasons=reasons,
            failures=failures,
            lint=lint,
            anchor=anchor_blk,
            segmentation=seg_multi,
            classification=classification,
            dish=meal_info,
            portion=_portion_wire_block(agg_portion),
            nutrition={
                "kcal": agg_mc["kcal"], "protein_g": agg_mc["protein_g"],
                "grams": agg_mc["grams"], "n": agg_mc["n"],
                "seed": agg_mc["seed"], "diagnostics": agg_mc["diagnostics"],
                "assumed_nutrients": agg_mc["assumed_nutrients"],
                "wider_ranges": agg_mc["wider_ranges"],
            },
            coverage=coverage,
            assumptions=assumptions,
            advisory=advisory,
            compliance=compliance,
            model_versions=_model_versions(depth_out, head),
            items=[_item_wire_block(it, ci, ii, pi)
                   for it, ci, ii, _d, pi, _m in resolved] + skipped,
        )
        analysis.path_used = "multi_item"
        return analysis

    overlap_resolution_note = None
    if len(detected_items) >= 2:
        if items_det.get("truncated_count", 0):
            note = (
                "More distinct regions were detected than the per-item "
                "limit can process. The top-level food mask is used for one "
                "tentative meal estimate, without a compliance verdict.")
            estimate_only_notes.append(note)
            detected_items = [{
                "mask": mask,
                "sam_score": seg_info.get("sam_score"),
                "area_frac": seg_info.get("area_frac", float(mask.mean())),
                "bbox": None,
            }]
            seg_info = {
                **(seg_info or {}),
                "multi_item_status": "whole-mask-estimate",
                "n_items_detected": int(items_det.get("candidate_count") or
                                         len(detected_items)),
            }
        valid_food_envelope = np.asarray(mask, dtype=bool)
        c_mask = np.asarray(card_mask, dtype=bool) if card_mask is not None else np.zeros_like(valid_food_envelope)
        clipped_items = []
        for item in detected_items:
            m = np.asarray(item.get("mask"), dtype=bool)
            if m.shape == valid_food_envelope.shape:
                item_ar = float(m.sum())
                in_top = float((m & valid_food_envelope).sum()) / max(item_ar, 1.0)
                if in_top >= 0.50:
                    m_clipped = m & valid_food_envelope & ~c_mask
                elif item.get("is_secondary_vessel") or _is_valid_secondary_vessel(m, valid_food_envelope, card_mask, m.shape[:2]):
                    m_clipped = m & ~valid_food_envelope & ~c_mask
                else:
                    m_clipped = np.zeros_like(m)
                if m_clipped.sum() >= 64:
                    item_copy = dict(item, mask=m_clipped)
                    if item.get("bbox") is not None:
                        ys, xs = np.nonzero(m_clipped)
                        if len(xs):
                            item_copy["bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
                    clipped_items.append(item_copy)
        if clipped_items:
            detected_items = clipped_items

        masks = [item.get("mask") for item in detected_items]
        pair_fractions = [frac for _, _, frac in _mask_overlap_pairs(masks)]
        if pair_fractions:
            overlap_counts = np.zeros(masks[0].shape, dtype=np.uint8)
            for item_mask in masks:
                overlap_counts += np.asarray(item_mask, dtype=bool)
            overlap_pixels = int((overlap_counts > 1).sum())
            before_count = len(detected_items)
            detected_items = _assign_boundary_overlap(detected_items)
            overlap_resolution_note = (
                "Detected masks overlapped; shared pixels were assigned once "
                "to the nearest region interior before portion estimation")
            seg_info = {
                **(seg_info or {}),
                "overlap_resolution": "nearest-exclusive-region",
                "overlap_pairs_resolved": len(pair_fractions),
                "overlap_pixels_assigned": overlap_pixels,
                "duplicate_regions_removed": before_count - len(detected_items),
            }
        if len(detected_items) >= 2:
            return finish(_multi_item_analysis(detected_items))
        # If overlap partitioning removes a duplicate mask, continue through
        # the ordinary whole-serving estimator rather than measuring the same
        # vessel twice.
        seg_info = {**(seg_info or {}), "n_items": len(detected_items)}

    # --- portion stage ----------------------------------------------------
    # Learned path (prior tier only): head.predict -> grams. An absent head
    # (checkpoint missing/load failed) and a failing head are treated the
    # same on a WED-mapped dish: WeightHeadUnavailable -> cannot_verify with
    # the weight_head_unavailable reason, no grams, path_used null. Unmapped
    # prior-tier dishes also abstain because absolute geometry has no scale.

    def _portion_step():
        if anchor.get("label") != "measured":
            if _wed_slots_for_dish(dish_info["id"]) is not None:
                if head is None:
                    raise WeightHeadUnavailable(
                        f"weight head unavailable for {dish_info['id']}: "
                        "checkpoint missing or failed to load")
                try:
                    roi_mask = (detected_items[0]["bbox_mask"]
                                if len(detected_items) == 1
                                and detected_items[0].get("bbox_mask") is not None
                                else mask)
                    return _learned_portion(image_bgr, roi_mask, dish,
                                            dish_info["id"], head)
                except Exception as e:
                    if _is_oom(e):
                        raise  # _oom_guard retries; a second OOM is a Failure
                    raise WeightHeadUnavailable(
                        f"learned weight head failed: {type(e).__name__}: {e}"
                    ) from e
            if anchor and anchor.get("cm_per_px") is not None and depth_m is not None:
                return estimate_portion(image_bgr, mask, depth_m, anchor,
                                        {"K": depth_K}, dish,
                                        cfg={"base_method": "table_prior"})
            raise ValueError(
                "absolute geometry mass requires a measured marker scale")
        # Real MoGe ring fits follow the food surface on phone captures and
        # inflate thickness. The outside table plane is the validated real-
        # capture path (ledger 015); synthetic/GT depth keeps the ring path.
        geometry_cfg = (
            {"base_method": "table_prior"}
            if (anchor or {}).get("label") == "measured"
            and depth_model == MOGE_MODEL_ID
            else {}
        )
        portion_geom = estimate_portion(image_bgr, mask, depth_m, anchor,
                                        {"K": depth_K}, dish,
                                        cfg=geometry_cfg)
        dish_id = dish_info.get("id")
        if (head is not None
                and dish_id is not None
                and _wed_slots_for_dish(dish_id) is not None
                and (anchor or {}).get("label") == "measured"
                and depth_model == MOGE_MODEL_ID):
            try:
                portion_head = _learned_portion(image_bgr, mask, dish, dish_id, head)
                g_geom = float(portion_geom["grams"])
                g_head = float(portion_head["grams"])
                s_geom = float(portion_geom.get("sigma_grams_rel", 0.33))
                s_head = float(portion_head.get("sigma_grams_rel", 0.20))
                w_geom = (s_head ** 2) / (s_geom ** 2 + s_head ** 2)
                w_head = 1.0 - w_geom
                flags = list(portion_geom.get("flags", []))
                if g_geom < 0.55 * g_head or g_geom > 2.0 * g_head:
                    g_fused = 0.35 * g_geom + 0.65 * g_head
                    if g_geom > 2.0 * g_head:
                        flags.append("plate_elevation_bias_clamped")
                    elif g_geom < 0.55 * g_head:
                        flags.append("sub_rim_depth_truncated")
                else:
                    g_fused = w_geom * g_geom + w_head * g_head
                if g_geom > 1e-6:
                    ratio = g_fused / g_geom
                    portion_geom["grams"] = round(g_fused, 1)
                    if portion_geom.get("volume_ml"):
                        eff_density = portion_geom.get("density_eff", 0.85)
                        portion_geom["volume_ml"] = round(g_fused / eff_density, 1)
                    if portion_geom.get("components_g"):
                        shares, _, _ = _components(dish)
                        portion_geom["components_g"] = {k: round(g_fused * s, 1) for k, s in shares.items()}
                flags.append("learned_geometry_fused")
                portion_geom["flags"] = list(dict.fromkeys(flags))
            except Exception as e:
                log.warning("WeightHead fusion in single flow skipped (%s)", e)
        return portion_geom

    portion, failure = stage(Stage.PORTION, _oom_guard(_portion_step, degradations),
                             timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info, classification=classification,
                    dish=dish_info)
    assert portion is not None
    portion_block = _portion_wire_block(portion)
    _append_plate_sanity_note(lint, float(portion["grams"]), band)

    # --- nutrition stage (Monte Carlo) ------------------------------------
    mc, failure = stage(Stage.NUTRITION, sample_nutrients, portion, dish, band,
                        n=n_mc, seed=seed, timings=timings)
    if failure:
        return fail(failure, lint=lint, anchor=anchor_info,
                    segmentation=seg_info, classification=classification,
                    dish=dish_info, portion=portion_block)
    assert mc is not None
    nutrition_block = {
        "kcal": mc["kcal"], "protein_g": mc["protein_g"],
        "grams": mc["grams"],
        "n": mc["n"], "seed": mc["seed"],
        "diagnostics": mc["diagnostics"],
        "assumed_nutrients": mc["assumed_nutrients"],
        "wider_ranges": mc["wider_ranges"],
        "nutrition_provenance": mc["nutrition_provenance"],
    }

    # General mode compares this estimate with personal daily goals and does
    # not produce a school-standards verdict. School mode assesses every
    # recognized WED class; off-menu generic nutrient rows are explicitly
    # marked assumed in the nutrition block and assessment assumptions.
    if mode == "general":
        anchor_info = anchor_info or {}
        anchor_info["depth_scale_factor"] = round(float(scale_factor), 4)
        anchor_info["depth_scale_source"] = scale_source
        name = dish.get("display_name") or dish_info["id"]
        reasons = []
        if dish_info["id"] not in ((menu or {}).get("dishes") or {}):
            reasons.append(Reason(
                ReasonKind.OFF_MENU,
                f"recognized off-menu dish {name} — no school compliance "
                "verdict; grams and nutrients are provided"))
        if (anchor or {}).get("label") != "measured":
            reasons.append(no_card_reason(portion))
        assumptions = [
            f"generic nutrient row {gid} is an assumed estimate"
            for gid in mc.get("assumed_nutrients", [])
        ]
        density_note = _density_assumption(portion)
        if density_note:
            assumptions.append(density_note)
        if overlap_resolution_note:
            assumptions.append(overlap_resolution_note)
        if estimate_only_notes:
            reasons.extend(Reason(ReasonKind.ESTIMATE_ONLY, note)
                           for note in estimate_only_notes)
            assumptions.extend(estimate_only_notes)
        return finish(Analysis(
            verdict="ESTIMATED" if estimate_only_notes else "cannot_verify",
            reasons=reasons,
            lint=lint,
            anchor=anchor_info,
            segmentation=seg_info,
            classification=classification,
            dish=dish_info,
            portion=portion_block,
            nutrition=nutrition_block,
            assumptions=assumptions,
            model_versions=_model_versions(depth_out, head),
        ))

    if estimate_only_notes:
        anchor_info = dict(anchor_info or {})
        anchor_info["depth_scale_factor"] = round(float(scale_factor), 4)
        anchor_info["depth_scale_source"] = scale_source
        reasons = [Reason(ReasonKind.ESTIMATE_ONLY, note)
                   for note in estimate_only_notes]
        if (anchor or {}).get("label") != "measured":
            reasons.append(no_card_reason(portion))
        assumptions = list(estimate_only_notes)
        density_note = _density_assumption(portion)
        if density_note:
            assumptions.append(density_note)
        if overlap_resolution_note:
            assumptions.append(overlap_resolution_note)
        return finish(Analysis(
            verdict="ESTIMATED",
            reasons=reasons,
            lint=lint,
            anchor=anchor_info,
            segmentation=seg_info,
            classification=classification,
            dish=dish_info,
            portion=portion_block,
            nutrition=nutrition_block,
            assumptions=assumptions,
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
    assumptions = list(score.assumptions)
    density_note = _density_assumption(portion)
    if density_note:
        assumptions.append(density_note)
    if overlap_resolution_note:
        assumptions.append(overlap_resolution_note)

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
        assumptions=assumptions,
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


def _density_assumption(portion: dict) -> str | None:
    """Keep configured density provenance visible without changing the wire shape."""
    if portion.get("grams_source", "geometry") != "geometry":
        return None
    return ("geometry mass uses configured class/component density from "
            "data/wed_dishes.yaml; density uncertainty follows the declared "
            "density_sigma_pct status in data/params_status.yaml")


def _mask_overlap_pairs(masks):
    """Yield (i, j, inter/smaller) for mask pairs that share pixels."""
    for i in range(len(masks)):
        a = masks[i]
        if a is None:
            continue
        for j in range(i + 1, len(masks)):
            b = masks[j]
            if b is None:
                continue
            inter = float(np.logical_and(a, b).sum())
            if inter == 0:
                continue
            smaller = min(float(a.sum()), float(b.sum()))
            yield i, j, (inter / smaller if smaller else 1.0)


def _assign_boundary_overlap(items):
    """Partition every shared pixel once, assigning it to its nearest region.

    SAM proposals can overlap substantially even when they describe separate
    foods. Abstaining on an arbitrary overlap percentage discarded these
    meals; assigning all shared pixels to the largest proposal also distorted
    small portions. This uses each mask's exclusive pixels as spatial seeds,
    then assigns contested pixels to the nearest seed. A mask without an
    exclusive core uses its deepest interior pixel as its seed. Identical
    proposals resolve deterministically by score and area, and empty duplicate
    masks are removed. The output masks are disjoint and preserve the input
    union.
    """
    if not items:
        return []
    import cv2

    masks = [np.asarray(item["mask"], dtype=bool) for item in items]
    shape = masks[0].shape
    if any(mask.shape != shape for mask in masks):
        raise ValueError("overlapping food masks must have the same shape")

    counts = np.zeros(shape, dtype=np.uint8)
    for mask in masks:
        counts += mask
    union = counts > 0
    contested = counts > 1
    if not contested.any():
        return items

    seeds = []
    for index, mask in enumerate(masks):
        other_union = np.zeros(shape, dtype=bool)
        for other_index, other in enumerate(masks):
            if other_index != index:
                other_union |= other
        exclusive = mask & ~other_union
        if not exclusive.any():
            # This proposal is fully covered by other masks. Keep a stable
            # interior seed so it can still receive its closest shared area.
            interior = cv2.distanceTransform(
                mask.astype(np.uint8), cv2.DIST_L2, 5)
            if interior.max() > 0:
                y, x = np.unravel_index(int(interior.argmax()), shape)
                exclusive[y, x] = True
        seeds.append(exclusive)

    # Higher SAM score wins exact distance ties; original area is the stable
    # secondary key. Visit the strongest item first and only replace on a
    # strictly shorter distance.
    priority = sorted(
        range(len(items)),
        key=lambda i: (float(items[i].get("sam_score") or 0.0),
                       int(masks[i].sum())),
        reverse=True,
    )
    best_distance = np.full(shape, np.inf, dtype=np.float32)
    owner = np.full(shape, -1, dtype=np.int8)
    for index in priority:
        if not seeds[index].any():
            continue
        distance = cv2.distanceTransform(
            (~seeds[index]).astype(np.uint8), cv2.DIST_L2, 5)
        eligible = masks[index] & contested
        take = eligible & (distance < best_distance)
        owner[take] = index
        best_distance[take] = distance[take]

    assigned = []
    for index, item in enumerate(items):
        # Preserve uncontested pixels and take only the shared pixels owned by
        # this mask. This also drops an exact duplicate that lost every tie.
        result_mask = (masks[index] & ~contested) | (owner == index)
        if not result_mask.any():
            continue
        ys, xs = np.nonzero(result_mask)
        assigned.append(dict(
            item,
            mask=result_mask,
            area_frac=float(result_mask.mean()),
            bbox=[int(xs.min()), int(ys.min()),
                  int(xs.max()) + 1, int(ys.max()) + 1],
        ))

    # Guard the partition invariant here: a programming or OpenCV error must
    # not silently create or discard food pixels before nutrition scoring.
    if assigned:
        assigned_union = np.zeros(shape, dtype=bool)
        assigned_count = np.zeros(shape, dtype=np.uint8)
        for item in assigned:
            item_mask = item["mask"]
            assigned_union |= item_mask
            assigned_count += item_mask
        if np.any(assigned_count > 1) or not np.array_equal(assigned_union, union):
            raise RuntimeError("overlap partition failed to preserve food regions")
    return assigned


def _item_wire_block(item, classification, dish_info, portion, reason=None):
    """One serving of a multi-item plate -> its wire items[] block (spec
    003). reason is a Reason whose wire form carries the skip explanation
    for unrecognized/unmeasurable items (paths redacted by Reason)."""
    block = {
        "dish": dish_info,
        "classification": classification,
        "portion": _portion_wire_block(portion) if portion is not None else None,
        "bbox": item.get("bbox"),
        "area_frac": (None if item.get("area_frac") is None
                      else round(float(item["area_frac"]), 4)),
        "sam_score": (None if item.get("sam_score") is None
                      else round(float(item["sam_score"]), 4)),
    }
    if reason is not None:
        block["reason"] = reason.to_wire()
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
