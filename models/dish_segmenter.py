"""SAM2.1 food segmentation (S2).

Strategy (validated against the synthetic renderer, tests/test_s2.py):
  1. Prompt SAM2.1 at the image centre (protocol: vessel is centred).
  2. Keep the 3 multimask candidates that are *solid* blobs
     (fill ratio >= SOLIDITY_MIN) and in a sane area range.
  3. Pick the candidate that is a strict subset of another solid candidate
     (food sits inside plate/table context), preferring one that also
     contains a smaller solid candidate (middle of a nested chain),
     tie-broken by SAM's predicted IoU score.
     On the synthetic scene this selects the food mask (IoU 0.97 vs GT);
     SAM's raw score alone picks a rim arc (IoU 0.38) — do not use it.
  4. Fallbacks: no parent found -> best-scoring solid mask; no solid mask
     at all -> best-scoring candidate; centre query produced nothing ->
     one box-prompted query (centre 20-80% square).

Model: facebook/sam2.1-hiera-large (Apache-2.0, docs/licenses.md).
Weights download on first use (HF_HUB_DISABLE_XET=1 is recommended —
the xet backend stalls in this environment).
"""
import os

import cv2
import numpy as np

MODEL_ID = "facebook/sam2.1-hiera-large"
SOLIDITY_MIN = 0.85
AREA_MIN, AREA_MAX = 0.005, 0.7
PARENT_FRAC = 0.90          # area(i ∩ j) / area(i) >= this => i ⊂ j

_STATE = {}


def _device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _load():
    if _STATE:
        return _STATE["proc"], _STATE["model"]
    from transformers import Sam2Model, Sam2Processor
    dev = _device()
    proc = Sam2Processor.from_pretrained(MODEL_ID)
    model = Sam2Model.from_pretrained(MODEL_ID).to(dev).eval()
    _STATE.update(proc=proc, model=model, device=dev)
    return proc, model


def _query(rgb, pt, box=None):
    """One SAM2 forward; returns [(small_mask, small_logits, score), ...]."""
    import numpy as _np
    import torch
    proc, model, dev = _STATE["proc"], _STATE["model"], _STATE["device"]
    kw = dict(images=rgb,
              input_points=_np.array([[[[pt[0], pt[1]]]]], dtype=_np.float32),
              input_labels=_np.array([[[1]]], dtype=_np.int32),
              return_tensors="pt")
    if box is not None:
        kw["input_boxes"] = _np.array([[box]], dtype=_np.float32)
    inputs = {k: (v.to(dev) if hasattr(v, "to") else v) for k, v in proc(**kw).items()}
    with torch.no_grad():
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


def _select(cands):
    """cands: [(small, logits, score)] -> index of winner."""
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
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    cx, cy = W / 2.0, H / 2.0

    cands = _query(rgb, (cx, cy))
    strategy = "centre_point"
    k = _select(cands)
    if k is None or cands[k][0].mean() > AREA_MAX:
        box = [W * 0.2, H * 0.2, W * 0.8, H * 0.8]
        cands = _query(rgb, (cx, cy), box=box)
        strategy = "centre_box"
        k = _select(cands)
    if k is None:
        raise RuntimeError("SAM2 produced no mask candidates")

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
