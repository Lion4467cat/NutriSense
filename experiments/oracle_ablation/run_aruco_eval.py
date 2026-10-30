"""Run the confirmed six-plate ArUco ground-truth diagnostic.

Ground-truth weights are used only after analyze() returns. The eval requires
CUDA and fails closed; model stages unload between calls to keep loading
sequential on the target GPU.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_DATA = ROOT.parent / "Aruco_7ID_60mm_with_food"
DEFAULT_OUT = Path(__file__).resolve().parent / "aruco_raw.jsonl"
DAY = "mon"
BAND = "1-5"
SERVING_STYLE = "mixed"
N_MC = 4000
SEED = 1234
ARTIFACT_ROOT = Path(__file__).resolve().parent

# Confirmed by the user. This table is read only by scoring/reporting code;
# none of these values are passed to engine.pipeline.analyze().
GROUND_TRUTH: dict[str, dict[str, Any]] = {
    "Dish 1": {"total_g": 450, "components": [
        {"name": "rice", "grams": 250, "aliases": ["rice", "steamed rice"]},
        {"name": "keerai sambar", "grams": 200,
         "aliases": ["keerai sambar"]},
    ]},
    "Dish 2": {"total_g": 338, "components": [
        {"name": "rice", "grams": 211, "aliases": ["rice", "steamed rice"]},
        {"name": "tomato rasam", "grams": 127,
         "aliases": ["tomato rasam"]},
    ]},
    "Dish 3": {"total_g": 191, "components": [
        {"name": "coconut chutney", "grams": 70,
         "aliases": ["coconut chutney"]},
        {"name": "chapati (2 total)", "grams": 121,
         "aliases": ["chapati", "chapathi"]},
    ]},
    "Dish 4": {"total_g": 250, "components": [
        {"name": "dum biryani", "grams": 206, "aliases": ["biryani"]},
        {"name": "egg (1)", "grams": 44, "aliases": ["egg", "boiled egg"]},
    ]},
    "Dish 5": {"total_g": 150, "components": [
        {"name": "dum biryani", "grams": 150, "aliases": ["biryani"]},
    ]},
    "Dish 6": {"total_g": 351, "components": [
        {"name": "dum biryani", "grams": 257, "aliases": ["biryani"]},
        {"name": "egg (2 total)", "grams": 94,
         "aliases": ["egg", "boiled egg"]},
    ]},
}


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").lower().replace("_", " ").replace("-", " ")).strip()


def _unload_models() -> None:
    from models import registry
    registry.unload()
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def _measure_stage(name: str, fn: Callable[..., Any],
                   peaks: dict[str, dict[str, float]]) -> Callable[..., Any]:
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA became unavailable; refusing CPU fallback")
        _unload_models()
        torch.cuda.reset_peak_memory_stats()
        try:
            value = fn(*args, **kwargs)
            torch.cuda.synchronize()
            return value
        finally:
            torch.cuda.synchronize()
            peaks[name] = {
                "allocated_peak_mb": round(torch.cuda.max_memory_allocated() / 2**20, 2),
                "reserved_peak_mb": round(torch.cuda.max_memory_reserved() / 2**20, 2),
            }
            _unload_models()
    return wrapped


class _DepthStage:
    def __init__(self, peaks: dict[str, dict[str, float]],
                 capture: dict[str, Any] | None = None) -> None:
        self.peaks = peaks
        self.capture = capture

    def __call__(self, image_bgr: np.ndarray, fov_x: float | None = None) -> dict[str, Any]:
        from engine.depth import MonocularDepth
        out = _measure_stage("depth", MonocularDepth(), self.peaks)(image_bgr, fov_x=fov_x)
        if self.capture is not None:
            depth = out.get("depth_m")
            if depth is not None:
                self.capture["depth_m"] = np.asarray(depth, dtype=np.float32).copy()
        return out


def _draw_overlay(image: np.ndarray, top: np.ndarray | None,
                  items: list[np.ndarray], item_rows: list[dict[str, Any]],
                  marker_quad: Any, title: str) -> np.ndarray:
    h, w = image.shape[:2]
    scale = min(1.0, 1600.0 / max(h, w))
    canvas = cv2.resize(image, (round(w * scale), round(h * scale)),
                        interpolation=cv2.INTER_AREA) if scale < 1 else image.copy()
    color_list = [(0, 220, 255), (255, 80, 30), (60, 255, 80),
                  (255, 50, 220), (0, 150, 255)]
    def outline(mask: np.ndarray, color: tuple[int, int, int], thickness: int) -> None:
        small = cv2.resize(mask.astype(np.uint8), (canvas.shape[1], canvas.shape[0]),
                           interpolation=cv2.INTER_NEAREST)
        contours, _ = cv2.findContours(small, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(canvas, contours, -1, color, thickness)
    if top is not None:
        outline(top, (255, 255, 0), 2)
    for i, mask in enumerate(items):
        outline(mask, color_list[i % len(color_list)], 2)
    if marker_quad is not None:
        quad = np.asarray(marker_quad, dtype=np.float32).reshape(-1, 2) * scale
        cv2.polylines(canvas, [np.round(quad).astype(np.int32)], True,
                      (0, 255, 255), 3)
    footer = [(title, (245, 245, 245))]
    for i, row in enumerate(item_rows):
        cls = row.get("classification") or {}
        portion = row.get("portion") or {}
        footer.append((f"item {i}: {cls.get('dish')} {portion.get('grams')} g",
                       color_list[i % len(color_list)]))
    line_h = 25
    footer_img = np.zeros((line_h * len(footer) + 8, canvas.shape[1], 3),
                          dtype=np.uint8)
    for i, (text, color) in enumerate(footer):
        x = 8
        if i:
            cv2.rectangle(footer_img, (8, line_h * i + 3),
                          (22, line_h * i + 17), color, -1)
            x = 30
        cv2.putText(footer_img, text[:180], (x, line_h * (i + 1) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (245, 245, 245), 1,
                    cv2.LINE_AA)
    return np.vstack([canvas, footer_img])


def _save_height_overlay(image: np.ndarray, top: np.ndarray | None,
                         items: list[np.ndarray], height_maps: list[Any],
                         item_rows: list[dict[str, Any]], marker_quad: Any,
                         out_path: Path, title: str) -> None:
    h, w = image.shape[:2]
    scale = min(1.0, 1600.0 / max(h, w))
    canvas = cv2.resize(image, (round(w * scale), round(h * scale)),
                        interpolation=cv2.INTER_AREA) if scale < 1 else image.copy()
    merged = np.full((h, w), np.nan, dtype=np.float32)
    for height in height_maps:
        if height is None:
            continue
        valid = np.isfinite(height)
        merged[valid] = np.fmax(np.nan_to_num(merged[valid], nan=0.0), height[valid])
    valid = np.isfinite(merged)
    heat = np.zeros((h, w), dtype=np.uint8)
    if valid.any():
        heat[valid] = np.clip(merged[valid] * 255.0 / 40.0, 0, 255).astype(np.uint8)
    heat = cv2.applyColorMap(heat, cv2.COLORMAP_TURBO)
    heat_small = cv2.resize(heat, (canvas.shape[1], canvas.shape[0]),
                            interpolation=cv2.INTER_AREA)
    valid_small = cv2.resize(valid.astype(np.uint8),
                             (canvas.shape[1], canvas.shape[0]),
                             interpolation=cv2.INTER_NEAREST).astype(bool)
    canvas[valid_small] = cv2.addWeighted(canvas, 0.48, heat_small, 0.52, 0)[valid_small]
    colors = [(0, 220, 255), (255, 80, 30), (60, 255, 80),
              (255, 50, 220), (0, 150, 255)]
    def outline(mask: np.ndarray, color: tuple[int, int, int]) -> None:
        small = cv2.resize(mask.astype(np.uint8), (canvas.shape[1], canvas.shape[0]),
                           interpolation=cv2.INTER_NEAREST)
        contours, _ = cv2.findContours(small, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(canvas, contours, -1, color, 2)
    if top is not None:
        outline(top, (255, 255, 0))
    for i, mask in enumerate(items):
        outline(mask, colors[i % len(colors)])
    if marker_quad is not None:
        quad = np.asarray(marker_quad, dtype=np.float32).reshape(-1, 2) * scale
        cv2.polylines(canvas, [np.round(quad).astype(np.int32)], True,
                      (0, 255, 255), 3)
    footer = [title, "height above fitted base plane (mm); TURBO scale 0 to 40 mm"]
    for i, row in enumerate(item_rows):
        portion = row.get("portion") or {}
        footer.append(f"item {i}: {row.get('dish', {}).get('id')} "
                      f"{portion.get('grams')} g; mean h={portion.get('mean_h_mm')} mm")
    footer_img = np.zeros((25 * len(footer) + 8, canvas.shape[1], 3), dtype=np.uint8)
    for i, text in enumerate(footer):
        cv2.putText(footer_img, text[:180], (8, 25 * (i + 1) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (245, 245, 245), 1,
                    cv2.LINE_AA)
    cv2.imwrite(str(out_path), np.vstack([canvas, footer_img]))


def _write_contact_sheets(rows: list[dict[str, Any]]) -> None:
    for plate in sorted({row["plate"] for row in rows}):
        paths = [Path(row["mask_artifacts"]["overlay"]) for row in rows
                 if row.get("plate") == plate and row.get("mask_artifacts")]
        thumbs = []
        for path in paths:
            image = cv2.imread(str(path))
            if image is not None:
                thumbs.append(cv2.resize(image, (480, 540),
                                         interpolation=cv2.INTER_AREA))
        if not thumbs:
            continue
        cols = min(3, len(thumbs))
        rows_n = (len(thumbs) + cols - 1) // cols
        sheet = np.zeros((rows_n * 540, cols * 480, 3), dtype=np.uint8)
        for i, thumb in enumerate(thumbs):
            y, x = divmod(i, cols)
            sheet[y * 540:(y + 1) * 540, x * 480:(x + 1) * 480] = thumb
        out = ARTIFACT_ROOT / "overlays" / f"{plate.replace(' ', '_')}_contact_sheet.png"
        cv2.imwrite(str(out), sheet)


def _geometry_height_map(mask: np.ndarray, depth: np.ndarray, K: np.ndarray,
                         base: tuple[float, float, float]) -> tuple[np.ndarray, float, float]:
    from models.portion_estimator import _fill_depth, _unproject
    ys, xs = np.nonzero(mask)
    z = _fill_depth(depth[ys, xs])
    pts = _unproject(xs, ys, z, K)
    a, b, c = base
    norm = float(np.sqrt(a * a + b * b + 1.0))
    h = (a * pts[:, 0] + b * pts[:, 1] + c - pts[:, 2]) / norm * 1000.0
    if float(np.median(h)) < 0:
        h = -h
    h = np.clip(h, 0.0, None)
    out = np.full(mask.shape, np.nan, dtype=np.float32)
    out[ys, xs] = h.astype(np.float32)
    return out, float(h.mean()), float(h.max())


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    union = int(np.logical_or(a, b).sum())
    return float(np.logical_and(a, b).sum() / union) if union else 0.0


def _mask_diagnostics(result: dict[str, Any], capture: dict[str, Any]) -> dict[str, Any]:
    top = capture.get("top_mask")
    item_masks = capture.get("item_masks") or []
    items = result.get("items") or []
    if len(items) == 1 and not item_masks and top is not None:
        item_masks = [top]
    if len(item_masks) != len(items):
        return {
            "top_food_area_px": int(top.sum()) if top is not None else None,
            "item_mask_areas": [], "sum_item_mask_area_px": None,
            "item_area_sum_to_top_ratio": None, "pairwise_iou": [],
            "flagged_item_indices": [], "duplicate_drop_indices": [],
            "flagged_grams": None, "duplicate_dropped_total_g": None,
            "mask_mapping_note": f"captured {len(item_masks)} item masks for {len(items)} output items",
        }

    top_area = int(top.sum()) if top is not None else None
    item_areas = [int(m.sum()) for m in item_masks]
    pairs = []
    overlap_indices: set[int] = set()
    duplicate_drop: set[int] = set()
    grams = [((it.get("portion") or {}).get("grams")) for it in items]
    for i in range(len(item_masks)):
        for j in range(i + 1, len(item_masks)):
            value = _iou(item_masks[i], item_masks[j])
            pairs.append({"i": i, "j": j, "iou": value})
            if value > 0.5:
                overlap_indices.update((i, j))
                gi, gj = grams[i], grams[j]
                if gi is None or gj is None:
                    drop = j
                elif float(gi) > float(gj):
                    drop = j
                elif float(gj) > float(gi):
                    drop = i
                else:
                    drop = j
                duplicate_drop.add(drop)

    exceeds = {i for i, area in enumerate(item_areas)
               if top_area is not None and area > top_area}
    outside = []
    if top is not None:
        outside = [int(np.logical_and(m, np.logical_not(top)).sum()) for m in item_masks]
    flagged = overlap_indices | exceeds
    flagged_known_grams = sum(float(grams[i]) for i in flagged if grams[i] is not None)
    flagged_unknown_count = sum(grams[i] is None for i in flagged)
    flagged_grams = flagged_known_grams if flagged_unknown_count == 0 else None
    drop_total = (sum(float(g) for i, g in enumerate(grams)
                      if i not in duplicate_drop and g is not None)
                  if all(g is not None for g in grams) else None)
    total = (result.get("portion") or {}).get("grams")
    return {
        "top_food_area_px": top_area,
        "item_mask_areas": [
            {"item_index": i, "area_px": area,
             "area_frac": float(item_masks[i].mean()),
             "exceeds_top_food_area": i in exceeds,
             "pixels_outside_top_food_mask": outside[i] if outside else None}
            for i, area in enumerate(item_areas)
        ],
        "sum_item_mask_area_px": sum(item_areas),
        "item_area_sum_to_top_ratio": (
            sum(item_areas) / top_area if top_area else None),
        "pairwise_iou": pairs,
        "flagged_item_indices": sorted(flagged),
        "duplicate_drop_indices": sorted(duplicate_drop),
        "flagged_grams": flagged_grams,
        "flagged_known_grams": flagged_known_grams,
        "flagged_unknown_item_count": flagged_unknown_count,
        "flagged_grams_pct_of_prediction": (
            100.0 * flagged_grams / float(total)
            if flagged_grams is not None and total not in (None, 0) else None),
        "flagged_known_grams_pct_of_prediction": (
            100.0 * flagged_known_grams / float(total)
            if total not in (None, 0) else None),
        "duplicate_dropped_total_g": drop_total,
        "duplicate_drop_delta_g": (
            float(drop_total) - float(total)
            if drop_total is not None and total is not None else None),
        "mask_mapping_note": None,
    }


def _labels(result: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    top = (result.get("classification") or {}).get("dish")
    if top:
        labels.append(str(top))
    for item in result.get("items") or []:
        label = (item.get("classification") or {}).get("dish")
        if label:
            labels.append(str(label))
    return list(dict.fromkeys(labels))


def _classification_score(dish_name: str, result: dict[str, Any]) -> dict[str, Any]:
    labels = _labels(result)
    normalized = [_norm(label) for label in labels]
    if dish_name in {"Dish 4", "Dish 5", "Dish 6"}:
        correct = any("biryani" in label for label in normalized)
        return {"correct": correct, "predicted_labels": labels,
                "rubric": "any label containing biryani is correct"}
    components = GROUND_TRUTH[dish_name]["components"]
    covered = {}
    for comp in components:
        aliases = {_norm(alias) for alias in comp["aliases"]}
        covered[comp["name"]] = any(label in aliases for label in normalized)
    return {"correct": all(covered.values()), "component_label_coverage": covered,
            "predicted_labels": labels,
            "rubric": "all weighed component names must have an exact normalized label alias"}


def _component_scores(dish_name: str, result: dict[str, Any]) -> dict[str, Any]:
    components = GROUND_TRUTH[dish_name]["components"]
    items = result.get("items") or []
    matched: dict[str, list[dict[str, Any]]] = {c["name"]: [] for c in components}
    unmatched = []
    for item_index, item in enumerate(items):
        label = (item.get("classification") or {}).get("dish")
        grams = (item.get("portion") or {}).get("grams")
        norm_label = _norm(label)
        names = [c["name"] for c in components
                 if norm_label and norm_label in {_norm(a) for a in c["aliases"]}]
        if len(names) == 1 and grams is not None:
            matched[names[0]].append({"item_index": item_index,
                                     "dish_label": label, "grams": float(grams)})
        else:
            unmatched.append({"item_index": item_index, "dish_label": label,
                              "grams": grams,
                              "reason": "no exact component alias match" if label else "no dish label"})
    rows = []
    missing = []
    for comp in components:
        preds = matched[comp["name"]]
        if not preds:
            missing.append(comp["name"])
            rows.append({"component": comp["name"], "true_g": comp["grams"],
                         "predicted_g": None, "signed_error_g": None,
                         "percent_error": None, "matched_items": []})
            continue
        pred = sum(p["grams"] for p in preds)
        err = pred - float(comp["grams"])
        rows.append({"component": comp["name"], "true_g": comp["grams"],
                     "predicted_g": pred, "signed_error_g": err,
                     "percent_error": 100.0 * err / float(comp["grams"]),
                     "matched_items": preds})
    return {"components": rows, "unmatched_items": unmatched,
            "unmatched_ground_truth_components": missing}


def _call_analyze(path: Path, mode: str, force_prior: bool,
                  output_stream, save_masks: bool = False,
                  height_done: set[str] | None = None) -> dict[str, Any]:
    import engine.pipeline as pipeline
    from models import registry
    from models.dish_segmenter import segment_food, segment_items
    from models.food_classifier import classify_dish
    from models.scale_anchor import estimate_anchor, read_exif, prior_anchor
    from config import load_anchor_config, load_params
    from models.portion_estimator import _fit_base_ring, _fit_base_table

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable before image; stopping without CPU fallback")
    image = cv2.imread(str(path))
    if image is None:
        raise RuntimeError(f"unreadable image: {path}")
    exif = read_exif(path)
    captures: dict[str, Any] = {"top_mask": None, "item_masks": [],
                                "classifier_calls": [], "geometry": [],
                                "geometry_height_maps": []}
    stage_peaks: dict[str, dict[str, float]] = {}
    timings_seen: list[dict[str, float]] = []
    original_log = pipeline.log_analysis
    original_anchor = pipeline.estimate_anchor
    original_estimate_portion = pipeline.estimate_portion

    def capture_log(verdict: str, day: str, band: str,
                    timings: dict[str, float]) -> None:
        timings_seen.append(dict(timings))
        original_log(verdict, day, band, timings)

    def capture_segment(img: np.ndarray) -> dict[str, Any]:
        out = segment_food(img)
        captures["top_mask"] = np.asarray(out["mask"], dtype=bool).copy()
        return out

    def capture_items(img: np.ndarray) -> dict[str, Any]:
        out = segment_items(img)
        captures["item_masks"] = [np.asarray(row["mask"], dtype=bool).copy()
                                   for row in out.get("items") or []]
        return out

    def capture_classifier(img: np.ndarray) -> dict[str, Any]:
        out = classify_dish(img)
        scores = out.get("scores") or {}
        top2 = sorted(((str(k), float(v)) for k, v in scores.items()
                       if v is not None), key=lambda row: row[1], reverse=True)[:2]
        if save_masks:
            captures["classifier_calls"].append({
                "crop_shape_hw": [int(img.shape[0]), int(img.shape[1])],
                "dish": out.get("dish"), "confidence": out.get("confidence"),
                "top2": [{"label": k, "score": v} for k, v in top2],
                "method": out.get("method"), "match_score": out.get("match_score"),
            })
        return out

    def capture_estimate_portion(img, mask, depth_m, anchor, camera, dish,
                                 params=None, cfg=None):
        out = original_estimate_portion(img, mask, depth_m, anchor, camera, dish,
                                        params=params, cfg=cfg)
        if save_masks:
            chosen_params = params if params is not None else load_params()
            chosen_cfg = cfg or {}
            dm = np.asarray(depth_m, dtype=np.float64)
            mk = np.asarray(mask, dtype=bool)
            base = None
            base_method = "table_prior"
            if chosen_cfg.get("base_method", "auto") in ("auto", "ring"):
                base, _, method = _fit_base_ring(dm, mk, camera["K"],
                                                  chosen_params, chosen_cfg)
                if base is not None:
                    base_method = method
            if base is None and chosen_cfg.get("base_method", "auto") in ("auto", "table_prior"):
                base, _, _ = _fit_base_table(dm, mk, camera["K"],
                                              chosen_params, chosen_cfg)
                base_method = "table_prior"
            geom = {
                "geometry_call_index": len(captures["geometry"]),
                "mask_index": next((i for i, candidate in enumerate(captures["item_masks"])
                                    if np.array_equal(candidate, mk)), None),
                "mask_matches_top_level": bool(
                    captures["top_mask"] is not None
                    and np.array_equal(captures["top_mask"], mk)),
                "area_cm2": out.get("area_cm2"),
                "mean_height_mm": out.get("mean_h_mm"),
                "base_method": out.get("base_method"),
                "density_g_ml": out.get("density_eff"),
                "grams": out.get("grams"),
                "base_plane_coefficients_camera": (
                    [float(x) for x in base] if base is not None else None),
                "base_fit_method_replayed": base_method if base is not None else None,
                "mask_area_px": int(mk.sum()),
            }
            if base is not None:
                hmap, mean_h, max_h = _geometry_height_map(
                    mk, dm, camera["K"], tuple(float(x) for x in base))
                geom["recomputed_mean_height_mm"] = mean_h
                geom["max_height_mm"] = max_h
                captures["geometry_height_maps"].append(hmap)
            else:
                captures["geometry_height_maps"].append(None)
            captures["geometry"].append(geom)
        return out

    detector_observation = None
    if force_prior:
        detector_observation = estimate_anchor(image, exif=exif)

        def forced_anchor(img, config=None, exif=None):
            cfg = config if config is not None else load_anchor_config()
            reason = "forced prior by opt-in --force-prior flag"
            return prior_anchor(reason, cfg)

        pipeline.estimate_anchor = forced_anchor
    elif save_masks:
        def capture_anchor(img, config=None, exif=None):
            found = original_anchor(img, config=config, exif=exif)
            captures["anchor_full"] = found
            return found
        pipeline.estimate_anchor = capture_anchor

    pipeline.log_analysis = capture_log
    if save_masks:
        pipeline.estimate_portion = capture_estimate_portion
    deps = {
        "segment": _measure_stage("segment", capture_segment, stage_peaks),
        "classify": _measure_stage("classify", capture_classifier, stage_peaks),
        "depth": _DepthStage(stage_peaks, captures if save_masks else None),
        "segment_items": _measure_stage("segment_items", capture_items, stage_peaks),
    }
    started = time.perf_counter()
    try:
        result = pipeline.analyze(image, day=DAY, band=BAND, exif=exif,
                                  deps=deps, n_mc=N_MC, seed=SEED,
                                  serving_style=SERVING_STYLE)
    finally:
        pipeline.log_analysis = original_log
        pipeline.estimate_anchor = original_anchor
        pipeline.estimate_portion = original_estimate_portion
        del image
        registry.unload()
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA became unavailable during image; stopping")
        torch.cuda.synchronize()
    elapsed = round(time.perf_counter() - started, 4)
    anchor = result.get("anchor") or {}
    anchor_tier = anchor.get("tier")
    item_rows = result.get("items") or []
    if result.get("path_used") == "multi_item":
        output_item_masks = captures["item_masks"]
    elif result.get("portion") is not None and captures["top_mask"] is not None:
        output_item_masks = [captures["top_mask"]]
    else:
        output_item_masks = []
    diagnostic_capture = dict(captures, item_masks=output_item_masks)
    row = {
        "event": "image_result", "image": str(path),
        "plate": path.parent.name, "mode": mode,
        "forced_prior": force_prior,
        "detector_observation_forced_run": detector_observation,
        "anchor_tier": anchor_tier,
        "detector_rejection_evidence": (
            anchor.get("reason") if anchor_tier == "prior" and not force_prior else None),
        "result": result,
        "elapsed_s": elapsed,
        "pipeline_stage_timings_s": timings_seen[-1] if timings_seen else {},
        "stage_vram_peak": stage_peaks,
        "mask_diagnostics": _mask_diagnostics(result, diagnostic_capture),
        "classification_score": _classification_score(path.parent.name, result),
        "component_scores": _component_scores(path.parent.name, result),
    }
    if save_masks:
        overlay_source = cv2.imread(str(path))
        mask_dir = ARTIFACT_ROOT / "masks" / path.parent.name
        overlay_dir = ARTIFACT_ROOT / "overlays" / path.parent.name
        height_dir = ARTIFACT_ROOT / "height_maps" / path.parent.name
        for directory in (mask_dir, overlay_dir, height_dir):
            directory.mkdir(parents=True, exist_ok=True)
        stem = path.stem
        arrays: dict[str, Any] = {}
        if captures["top_mask"] is not None:
            arrays["top_mask"] = captures["top_mask"].astype(np.uint8)
        for i, m in enumerate(output_item_masks):
            arrays[f"item_mask_{i}"] = m.astype(np.uint8)
        if captures.get("depth_m") is not None:
            arrays["depth_m"] = captures["depth_m"].astype(np.float32)
        for i, hmap in enumerate(captures.get("geometry_height_maps", [])):
            if hmap is not None:
                arrays[f"item_height_mm_{i}"] = hmap
        mask_path = mask_dir / f"{stem}.npz"
        np.savez_compressed(mask_path, **arrays)
        raw_anchor = captures.get("anchor_full") or detector_observation or {}
        marker_quad = ((raw_anchor.get("extras") or {}).get("marker_corners_px"))
        classifier_calls = captures["classifier_calls"]
        overlay_path = overlay_dir / f"{stem}.png"
        overlay = _draw_overlay(overlay_source, captures["top_mask"],
                                output_item_masks, item_rows,
                                marker_quad, f"{path.parent.name} / {path.name}")
        cv2.imwrite(str(overlay_path), overlay)
        row["mask_artifacts"] = {
            "npz": str(mask_path), "overlay": str(overlay_path),
            "marker_quad_px": marker_quad,
            "classifier_calls": classifier_calls,
            "item_classifier_top2": [
                classifier_calls[index + 1]
                if index + 1 < len(classifier_calls) else None
                for index in range(len(item_rows))],
            "item_geometry_telemetry": captures["geometry"],
        }
        if (path.parent.name in {"Dish 1", "Dish 4", "Dish 6"}
                and anchor_tier == "measured"
                and (height_done is None or path.parent.name not in height_done)):
            hpath = height_dir / f"{stem}.png"
            _save_height_overlay(overlay_source, captures["top_mask"],
                                 output_item_masks,
                                 captures.get("geometry_height_maps", []),
                                 item_rows, marker_quad, hpath,
                                 f"{path.parent.name} / {path.name}")
            row["mask_artifacts"]["height_overlay"] = str(hpath)
            if height_done is not None:
                height_done.add(path.parent.name)
    output_stream.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    output_stream.flush()
    print(json.dumps({
        "event": "image_complete", "plate": row["plate"],
        "image": path.name, "mode": mode, "anchor_tier": anchor_tier,
        "dish_labels": row["classification_score"]["predicted_labels"],
        "grams": (result.get("portion") or {}).get("grams"),
        "verdict": result.get("verdict"), "elapsed_s": elapsed,
    }, sort_keys=True), flush=True)
    return row


def _images(data_root: Path) -> list[Path]:
    return sorted(p for p in data_root.glob("Dish */*")
                  if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"})


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--force-prior", action="store_true", default=False,
                    help="opt in to bypass card anchor detection and use the prior anchor")
    ap.add_argument("--paired-card-vs-prior", action="store_true", default=False,
                    help="run default full cohort, then force prior on every measured-anchor image")
    ap.add_argument("--save-masks", action="store_true", default=False,
                    help="opt in to save segmentation masks, overlays, classifier details and geometry telemetry")
    ap.add_argument("--image", type=Path,
                    help="run one image only (used for the flag-off reproducibility check)")
    args = ap.parse_args()
    if args.force_prior and args.paired_card_vs_prior:
        ap.error("use --force-prior for a direct forced run or --paired-card-vs-prior for paired scoring, not both")
    if not torch.cuda.is_available():
        print("FATAL: CUDA unavailable; refusing CPU fallback", file=sys.stderr, flush=True)
        return 2
    logging.basicConfig(level=logging.WARNING)
    image_paths = [args.image.resolve()] if args.image else _images(args.data)
    expected_counts = {"Dish 1": 6, "Dish 2": 4, "Dish 3": 3,
                       "Dish 4": 3, "Dish 5": 3, "Dish 6": 4}
    actual_counts = defaultdict(int)
    for path in image_paths:
        actual_counts[path.parent.name] += 1
    if args.image is None and (dict(actual_counts) != expected_counts or len(image_paths) != 23):
        raise RuntimeError(f"dataset image count mismatch: {dict(actual_counts)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    with args.out.open("w", encoding="utf-8") as stream:
        start = {
            "event": "run_started", "cuda_device": torch.cuda.get_device_name(0),
            "torch": torch.__version__, "cuda": torch.version.cuda,
            "image_count": len(image_paths), "day": DAY, "band": BAND,
            "serving_style": SERVING_STYLE, "n_mc": N_MC, "seed": SEED,
            "force_prior_default": False,
            "paired_card_vs_prior": args.paired_card_vs_prior,
            "save_masks": args.save_masks,
        }
        stream.write(json.dumps(start, sort_keys=True) + "\n")
        stream.flush()
        print(json.dumps(start, sort_keys=True), flush=True)

        baseline_force = args.force_prior
        height_done: set[str] = set()
        for path in image_paths:
            rows.append(_call_analyze(path,
                                      "forced_prior" if baseline_force else "default",
                                      baseline_force, stream,
                                      save_masks=args.save_masks,
                                      height_done=height_done))

        if args.paired_card_vs_prior:
            measured = [r for r in rows if r["anchor_tier"] == "measured"]
            by_path = {r["image"]: r for r in measured}
            for path in image_paths:
                base = by_path.get(str(path))
                if base:
                    rows.append(_call_analyze(path, "forced_prior_paired", True, stream,
                                              save_masks=args.save_masks,
                                              height_done=height_done))

            # Re-run one input with the force flag off; compare the pipeline
            # result JSON only (timings are recorded out-of-band).
            replay_path = Path(measured[0]["image"]) if measured else image_paths[0]
            replay = _call_analyze(replay_path, "default_replay_flag_off", False, stream,
                                   save_masks=args.save_masks,
                                   height_done=height_done)
            original = next(r for r in rows if r["image"] == str(replay_path)
                            and r["mode"] == "default")
            replay_check = {
                "event": "default_flag_off_replay_check",
                "image": str(replay_path),
                "original_result_sha256": _canonical_sha(original["result"]),
                "replay_result_sha256": _canonical_sha(replay["result"]),
                "identical_pipeline_result": original["result"] == replay["result"],
            }
            stream.write(json.dumps(replay_check, sort_keys=True) + "\n")
            stream.flush()
            print(json.dumps(replay_check, sort_keys=True), flush=True)

        if args.save_masks and args.image is None:
            _write_contact_sheets(rows)

        print(json.dumps({
            "event": "run_complete", "records": len(rows),
            "measured_anchor_images": sum(r["anchor_tier"] == "measured" for r in rows
                                           if r["mode"] == "default"),
            "prior_anchor_images": sum(r["anchor_tier"] == "prior" for r in rows
                                        if r["mode"] == "default"),
            "raw_jsonl": str(args.out),
        }, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
