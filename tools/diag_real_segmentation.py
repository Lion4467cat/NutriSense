"""Diagnose SAM2 prompting on real canteen photos (M1/M3 gate, ledger 014).

The serving path prompts SAM2.1 with a single centre point and keeps one
mask (models/dish_segmenter.py). That is validated on synthetic renders
where one vessel is centred; real phone captures of a thali defeat it —
the point lands inside one bowl and the mask is that bowl, so the whole
plate is measured as a single dish.

This script measures, per photo, three prompt strategies against the SAME
checkpoint:

  centre_point  the deployed path: one point at the frame centre
  centre_box    one point + a coarse centre box (the deployed fallback)
  grid9_box     3x3 points inside a coarse centre box, masks deduped by
                IoU and unioned — a cheap multi-vessel prompt with no
                extra model

There is no pixel ground truth for these canteen photos (they were
captured without a card), so the report records area, SAM IoU score,
runtime and the number of distinct vessels. It is evidence about *what
the masks are*, not an accuracy claim: no gate is evaluated here.

Usage:
  .venv/bin/python tools/diag_real_segmentation.py \
      --dataset ../DATASET --per-class 3 \
      --out data/reports/real_segmentation_diag.json
"""
import argparse
import json
import time
from pathlib import Path

import cv2
import numpy as np

from models import dish_segmenter as ds

IOU_DEDUPE = 0.70


def _iou(a, b):
    inter = float((a & b).sum())
    union = float((a | b).sum())
    return inter / union if union else 0.0


def _distinct(masks, iou_thr=IOU_DEDUPE):
    """Greedy dedupe: keep the largest mask, drop near-duplicates."""
    ordered = sorted(masks, key=lambda m: float(m[0].sum()), reverse=True)
    kept = []
    for small, score in ordered:
        if all(_iou(small, k[0]) < iou_thr for k in kept):
            kept.append((small, score))
    return kept


def _union(masks, shape):
    out = np.zeros(shape, dtype=bool)
    for small, _ in masks:
        full = cv2.resize(small.astype(np.uint8), (shape[1], shape[0]),
                          interpolation=cv2.INTER_NEAREST).astype(bool)
        out |= full
    return out


def _single(cands):
    k = ds._select(cands)
    if k is None:
        return None, 0.0
    small, _logits, score = cands[k]
    return small, score


def run_strategy(rgb, name):
    H, W = rgb.shape[:2]
    box = [W * 0.10, H * 0.10, W * 0.90, H * 0.90]
    t0 = time.time()

    if name == "centre_point":
        cands = ds._query(rgb, (W / 2.0, H / 2.0))
        masks = [m for m in [_single(cands)] if m[0] is not None]
    elif name == "centre_box":
        cands = ds._query(rgb, (W / 2.0, H / 2.0), box=box)
        masks = [m for m in [_single(cands)] if m[0] is not None]
    elif name == "grid9_box":
        masks = []
        for gy in (0.3, 0.5, 0.7):
            for gx in (0.3, 0.5, 0.7):
                cands = ds._query(rgb, (W * gx, H * gy), box=box)
                small, score = _single(cands)
                if small is not None:
                    masks.append((small, score))
        masks = _distinct(masks)
    else:  # pragma: no cover - argparse restricts
        raise ValueError(name)

    elapsed = time.time() - t0
    if not masks:
        return {"strategy": name, "masks": 0, "area_frac": 0.0,
                "sam_score": 0.0, "seconds": round(elapsed, 2)}
    union = _union(masks, (H, W))
    return {
        "strategy": name,
        "masks": len(masks),
        "area_frac": round(float(union.mean()), 4),
        "sam_score": round(float(np.mean([m[1] for m in masks])), 4),
        "seconds": round(elapsed, 2),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="../DATASET")
    ap.add_argument("--per-class", type=int, default=3)
    ap.add_argument("--out", default="data/reports/real_segmentation_diag.json")
    args = ap.parse_args(argv)

    root = Path(args.dataset)
    dishes = sorted(p for p in root.iterdir() if p.is_dir())
    rows = []
    for dish in dishes:
        photos = sorted(dish.glob("*.jpg"))[: args.per_class]
        for photo in photos:
            bgr = cv2.imread(str(photo), cv2.IMREAD_COLOR)
            if bgr is None:
                continue
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            row = {"dish": dish.name, "photo": photo.name,
                   "size": [bgr.shape[1], bgr.shape[0]]}
            for strategy in ("centre_point", "centre_box", "grid9_box"):
                row[strategy] = run_strategy(rgb, strategy)
                print(f"{dish.name}/{photo.name} {strategy}: {row[strategy]}")
            rows.append(row)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"photos": rows}, indent=2) + "\n")
    print(f"wrote {out} ({len(rows)} photos)")


if __name__ == "__main__":
    main()
