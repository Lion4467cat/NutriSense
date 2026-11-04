"""Lazy production adapter for the frozen WED semantic segmenter.

WED supervision is semantic. Connected components are useful region proposals,
but are not serving IDs. For the existing WED weight head we therefore union
disconnected components of each predicted class into one class-level ROI, which
matches the granularity of its per-class mass labels.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch

from config import load_wed_index
from models.wed_semantic_segmenter import load_checkpoint, prepare_image

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKPOINT = ROOT / "experiments/wed_native_segmentation/model_wed_semantic_baseline.pt"
MODEL_ID = "deeplabv3_resnet50_imagenet_wed42"

# Small garnish/condiment classes in WED index_map (1-based label IDs) that
# legitimately appear as compact regions on a thali rim.
_SMALL_CONDIMENT_CLASSES = frozenset({2, 3, 7, 13, 19, 32, 33, 35, 39})

# Canonical WED capture resolution (1280x960 = 1,228,800 px = 4.6875x the
# 512x512 DeepLabV3 canvas). Across all 1,146 WED TRAIN views (9,568 main-dish
# and 3,421 condiment ground-truth regions), the 0th-percentile minimum
# ground-truth primary component area is 346 px (main) and 327 px (condiment).
_CANONICAL_WED_PIXELS = float(1280 * 960)


def _clean_semantic_labels(labels: np.ndarray) -> np.ndarray:
    """Suppress isolated false-positive speckles and boundary bleeds while
    preserving genuine small condiments and multi-compartment bowls."""
    if labels.size < 4096 or not np.any(labels > 0):
        return labels
    out = labels.copy()
    height, width = out.shape
    area_scale = max(0.25, float(labels.size) / _CANONICAL_WED_PIXELS)
    min_iso_cond = max(4, int(round(16.0 * area_scale)))
    min_iso_main = max(16, int(round(90.0 * area_scale)))
    bleed_cond = max(16, int(round(80.0 * area_scale)))
    bleed_main = max(64, int(round(340.0 * area_scale)))
    sec_cap = max(128, int(round(600.0 * area_scale)))
    kernel = np.ones((3, 3), dtype=np.uint8)
    max_same: dict[int, int] = {}
    max_area_by_id: dict[int, int] = {}
    comp_records: list[tuple[int, int, int, np.ndarray, np.ndarray]] = []
    for class_id in sorted(int(v) for v in np.unique(out) if v > 0):
        mask = (out == class_id).astype(np.uint8)
        n_cc, cc, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        areas = [int(stats[i, cv2.CC_STAT_AREA]) for i in range(1, n_cc)]
        if not areas:
            continue
        max_same[class_id] = max(areas)
        max_area_by_id[class_id] = max(areas)
        for comp_id in range(1, n_cc):
            area = int(stats[comp_id, cv2.CC_STAT_AREA])
            if area > 0:
                comp_records.append((area, class_id, comp_id, cc, stats[comp_id]))

    comp_records.sort(key=lambda item: (item[0], item[1], item[2]))
    for area, class_id, comp_id, cc, st in comp_records:
        x0 = int(st[cv2.CC_STAT_LEFT])
        y0 = int(st[cv2.CC_STAT_TOP])
        w = int(st[cv2.CC_STAT_WIDTH])
        h = int(st[cv2.CC_STAT_HEIGHT])
        r0, r1 = max(0, y0 - 2), min(height, y0 + h + 2)
        c0, c1 = max(0, x0 - 2), min(width, x0 + w + 2)
        sub_cc = cc[r0:r1, c0:c1] == comp_id
        sub_out = out[r0:r1, c0:c1]
        dil = cv2.dilate(sub_cc.astype(np.uint8), kernel) > 0
        ring_vals = sub_out[dil & ~sub_cc]
        if ring_vals.size == 0:
            continue
        food_vals = ring_vals[ring_vals > 0]
        frac_food = float(food_vals.size) / float(ring_vals.size)
        maj_food = 0
        if food_vals.size > 0:
            vals, counts = np.unique(food_vals, return_counts=True)
            maj_food = int(vals[int(np.argmax(counts))])

        if max_same.get(class_id, 0) >= 10 * area and area < sec_cap:
            sub_out[sub_cc] = maj_food if food_vals.size > 0 else 0
            continue

        min_iso = min_iso_cond if class_id in _SMALL_CONDIMENT_CLASSES else min_iso_main
        if area < min_iso:
            sub_out[sub_cc] = maj_food if (food_vals.size > 0 and frac_food >= 0.35) else 0
            continue

        if food_vals.size > 0:
            bleed_thresh = bleed_cond if class_id in _SMALL_CONDIMENT_CLASSES else bleed_main
            if (area < bleed_thresh
                    and frac_food >= 0.45
                    and max_area_by_id.get(maj_food, 0) >= 4 * area):
                sub_out[sub_cc] = maj_food

    return out if np.any(out > 0) else labels


# Minimum mean foreground softmax probability required to accept the WED
# 41-class thali segmenter before falling back to SAM2 + SigLIP2.
# Held-out WED DEV views: min=0.948, p01=0.952, median=0.973.
# Non-thali canteen / ArUco captures: max=0.872, median=0.774.
_WED_DOMAIN_MIN_FG_PROB = 0.90

# ISO 216 A6 reference card half-dimensions (52.5mm x 74.0mm) plus one 5.5mm
# ArUco module margin, and card-length to 60mm-marker ratio (148 / 60 = 2.47).
_A6_CARD_HALF_W_MM = 58.0
_A6_CARD_HALF_H_MM = 80.0
_A6_TO_MARKER_RATIO = 2.5


def _aruco_card_mask(image_bgr: np.ndarray) -> np.ndarray | None:
    """Return a boolean mask covering a detected ArUco reference card, or None."""
    try:
        from models.scale_anchor import estimate_anchor
        anchor = estimate_anchor(image_bgr)
    except Exception:
        return None
    if not isinstance(anchor, dict) or anchor.get("label") != "measured":
        return None
    h, w = image_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    H = anchor.get("H")
    if H is not None:
        try:
            H_arr = np.asarray(H, dtype=np.float64)
            card_mm = np.array(
                [[[-_A6_CARD_HALF_W_MM, -_A6_CARD_HALF_H_MM]],
                 [[_A6_CARD_HALF_W_MM, -_A6_CARD_HALF_H_MM]],
                 [[_A6_CARD_HALF_W_MM, _A6_CARD_HALF_H_MM]],
                 [[-_A6_CARD_HALF_W_MM, _A6_CARD_HALF_H_MM]]],
                dtype=np.float64,
            )
            pts = cv2.perspectiveTransform(card_mm, H_arr).reshape(4, 2)
            if np.all(np.isfinite(pts)):
                cv2.fillConvexPoly(mask, np.round(pts).astype(np.int32), 1)
        except Exception:
            pass
    corners = (anchor.get("extras") or {}).get("marker_corners_px")
    if corners is not None:
        c = np.asarray(corners, dtype=np.float64).reshape(4, 2)
        center = c.mean(axis=0, keepdims=True)
        expanded = center + _A6_TO_MARKER_RATIO * (c - center)
        cv2.fillConvexPoly(mask, np.round(expanded).astype(np.int32), 1)
    return mask > 0 if np.any(mask > 0) else None


def _predict_labels_and_probs(
    model: torch.nn.Module,
    image_bgr: np.ndarray,
    device: str | torch.device,
) -> tuple[np.ndarray, np.ndarray]:
    """Run one DeepLabV3 forward pass returning (uint8 labels, float32 max_probs)."""
    model.eval()
    h, w = image_bgr.shape[:2]
    image = prepare_image(image_bgr).unsqueeze(0).to(device)
    with torch.inference_mode():
        logits = model(image)["out"]
        if float(h * w) <= _CANONICAL_WED_PIXELS:
            logits = torch.nn.functional.interpolate(
                logits, size=(h, w), mode="bilinear", align_corners=False)
            probs = torch.softmax(logits, dim=1)[0]
            max_probs, labels = probs.max(dim=0)
            return labels.byte().cpu().numpy(), max_probs.float().cpu().numpy()
        scale = float(np.sqrt(_CANONICAL_WED_PIXELS / float(h * w)))
        eval_h = max(1, int(round(h * scale)))
        eval_w = max(1, int(round(w * scale)))
        logits = torch.nn.functional.interpolate(
            logits, size=(eval_h, eval_w), mode="bilinear", align_corners=False)
        probs = torch.softmax(logits, dim=1)[0]
        max_probs, labels = probs.max(dim=0)
        labels_np = labels.byte().cpu().numpy()
        probs_np = max_probs.float().cpu().numpy()
    labels_full = cv2.resize(labels_np, (w, h), interpolation=cv2.INTER_NEAREST)
    probs_full = cv2.resize(probs_np, (w, h), interpolation=cv2.INTER_LINEAR)
    return labels_full.astype(np.uint8), probs_full.astype(np.float32)


class WEDInference:
    """Image-only inference adapter used by the API and DEV evaluator."""

    def __init__(self, checkpoint: str | Path = DEFAULT_CHECKPOINT,
                 device: str | torch.device | None = None):
        self.checkpoint_path = Path(checkpoint)
        self.device = torch.device(device or
                                   ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model, self.checkpoint_metadata = load_checkpoint(
            self.checkpoint_path, device=self.device)

    def predict(self, image_bgr: np.ndarray) -> np.ndarray:
        raw_labels, max_probs = _predict_labels_and_probs(
            self.model, image_bgr, self.device)
        fg = raw_labels > 0
        if not np.any(fg):
            return raw_labels
        # Mask out any physical ArUco reference card before evaluating food regions
        # if confidence is borderline or white-card decoy classes (curd=13, papad=29)
        # are present.
        mean_prob = float(max_probs[fg].mean())
        if mean_prob < 0.94 or np.any((raw_labels == 13) | (raw_labels == 29)):
            card_mask = _aruco_card_mask(image_bgr)
            if card_mask is not None:
                raw_labels = raw_labels.copy()
                raw_labels[card_mask] = 0
                fg = raw_labels > 0
                if not np.any(fg):
                    return raw_labels
                mean_prob = float(max_probs[fg].mean())
        if mean_prob < _WED_DOMAIN_MIN_FG_PROB:
            return np.zeros_like(raw_labels)
        return _clean_semantic_labels(raw_labels)

    def segment(self, image_bgr: np.ndarray) -> dict[str, Any]:
        labels = self.predict(image_bgr)
        food = labels > 0
        if not food.any():
            raise RuntimeError("WED semantic segmenter predicted no food pixels")
        components: list[dict[str, Any]] = []
        class_items: list[dict[str, Any]] = []
        class_names = {int(value) + 1: str(name)
                       for name, value in load_wed_index().items()}
        for class_id in sorted(int(value) for value in np.unique(labels) if value > 0):
            class_mask = labels == class_id
            count, cc_labels, stats, _ = cv2.connectedComponentsWithStats(
                class_mask.astype(np.uint8), connectivity=8)
            class_components = []
            for component_id in range(1, count):
                area = int(stats[component_id, cv2.CC_STAT_AREA])
                if area == 0:
                    continue
                component_mask = cc_labels == component_id
                x = int(stats[component_id, cv2.CC_STAT_LEFT])
                y = int(stats[component_id, cv2.CC_STAT_TOP])
                w = int(stats[component_id, cv2.CC_STAT_WIDTH])
                h = int(stats[component_id, cv2.CC_STAT_HEIGHT])
                component = {
                    "class_id": class_id,
                    "mask": component_mask,
                    "area": area,
                    "bbox": [x, y, x + w - 1, y + h - 1],
                }
                components.append(component)
                class_components.append(component)
            # WED mass labels correspond to a class total, not each connected
            # island. Keep disjoint components in the same class ROI, while
            # anchoring the ROI bounding box on dominant component(s) so tiny
            # stray fragments cannot stretch roi_align across the plate.
            ys, xs = np.nonzero(class_mask)
            if not xs.size:
                continue
            max_comp_area = max((c["area"] for c in class_components), default=0)
            dom_comps = [
                c for c in class_components
                if c["area"] >= max(25, int(0.05 * max_comp_area))
            ] or class_components
            bx0 = min(int(c["bbox"][0]) for c in dom_comps)
            by0 = min(int(c["bbox"][1]) for c in dom_comps)
            bx1 = max(int(c["bbox"][2]) for c in dom_comps)
            by1 = max(int(c["bbox"][3]) for c in dom_comps)
            if len(dom_comps) == len(class_components):
                bbox_mask = class_mask
            else:
                bbox_mask = np.zeros_like(class_mask, dtype=bool)
                for c in dom_comps:
                    bbox_mask |= c["mask"]
            class_items.append({
                "class_id": class_id,
                "mask": class_mask,
                "bbox_mask": bbox_mask,
                "area": int(class_mask.sum()),
                "area_frac": float(class_mask.mean()),
                "bbox": [bx0, by0, bx1, by1],
                "component_count": len(class_components),
                "semantic_class_id": class_id,
                "semantic_class_name": class_names.get(class_id, str(class_id)),
            })
        if not components:
            raise RuntimeError("WED semantic mask contains no connected food regions")
        return {
            "mask": food,
            "labels": labels,
            "strategy": "wed_deeplabv3_semantic",
            "sam_score": None,
            "area_frac": float(food.mean()),
            "n_candidates": len(components),
            "regions": components,
            "items": class_items,
            "candidate_count": len(components),
            "class_item_count": len(class_items),
            "truncated_count": 0,
            "component_semantics": "8-connected class regions; not serving IDs",
            "model_id": MODEL_ID,
            "checkpoint": str(self.checkpoint_path),
        }

    def segment_items(self, image_bgr: np.ndarray) -> dict[str, Any]:
        result = self.segment(image_bgr)
        return {
            "items": result["items"],
            "regions": result["regions"],
            "strategy": "wed_semantic_class_union_components",
            "candidate_count": result["candidate_count"],
            "class_item_count": result["class_item_count"],
            "truncated_count": 0,
        }


@lru_cache(maxsize=1)
def get_runtime() -> WEDInference:
    """Load the frozen checkpoint on first real request, never at import."""
    checkpoint = DEFAULT_CHECKPOINT
    if not checkpoint.is_file():
        raise FileNotFoundError(f"frozen WED segmenter checkpoint missing: {checkpoint}")
    return WEDInference(checkpoint)


def segment_food(image_bgr: np.ndarray) -> dict[str, Any]:
    return get_runtime().segment(image_bgr)


def segment_items(image_bgr: np.ndarray) -> dict[str, Any]:
    return get_runtime().segment_items(image_bgr)


def pipeline_deps(image_bgr: np.ndarray) -> dict[str, Any]:
    """Bind the two pipeline seams to one prediction for this request image."""
    cached: dict[str, Any] = {}

    def result_for(frame: np.ndarray) -> dict[str, Any]:
        if frame is not image_bgr:
            raise ValueError("WED adapter received a different frame in one request")
        if "result" not in cached:
            try:
                cached["result"] = get_runtime().segment(frame)
            except RuntimeError:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                from models.dish_segmenter import (
                    segment_food as fallback_segment_food,
                    segment_items as fallback_segment_items,
                )
                seg_fallback = fallback_segment_food(frame)
                items_fallback = fallback_segment_items(frame)
                cached["result"] = {
                    **seg_fallback,
                    "items": items_fallback.get("items", []),
                    "regions": items_fallback.get("regions", []),
                    "candidate_count": items_fallback.get("candidate_count", 0),
                    "class_item_count": len(items_fallback.get("items", [])),
                    "truncated_count": items_fallback.get("truncated_count", 0),
                    "_fallback_strategy": items_fallback.get("strategy", "dish_segmenter"),
                }
        return cached["result"]

    def segment(frame: np.ndarray) -> dict[str, Any]:
        result = result_for(frame)
        return {key: value for key, value in result.items()
                if key not in {"items", "_fallback_strategy"}}

    def segment_items_for_frame(frame: np.ndarray) -> dict[str, Any]:
        result = result_for(frame)
        strategy = result.get("_fallback_strategy",
                              "wed_semantic_class_union_components")
        return {
            "items": result["items"],
            "regions": result.get("regions", []),
            "strategy": strategy,
            "candidate_count": result.get("candidate_count", len(result["items"])),
            "class_item_count": result.get("class_item_count", len(result["items"])),
            "truncated_count": result.get("truncated_count", 0),
        }

    def inspect_prediction() -> dict[str, Any]:
        """Evaluation-only access to the already-computed prediction."""
        return result_for(image_bgr)

    return {"segment": segment, "segment_items": segment_items_for_frame,
            "inspect_prediction": inspect_prediction}
