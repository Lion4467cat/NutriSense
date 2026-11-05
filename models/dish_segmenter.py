"""SAM2.1 food segmentation (S2).

Strategy (validated against the synthetic renderer, tests/test_s2.py):
  1. Prompt SAM2.1 at the image centre (protocol: vessel is centred).
  2. Keep the 3 multimask candidates that are *solid* blobs
     (fill ratio >= SOLIDITY_MIN) and in a sane area range.
  3. Pick the candidate that is a strict subset of another solid candidate
     (food sits inside plate/table context), preferring one that also
     contains a smaller solid candidate (middle of a nested chain),
     tie-broken by SAM's predicted IoU score.
     The synthetic-scene test asserts an IoU floor of 0.75. Historical
     summaries record 0.97 and 0.98 for this component, so the observed
     point estimate is not treated as reconciled evidence. SAM's raw score
     alone can pick a rim arc; do not use it without the selection logic.
  4. Fallbacks: no parent found -> best-scoring solid mask; no solid mask
     at all -> best-scoring candidate; centre query produced nothing, or a
     mask below AREA_MIN (a speck, not a serving — ledger 014) -> one
     box-prompted query (centre 20-80% square).

Model: facebook/sam2.1-hiera-large (Apache-2.0, docs/licenses.md).
Weights download on first use (HF_HUB_DISABLE_XET=1 is recommended —
the xet backend stalls in this environment).
"""
import logging
from typing import Any, cast

import cv2
import numpy as np
from models.model_revisions import SAM2_REVISION

MODEL_ID = "facebook/sam2.1-hiera-large"
SOLIDITY_MIN = 0.85
AREA_MIN, AREA_MAX = 0.005, 0.7
PARENT_FRAC = 0.90          # area(i ∩ j) / area(i) >= this => i ⊂ j
log = logging.getLogger(__name__)


def _device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _make_state():
    import torch
    from transformers import Sam2Model, Sam2Processor
    dev = _device()
    proc = Sam2Processor.from_pretrained(MODEL_ID, revision=SAM2_REVISION)
    # Load directly in FP16 to halve VRAM allocation and prevent OOM
    dtype = torch.float16 if dev == "cuda" else torch.float32
    model = cast(Any, Sam2Model.from_pretrained(
        MODEL_ID, revision=SAM2_REVISION, torch_dtype=dtype)).to(dev).eval()
    return {"proc": proc, "model": model, "device": dev}


def _state():
    from models import registry
    return registry.get_or_create("sam2", _make_state)


def _load():
    s = _state()
    return s["proc"], s["model"]


def _query(rgb, pt, box=None):
    """One SAM2 forward; returns [(small_mask, small_logits, score), ...]."""
    import numpy as _np
    import torch
    st = _state()
    proc, model, dev = st["proc"], st["model"], st["device"]
    kw = dict(images=rgb,
              input_points=_np.array([[[[pt[0], pt[1]]]]], dtype=_np.float32),
              input_labels=_np.array([[[1]]], dtype=_np.int32),
              return_tensors="pt")
    if box is not None:
        kw["input_boxes"] = _np.array([[box]], dtype=_np.float32)
    inputs = {k: (v.to(dev) if hasattr(v, "to") else v) for k, v in proc(**kw).items()}
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16, enabled=(dev == "cuda")):
        out = model(**inputs)
    masks = out.pred_masks[0][0]              # (K, hh, ww) logits
    scores = out.iou_scores[0][0].cpu().numpy()
    res = []
    for k in range(masks.shape[0]):
        lg = masks[k]
        while lg.dim() > 2:
            lg = lg[0]
        lg = lg.cpu().numpy().astype(np.float32)
        small = lg > 0.0
        res.append((small, lg, float(scores[k])))
    return res


def _query_batch(crops):
    """Run independent centered point+box prompts for equal-sized crops."""
    import torch
    st = _state()
    proc, model, dev = st["proc"], st["model"], st["device"]
    if not crops:
        return []
    height, width = crops[0].shape[:2]
    if any(crop.shape[:2] != (height, width) for crop in crops):
        raise ValueError("batched SAM2 crops must have equal dimensions")
    count = len(crops)
    if dev == "cuda" and count > 1 and torch.cuda.is_available():
        free_bytes, _ = torch.cuda.mem_get_info()
        if free_bytes < 2_800_000_000:
            midpoint = count // 2
            return (_query_batch(crops[:midpoint])
                    + _query_batch(crops[midpoint:]))
    points = np.tile(np.array([[[[width / 2.0, height / 2.0]]]],
                              dtype=np.float32), (count, 1, 1, 1))
    labels = np.ones((count, 1, 1), dtype=np.int32)
    boxes = np.tile(np.array([[[width * 0.08, height * 0.08,
                               width * 0.92, height * 0.92]]],
                             dtype=np.float32), (count, 1, 1))
    inputs = proc(images=crops, input_points=points, input_labels=labels,
                  input_boxes=boxes, return_tensors="pt")
    inputs = {key: (value.to(dev) if hasattr(value, "to") else value)
              for key, value in inputs.items()}
    try:
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16, enabled=(dev == "cuda")):
            output = model(**inputs)
    except torch.cuda.OutOfMemoryError:
        if count == 1:
            raise
        del inputs
        torch.cuda.empty_cache()
        midpoint = count // 2
        return (_query_batch(crops[:midpoint])
                + _query_batch(crops[midpoint:]))
    results = []
    for batch_index in range(count):
        masks = output.pred_masks[batch_index][0]
        scores = output.iou_scores[batch_index][0].float().cpu().numpy()
        candidates = []
        for candidate_index in range(masks.shape[0]):
            logits = masks[candidate_index]
            while logits.dim() > 2:
                logits = logits[0]
            logits = logits.float().cpu().numpy().astype(np.float32)
            candidates.append((logits > 0.0, logits,
                               float(scores[candidate_index])))
        results.append(candidates)
    return results


def _solidity(small):
    m = small.astype(np.uint8)
    contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0
    hull = cv2.convexHull(max(contours, key=cv2.contourArea))
    ha = cv2.contourArea(hull)
    if ha <= 0:
        return 0.0
    return float(cv2.contourArea(max(contours, key=cv2.contourArea))) / ha


def _select(cands, *, require_solid=False):
    """cands: [(small, logits, score)] -> index of winner.

    The single-serving path may fall back to SAM's top-scoring candidate when
    every proposal is irregular. Multi-item detection cannot safely promote
    that fallback to an extra serving, so it can require a solid candidate.
    """
    n = len(cands)
    if n == 0:
        return None
    area = np.array([float(c[0].mean()) for c in cands])
    solid = np.array([_solidity(c[0]) >= SOLIDITY_MIN
                      and AREA_MIN <= a <= AREA_MAX
                      for c, a in zip(cands, area)])
    score = np.array([c[2] for c in cands])

    def pick(idx):
        return int(idx[np.argmax(score[idx])]) if len(idx) else None

    if not solid.any():
        if require_solid:
            return None
        return int(np.argmax(score))

    # strict-parent relation among solid candidates
    has_parent = np.zeros(n, dtype=bool)
    has_child = np.zeros(n, dtype=bool)
    idx_s = np.where(solid)[0]
    for i in idx_s:
        for j in idx_s:
            if i == j or area[j] <= area[i]:
                continue
            inter = float((cands[i][0] & cands[j][0]).sum())
            if inter >= PARENT_FRAC * float(cands[i][0].sum()):
                has_parent[i] = True
                has_child[j] = True
    eligible = idx_s[has_parent[idx_s]]
    if len(eligible):
        mid = eligible[has_child[eligible]]
        return int(mid[np.argmax(score[mid])]) if len(mid) else pick(eligible)
    return pick(idx_s)


def segment_food(image_bgr):
    """Segment the food region of a top-down capture.

    Returns dict: mask bool (H, W), strategy, sam_score, n_candidates.
    """
    H, W = image_bgr.shape[:2]
    _load()
    max_side = max(H, W)
    if max_side > 1024:
        s = 1024.0 / max_side
        new_W, new_H = int(round(W * s)), int(round(H * s))
        image_scaled = cv2.resize(image_bgr, (new_W, new_H), interpolation=cv2.INTER_AREA)
    else:
        image_scaled = image_bgr
        new_W, new_H = W, H

    rgb = cv2.cvtColor(image_scaled, cv2.COLOR_BGR2RGB)
    cx, cy = new_W / 2.0, new_H / 2.0

    cands = _query(rgb, (cx, cy))
    strategy = "centre_point"
    k = _select(cands)
    # A point prompt inside a bowl can come back as a sliver (ledger 014:
    # 0.08% / 0.18% of frame on real canteen photos, sometimes with a high
    # SAM score). Treat sub-AREA_MIN as a failed query and retry with the
    # box prompt rather than measuring a speck as the whole serving.
    if k is None or cands[k][0].mean() > AREA_MAX or cands[k][0].mean() < AREA_MIN:
        box = [new_W * 0.2, new_H * 0.2, new_W * 0.8, new_H * 0.8]
        cands = _query(rgb, (cx, cy), box=box)
        strategy = "centre_box"
        k = _select(cands)
        if k is not None and not (AREA_MIN <= cands[k][0].mean() <= AREA_MAX):
            # A box prompt that still returns a speck (or the whole frame) is
            # not a serving: fail loudly so the stage degrades instead of
            # reporting a plausible-looking portion from a bad mask.
            k = None
    if k is None:
        raise RuntimeError("SAM2 produced no usable food mask")

    small, logits, score = cands[k]
    full = cv2.resize(logits, (W, H), interpolation=cv2.INTER_LINEAR) > 0.0
    if not full.any():
        full = cv2.resize(small.astype(np.uint8), (W, H),
                          interpolation=cv2.INTER_NEAREST).astype(bool)
    return {
        "mask": full,
        "strategy": strategy,
        "sam_score": score,
        "n_candidates": len(cands),
        "area_frac": float(full.mean()),
    }


# --- multi-vessel detection (spec 003) --------------------------------------

IOU_DEDUPE = 0.45       # masks closer than this are the same vessel
CONTAIN_DEDUPE = 0.65   # ...or this much of the smaller mask is covered
ITEM_CROP_FRAC = 0.34   # preserve context while adding denser seed coverage
ITEM_GRID = (0.16, 0.33, 0.50, 0.67, 0.84)
ITEM_PROMPT_BATCH = 4   # dense prompts without one GPU pass per point
ITEM_AREA_MIN = 0.001   # retain small semantic portions on a shared plate


def _iou(a, b):
    union = float((a | b).sum())
    return float((a & b).sum()) / union if union else 0.0


def _same_vessel(a, b):
    """Same bowl seen at different mask tightness: full IoU dedupe misses a
    food-only mask inside a bowl-and-plate mask (IoU ~0.5 but containment ~1),
    which double-counted vessels and inflates truncated_count."""
    inter = float((a & b).sum())
    if inter == 0:
        return False
    if inter / float((a | b).sum()) >= IOU_DEDUPE:
        return True
    smaller = min(float(a.sum()), float(b.sum()))
    return smaller > 0 and inter / smaller >= CONTAIN_DEDUPE


def _bbox(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def _crop_bounds(length, center_frac, crop_frac=ITEM_CROP_FRAC):
    """Return a fixed-size crop around a normalized point, clamped to image."""
    size = min(length, max(1, round(length * crop_frac)))
    start = max(0, min(length - size,
                        round(length * center_frac - size / 2)))
    return start, start + size


def segment_items(image_bgr):
    """Detect distinct food regions using a dense, batched local point grid.

    Each point is evaluated in its own crop so adjacent food regions can be
    proposed independently. Candidates are deduplicated and area-gated; no
    fixed maximum silently truncates a meal.
    """
    H, W = image_bgr.shape[:2]
    _load()
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    prompts = []
    for gy in ITEM_GRID:
        y1, y2 = _crop_bounds(H, gy)
        for gx in ITEM_GRID:
            x1, x2 = _crop_bounds(W, gx)
            prompts.append(((gx, gy), (x1, y1, x2, y2), rgb[y1:y2, x1:x2]))

    kept = []  # (full-frame projected mask, score), largest first
    rejected = []
    for offset in range(0, len(prompts), ITEM_PROMPT_BATCH):
        batch = prompts[offset:offset + ITEM_PROMPT_BATCH]
        batch_candidates = _query_batch([entry[2] for entry in batch])
        for ((gx, gy), (x1, y1, x2, y2), _crop_rgb), cands in zip(
                batch, batch_candidates):
            crop_rgb = _crop_rgb
            crop_h, crop_w = crop_rgb.shape[:2]
            k = _select(cands, require_solid=True)
            if k is None:
                rejected.append({
                    "point": (gx, gy),
                    "crop": (x1, y1, x2, y2),
                    "candidates": [
                        (round(float(mask.mean()), 4),
                         round(_solidity(mask), 3), round(score, 3))
                        for mask, _logits, score in cands
                    ],
                })
                continue
            small, _logits, score = cands[k]
            local_mask = cv2.resize(
                _logits, (crop_w, crop_h),
                interpolation=cv2.INTER_LINEAR) > 0.0
            full = np.zeros((H, W), dtype=bool)
            full[y1:y2, x1:x2] = local_mask
            area_frac = float(full.mean())
            if not (ITEM_AREA_MIN <= area_frac <= AREA_MAX):
                rejected.append({
                    "point": (gx, gy),
                    "crop": (x1, y1, x2, y2),
                    "selected": k,
                    "area": round(area_frac, 4),
                    "solidity": round(_solidity(small), 3),
                    "score": round(score, 3),
                    "reason": "area",
                })
                continue
            if all(not _same_vessel(full, m) for m, _ in kept):
                kept.append((full, score))
    kept.sort(key=lambda m: float(m[0].sum()), reverse=True)
    candidate_count = len(kept)
    if not kept:
        log.warning(
            "SAM2 dense-grid detector found no usable region; prompt proposals "
            "(area fraction, solidity, SAM score): %s", rejected)
        raise RuntimeError("SAM2 produced no usable food mask")

    items = []
    for full, score in kept:
        items.append({"mask": full, "sam_score": score,
                      "area_frac": float(full.mean()), "bbox": _bbox(full)})
    return {
        "items": items,
        "strategy": "dense_grid_box",
        "candidate_count": candidate_count,
        "truncated_count": 0,
        "seed_prompt_count": len(prompts),
    }
