"""P1: evaluate our current no-card (prior-tier) portion estimate on WED.

Honest "before" number for the learned weight head. For every test-split
view we run the production prior-tier geometry path (size-prior footprint +
MoGe depth + ring/table base plane — the exact estimate_portion code the
pipeline uses when no reference card is found) and compare against the
dataset's kitchen-scale gram labels:

  per-ROI  — each dish mask (labelIds) estimated as a single-component dish
             (this is what the learned head replaces at inference)
  merged   — union of all dish masks vs the plate's total grams
             (diagnostic: what a whole-plate prior guess would say)

Depth is MoGe (uncalibrated — prior tier has no card), cached under
/tmp/wed_depth so reruns are fast. Densities come from menu.yaml where a
WED dish maps to one of ours, else 1.0 g/ml assumed.

Run:  .venv/bin/python -m tools.eval_prior_tier_on_wed [--split test] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import cv2  # noqa: E402

from config import load_anchor_config, load_params  # noqa: E402
from engine.depth import MonocularDepth  # noqa: E402
from geo.pose import camera_matrix  # noqa: E402
from models.portion_estimator import estimate_portion  # noqa: E402
from models.scale_anchor import prior_anchor  # noqa: E402

# WED class -> effective density g/ml (menu.yaml where mapped, else 1.0)
DENSITY = {
    "steamed-rice": 0.75, "veg-pulao": 0.85, "bisi-bele-bath": 0.90,
    "sambar": 1.03, "curd": 1.03, "rasam": 1.00, "chutney": 1.00,
    "raita": 1.03, "papad": 0.60, "salad": 0.70, "phulka": 0.55,
    "payasam": 1.02, "boondi": 0.90, "mango-pickle": 1.10,
}
DEFAULT_DENSITY = 1.0

DEPTH_CACHE = Path("/tmp/wed_depth")


def _pseudo_dish(density: float) -> dict:
    return {"components": {"food": {"share": 1.0, "density_g_ml": density}}}


def _depth_for(image_bgr, stem: str, provider: MonocularDepth) -> np.ndarray:
    DEPTH_CACHE.mkdir(parents=True, exist_ok=True)
    cache = DEPTH_CACHE / f"{stem}.npy"
    if cache.is_file():
        return np.load(cache)
    out = provider(image_bgr)
    depth = np.asarray(out["depth_m"], dtype=np.float64)
    np.save(cache, depth)
    return depth


def evaluate(split: str, limit: int | None) -> dict:
    rows = []
    with (_ROOT / "data" / "wed_manifest.jsonl").open() as fh:
        for line in fh:
            r = json.loads(line)
            if r["split"] == split:
                rows.append(r)
    if limit:
        rows = rows[:limit]

    cfg = load_anchor_config()
    params = load_params()
    cam = cfg["camera"]
    anchor = prior_anchor("WED baseline — no reference card", cfg)
    depth_provider = MonocularDepth()

    per_roi_errors, per_class_errors, failures = [], {}, []
    plate_errors = []
    t0 = time.time()

    _wed_default = _ROOT / "data" / "wed"
    for i, row in enumerate(rows):
        image_path = Path(cfg.get("_wed_root", str(_wed_default))) / row["image"]
        mask_path = Path(cfg.get("_wed_root", str(_wed_default))) / row["mask"]
        image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        label_mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if image_bgr is None or label_mask is None:
            failures.append({"row": i, "why": "imread failed"})
            continue
        H, W = image_bgr.shape[:2]
        K = camera_matrix(cam["focal_length_fallback_mm"],
                          cam.get("sensor_width_mm", 6.17), W, H)
        depth = _depth_for(image_bgr, f"{row['date_key']}_{row['set']}_{Path(row['image']).stem}",
                           depth_provider)

        plate_gt = sum(d["weight_g"] for d in row["dishes"])
        merged_est = None
        try:
            union = np.isin(label_mask, [d["class_id"] for d in row["dishes"]])
            out = estimate_portion(image_bgr, union, depth, anchor, {"K": K},
                                   _pseudo_dish(DEFAULT_DENSITY),
                                   params=params)
            merged_est = out["grams"]
            plate_errors.append({"pred": merged_est, "gt": plate_gt,
                                 "err": merged_est - plate_gt})
        except Exception as e:
            failures.append({"row": i, "stage": "merged", "why": str(e)})

        for dish in row["dishes"]:
            roi = label_mask == dish["class_id"]
            if int(roi.sum()) < 64:
                failures.append({"row": i, "stage": "roi", "name": dish["name"],
                                 "why": f"mask too small ({int(roi.sum())} px)"})
                continue
            try:
                out = estimate_portion(image_bgr, roi, depth, anchor, {"K": K},
                                       _pseudo_dish(DENSITY.get(dish["name"], DEFAULT_DENSITY)),
                                       params=params)
                err = out["grams"] - dish["weight_g"]
                per_roi_errors.append({"name": dish["name"], "pred": out["grams"],
                                       "gt": dish["weight_g"], "err": err})
                per_class_errors.setdefault(dish["name"], []).append(err)
            except Exception as e:
                failures.append({"row": i, "stage": "roi", "name": dish["name"],
                                 "why": str(e)})

        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(rows)} views "
                  f"({time.time() - t0:.0f}s, {len(failures)} failures)", flush=True)

    def _stats(errors):
        if not errors:
            return {"n": 0}
        e = np.array(errors, dtype=float)
        return {"n": int(e.size), "mae": float(np.abs(e).mean()),
                "median_ae": float(np.median(np.abs(e))),
                "bias": float(e.mean())}

    roi_preds = np.array([r["pred"] for r in per_roi_errors])
    roi_gts = np.array([r["gt"] for r in per_roi_errors])
    report = {
        "split": split,
        "views": len(rows),
        "per_roi": _stats([r["err"] for r in per_roi_errors]),
        "per_roi_mape_pct": float(np.mean(np.abs(roi_preds - roi_gts) /
                                          np.maximum(roi_gts, 1e-8)) * 100) if len(roi_gts) else None,
        "merged_plate": _stats([p["err"] for p in plate_errors]),
        "per_class_mae": {k: float(np.abs(np.array(v)).mean())
                          for k, v in sorted(per_class_errors.items())},
        "failures": len(failures),
        "failure_examples": failures[:10],
        "elapsed_s": round(time.time() - t0, 1),
    }
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", default="test", choices=["train", "test"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=str(_ROOT / "data" / "reports" / "prior_tier_wed.json"))
    args = ap.parse_args()

    report = evaluate(args.split, args.limit)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("per_class_mae", "failure_examples")}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
