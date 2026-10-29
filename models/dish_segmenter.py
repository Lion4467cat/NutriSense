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
import cv2
import numpy as np

MODEL_ID = "facebook/sam2.1-hiera-large"
SOLIDITY_MIN = 0.85
AREA_MIN, AREA_MAX = 0.005, 0.7
PARENT_FRAC = 0.90          # area(i ∩ j) / area(i) >= this => i ⊂ j


def _device():
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"


def _make_state():
    from transformers import Sam2Model, Sam2Processor
    dev = _device()
    proc = Sam2Processor.from_pretrained(MODEL_ID)
    model = Sam2Model.from_pretrained(MODEL_ID).to(dev).eval()
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
    # A point prompt inside a bowl can come back as a sliver (ledger 014:
    # 0.08% / 0.18% of frame on real canteen photos, sometimes with a high
    # SAM score). Treat sub-AREA_MIN as a failed query and retry with the
    # box prompt rather than measuring a speck as the whole serving.
    if k is None or cands[k][0].mean() > AREA_MAX or cands[k][0].mean() < AREA_MIN:
        box = [W * 0.2, H * 0.2, W * 0.8, H * 0.8]
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

IOU_DEDUPE = 0.70       # masks closer than this are the same vessel
MAX_ITEMS = 4           # per-frame item cap (spec 003 decision 4)


def _iou(a, b):
    union = float((a | b).sum())
    return float((a & b).sum()) / union if union else 0.0


def _bbox(mask):
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def segment_items(image_bgr):
    """Detect distinct food vessels on a (possibly multi-item) capture.

    3x3 point grid inside a coarse centre box (the grid9_box diagnostic
    strategy of ledger 014, promoted to a serving primitive). Candidates are
    selected with the same _select() logic as the single-mask path, deduped
    by IoU >= IOU_DEDUPE (largest mask wins), area-gated to
    [AREA_MIN, AREA_MAX], and capped at MAX_ITEMS, largest first.

    Returns {"items": [{"mask": bool (H,W), "sam_score", "area_frac",
    "bbox"}], "strategy": "grid9_box"}. Raises RuntimeError when no usable
    mask exists, so the stage degrades honestly like the single-mask path.
    """
    H, W = image_bgr.shape[:2]
    _load()
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    box = [W * 0.1, H * 0.1, W * 0.9, H * 0.9]

    kept = []  # (small_mask, score), largest first
    for gy in (0.3, 0.5, 0.7):
        for gx in (0.3, 0.5, 0.7):
            cands = _query(rgb, (W * gx, H * gy), box=box)
            k = _select(cands)
            if k is None:
                continue
            small, _logits, score = cands[k]
            a = float(small.mean())
            if not (AREA_MIN <= a <= AREA_MAX):
                continue
            if all(_iou(small, m) < IOU_DEDUPE for m, _ in kept):
                kept.append((small, score))
    kept.sort(key=lambda m: float(m[0].sum()), reverse=True)
    kept = kept[:MAX_ITEMS]
    if not kept:
        raise RuntimeError("SAM2 produced no usable food mask")

    items = []
    for small, score in kept:
        full = cv2.resize(small.astype(np.uint8), (W, H),
                          interpolation=cv2.INTER_NEAREST).astype(bool)
        items.append({"mask": full, "sam_score": score,
                      "area_frac": float(full.mean()), "bbox": _bbox(full)})
    return {"items": items, "strategy": "grid9_box"}
