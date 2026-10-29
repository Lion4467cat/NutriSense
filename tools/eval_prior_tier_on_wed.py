"""Evaluate the geometry (prior-tier) portion estimate on WED views.

For every split view we run the production prior-tier geometry path
(size-prior footprint + MoGe depth + ring/table base plane — the exact
estimate_portion code the pipeline uses when no reference card is found)
and compare against the dataset's kitchen-scale gram labels:

  per-ROI  — each dish mask (labelIds) estimated as a single-component dish
             (this is what the learned head replaces at inference)
  merged   — union of all dish masks vs the plate's total grams
             (diagnostic: what a whole-plate prior guess would say)

Depth is MoGe, cached under /tmp/wed_depth so reruns are fast. Densities
come from a fixed table (menu values where mapped, else 1.0 g/ml assumed).

Ledger 007 adds --intrinsics {fallback,moge}:
  fallback — camera K from the EXIF-focal fallback (original behaviour,
             bitwise identical for the default)
  moge     — K built from MoGe's predicted normalized intrinsics
             (fx_px = fx_norm * W, principal point W/2, H/2)
Both modes use the SAME cached depth map, so the paired comparison isolates
the unprojection geometry. --compare diffs two reports with a paired
plate-bootstrap 95% CI (seed 42); --depth-scale multiplies the cached depth
by a constant (oracle-scale diagnostic; never a serving proposal).

Run:
  .venv/bin/python -m tools.eval_prior_tier_on_wed --split dev \
      --intrinsics moge --out data/reports/prior_tier_wed_dev_moge.json
  .venv/bin/python -m tools.eval_prior_tier_on_wed --compare \
      data/reports/prior_tier_wed_dev_fallback.json \
      data/reports/prior_tier_wed_dev_moge.json \
      --out data/reports/prior_tier_wed_dev_compare.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import cv2  # noqa: E402
import torch  # noqa: E402

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
SPLIT_SEED = 42
VAL_FRAC = 0.10


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


def _moge_K(intrinsics, W: int, H: int) -> np.ndarray | None:
    """MoGe normalized intrinsics -> pixel K. None when unavailable."""
    if intrinsics is None:
        return None
    K = intrinsics
    if isinstance(K, torch.Tensor):
        K = K.float().cpu().numpy()
    K = np.asarray(K, dtype=np.float64)
    return np.array([[K[0, 0] * W, 0.0, W * K[0, 2]],
                     [0.0, K[1, 1] * H, H * K[1, 2]],
                     [0.0, 0.0, 1.0]])


def _plate_key(row: dict) -> str:
    return f"{row['date_key']}_{row['set']}"


def _rows_for(split: str, limit: int | None) -> list[dict]:
    if split == "dev":
        from tools.run_eval import dev_rows
        rows = dev_rows()
    else:
        rows = []
        with (_ROOT / "data" / "wed_manifest.jsonl").open() as fh:
            for line in fh:
                r = json.loads(line)
                if r["split"] == split:
                    rows.append(r)
    if limit:
        rows = rows[:limit]
    return rows


def evaluate(split: str, limit: int | None, intrinsics: str,
             depth_scale: float = 1.0) -> dict:
    rows = _rows_for(split, limit)

    cfg = load_anchor_config()
    params = load_params()
    cam = cfg["camera"]
    anchor = prior_anchor("WED baseline — no reference card", cfg)
    depth_provider = MonocularDepth()

    per_roi_errors, per_class_errors, failures = [], {}, []
    plate_errors = []
    per_view = []
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
        Ka = {"K": K}
        stem = f"{row['date_key']}_{row['set']}_{Path(row['image']).stem}"
        if intrinsics == "moge":
            DEPTH_CACHE.mkdir(parents=True, exist_ok=True)
            kpath = DEPTH_CACHE / f"{stem}.K.json"
            if kpath.is_file():
                K_m = _moge_K(json.loads(kpath.read_text()), W, H)
            else:
                out = depth_provider(image_bgr)
                K_m = _moge_K(out.get("intrinsics"), W, H)
                if K_m is not None:
                    kpath.write_text(json.dumps(np.asarray(
                        out["intrinsics"].float().cpu().numpy()
                        if isinstance(out["intrinsics"], torch.Tensor)
                        else out["intrinsics"]).tolist()))
            if K_m is not None:
                Ka = {"K": K_m}
            else:
                failures.append({"row": i, "stage": "intrinsics",
                                 "why": "MoGe returned no K"})
        depth = _depth_for(image_bgr, stem, depth_provider) * depth_scale

        plate_gt = sum(d["weight_g"] for d in row["dishes"])
        view_roi_idx = []
        try:
            union = np.isin(label_mask, [d["class_id"] for d in row["dishes"]])
            out = estimate_portion(image_bgr, union, depth, anchor, Ka,
                                   _pseudo_dish(DEFAULT_DENSITY),
                                   params=params)
            plate_errors.append({"plate": _plate_key(row),
                                 "pred": out["grams"], "gt": plate_gt,
                                 "err": out["grams"] - plate_gt})
        except Exception as e:
            failures.append({"row": i, "stage": "merged", "why": str(e)})

        for dish in row["dishes"]:
            roi = label_mask == dish["class_id"]
            if int(roi.sum()) < 64:
                failures.append({"row": i, "stage": "roi", "name": dish["name"],
                                 "why": f"mask too small ({int(roi.sum())} px)"})
                continue
            try:
                out = estimate_portion(image_bgr, roi, depth, anchor, Ka,
                                       _pseudo_dish(DENSITY.get(
                                           dish["name"], DEFAULT_DENSITY)),
                                       params=params)
                err = out["grams"] - dish["weight_g"]
                per_roi_errors.append({"plate": _plate_key(row),
                                       "name": dish["name"],
                                       "pred": out["grams"],
                                       "gt": dish["weight_g"], "err": err})
                view_roi_idx.append(len(per_roi_errors) - 1)
                per_class_errors.setdefault(dish["name"], []).append(err)
            except Exception as e:
                failures.append({"row": i, "stage": "roi", "name": dish["name"],
                                 "why": str(e)})
        per_view.append({"plate": _plate_key(row),
                         "roi_rows": view_roi_idx,
                         "merged_row": len(plate_errors) - 1})

        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(rows)} views "
                  f"({time.time() - t0:.0f}s, {len(failures)} failures)",
                  flush=True)

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
        "intrinsics": intrinsics,
        "depth_scale": depth_scale,
        "views": len(rows),
        "per_roi": _stats([r["err"] for r in per_roi_errors]),
        "per_roi_mape_pct": float(np.mean(np.abs(roi_preds - roi_gts) /
                                          np.maximum(roi_gts, 1e-8)) * 100)
        if len(roi_gts) else None,
        "merged_plate": _stats([p["err"] for p in plate_errors]),
        "per_class_mae": {k: float(np.abs(np.array(v)).mean())
                          for k, v in sorted(per_class_errors.items())},
        "failures": len(failures),
        "failure_examples": failures[:10],
        "per_roi_rows": per_roi_errors,
        "per_view": per_view,
        "elapsed_s": round(time.time() - t0, 1),
    }
    return report


def compare(path_a: str, path_b: str, n_boot: int = 2000,
            seed: int = SPLIT_SEED) -> dict:
    """Paired plate-bootstrap 95% CI of ΔMAE / Δ|bias| (B - A)."""
    ra = json.loads(Path(path_a).read_text())
    rb = json.loads(Path(path_b).read_text())
    if not (ra["intrinsics"] != rb["intrinsics"]
            or ra["depth_scale"] != rb["depth_scale"]):
        raise SystemExit("identical mode/depth_scale: nothing to pair")
    key = lambda r: (r["plate"], r["name"])  # noqa: E731
    ma = {key(r): r["err"] for r in ra["per_roi_rows"]}
    mb = {key(r): r["err"] for r in rb["per_roi_rows"]}
    common = sorted(set(ma) & set(mb))
    if len(common) < len(ma) * 0.5:
        raise SystemExit("<50% row overlap between reports")
    wa = np.array([ma[k] for k in common], dtype=float)
    wb = np.array([mb[k] for k in common], dtype=float)
    plates = sorted({p for p, _ in common})
    idx = {p: np.array([j for j, (q, _) in enumerate(common) if q == p])
           for p in plates}
    rng = np.random.default_rng(seed)
    d_mae, d_bias = [], []
    for _ in range(n_boot):
        pick = rng.choice(plates, size=len(plates), replace=True)
        ia = np.concatenate([idx[p] for p in pick])
        ea, eb = wa[ia], wb[ia]
        d_mae.append(np.abs(eb).mean() - np.abs(ea).mean())
        d_bias.append(eb.mean() - ea.mean())
    q_mae = np.quantile(d_mae, [0.025, 0.5, 0.975])
    q_bias = np.quantile(d_bias, [0.025, 0.5, 0.975])
    return {
        "a": {"path": path_a, "intrinsics": ra["intrinsics"],
              "depth_scale": ra["depth_scale"]},
        "b": {"path": path_b, "intrinsics": rb["intrinsics"],
              "depth_scale": rb["depth_scale"]},
        "n_boot": n_boot, "seed": seed, "plates": len(plates),
        "delta_mae_absmean": q_mae.tolist(),
        "delta_bias": q_bias.tolist(),
        "mae_a": np.abs(wa).mean(), "mae_b": np.abs(wb).mean(),
        "bias_a": float(wa.mean()), "bias_b": float(wb.mean()),
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split", default="test", choices=["train", "test", "dev"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--intrinsics", default="fallback",
                    choices=["fallback", "moge"])
    ap.add_argument("--depth-scale", type=float, default=1.0,
                    help="multiply cached depth by a constant "
                         "(oracle-scale diagnostic; NOT a serving proposal)")
    ap.add_argument("--out", default=str(
        _ROOT / "data" / "reports" / "prior_tier_wed.json"))
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"),
                    help="paired plate-bootstrap comparison of two reports")
    ap.add_argument("--n-boot", type=int, default=2000)
    args = ap.parse_args()

    if args.compare:
        cmp_report = compare(args.compare[0], args.compare[1],
                             n_boot=args.n_boot)
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(cmp_report, indent=2) + "\n")
        print(json.dumps(cmp_report, indent=2))
        print(f"wrote {out}")
        return

    report = evaluate(args.split, args.limit, args.intrinsics,
                      depth_scale=args.depth_scale)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("per_class_mae", "failure_examples",
                                   "per_roi_rows", "per_view")}, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
