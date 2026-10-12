"""Tiered evaluation of the no-card learned weight head — deployable path only.

Scores data/weight_head.pt through `WeightHead.load(...)` + `.eval()` — the
exact production load path — reading ROIs batched the way
tools/train_weight_head.evaluate_mae does, so numbers stay comparable with
the training report. Never touches the in-process training model.

Reports (docs/eval_protocol.md defines every term):
  1. weight MAE (g) and mean absolute % error, overall and per dish (MAPE
     excludes ground truth below 1 g — WED ships a few weight_g = 0 rows)
  2. 90% interval coverage and mean interval width — per-dish sigma_g from
     data/weight_head_sigma.yaml, Gaussian band pred +- 1.6448536 * sigma
  3. the number of samples skipped for lack of sigma (dish has no entry)
  4. bootstrap 95% confidence intervals over PLATES (not views) for MAE and
     coverage — 2000 replicates, fixed seed
  5. the tier, printed with every line and saved in the JSON report

Tiers:
  train   — WED train split (in-sample; it CONTAINS the DEV carve, so its
            numbers are optimistic and never a tuning signal)
  dev     — WED val carve: 10% of train plates, shuffled with seed 42 exactly
            as tools/train_weight_head.carve does (+ data/dev_real/ if that
            manifest ever appears, scored as a separate block)
  locked  — WED test split. Requires --i-know-this-is-locked and appends a
            line (utc, git commit, flag, result summary) to
            docs/locked_access_log.txt.

`--stress` runs the frozen five-perturbation suite (tools/stress_suite.py)
on DEV images only and labels every stress result
"WED stress test, not real-world".

Run:
  .venv/bin/python -m tools.run_eval --tier dev
  .venv/bin/python -m tools.run_eval --tier dev --stress
  .venv/bin/python -m tools.run_eval --tier train --seed 42 \
      --out data/reports/run_eval_train.json
  .venv/bin/python -m tools.run_eval --tier locked --i-know-this-is-locked
"""
from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from models.weight_head import WeightHead  # noqa: E402
from tools.stress_suite import PERTURBATIONS, STRESS_LABEL, PerturbedWedPlates  # noqa: E402
from tools.train_weight_head import (  # noqa: E402
    WedPlates,
    build_rois,
    collate,
    load_manifest,
    plate_key,
)

Z90 = 1.6448536269514722          # two-sided 90% normal quantile
BOOTSTRAP_REPS = 2000
SPLIT_SEED = 42                   # val carve seed — fixed, never user-tunable
VAL_FRAC = 0.10
LOCKED_LOG = _ROOT / "docs" / "locked_access_log.txt"
LOADED: list[str] = []            # manifest splits read this process (guard)


# ----------------------------------------------------------------- splits --
def _manifest(split: str) -> list[dict]:
    LOADED.append(split)
    return load_manifest(split)


def train_rows() -> list[dict]:
    return _manifest("train")


def dev_rows() -> list[dict]:
    """Val carve — identical arithmetic to train_weight_head.main (seed 42)."""
    rows = _manifest("train")
    plates = sorted({plate_key(r) for r in rows})
    random.Random(SPLIT_SEED).shuffle(plates)
    n_val = max(1, int(len(plates) * VAL_FRAC))
    val_plates = set(plates[:n_val])
    return [r for r in rows if plate_key(r) in val_plates]


def dev_real_rows() -> tuple[list[dict], Path] | None:
    """Optional future dev_real capture: data/dev_real/manifest.jsonl."""
    root = _ROOT / "data" / "dev_real"
    path = root / "manifest.jsonl"
    if not path.exists():
        return None
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return rows, root


def wed_root() -> Path:
    cfg = yaml.safe_load((_ROOT / "data" / "wed_dishes.yaml").read_text())
    root = Path(cfg["dataset"]["root"])
    return root if root.is_absolute() else _ROOT / root


def slot_names() -> dict[int, str]:
    raw = json.loads((_ROOT / "data" / "wed" / "index_map.json").read_text())
    return {int(k) - 1: v for k, v in raw.items() if v != "background"}


def sigma_map() -> dict[str, float]:
    doc = yaml.safe_load((_ROOT / "data" / "weight_head_sigma.yaml").read_text())
    return {k: float(v) for k, v in (doc.get("sigma_g") or {}).items()}


# --------------------------------------------------------------- scoring --
@torch.no_grad()
def score(model, rows: list[dict], root: Path, device, *, batch: int = 4,
          perturb=None) -> list[dict]:
    """One record per dish ROI: plate, dish, prediction, ground truth, error."""
    ds = (PerturbedWedPlates(rows, root, perturb) if perturb is not None
          else WedPlates(rows, root, train=False))
    loader = DataLoader(ds, batch_size=batch, shuffle=False, collate_fn=collate,
                        num_workers=0)
    names = slot_names()
    model.eval()
    out: list[dict] = []
    for batch_items in loader:
        imgs = torch.stack([s["img"] for s in batch_items]).to(device)
        feats = model.encode(imgs)
        rois, weights, cls_ids = build_rois(batch_items, feats)
        preds = model(feats, rois)
        pred = preds[torch.arange(preds.size(0), device=device), cls_ids]
        p = pred.cpu().numpy()
        w = weights.cpu().numpy()
        c = cls_ids.cpu().numpy()
        k = 0
        for s in batch_items:
            for _ in s["cls_ids"]:
                slot = int(c[k])
                out.append({"plate": s["key"],
                            "dish": names.get(slot, f"slot{slot}"),
                            "pred": float(p[k]), "gt": float(w[k]),
                            "err": float(p[k] - w[k])})
                k += 1
    return out


def bootstrap(samples: list[dict], has_sigma: list[bool], covered: list[bool | None],
              seed: int) -> tuple[list[float] | None, list[float] | None]:
    """Percentile 95% CIs from resampling PLATES with replacement."""
    by_plate: dict[str, list[int]] = defaultdict(list)
    for i, s in enumerate(samples):
        by_plate[s["plate"]].append(i)
    plates = sorted(by_plate)
    if len(plates) < 2:
        return None, None
    rng = np.random.default_rng(seed)
    errs = np.array([abs(s["err"]) for s in samples], dtype=float)
    maes: list[float] = []
    covs: list[float] = []
    for _ in range(BOOTSTRAP_REPS):
        pick = rng.integers(0, len(plates), size=len(plates))
        idx = [i for j in pick for i in by_plate[plates[int(j)]]]
        maes.append(float(errs[idx].mean()))
        vis = [i for i in idx if has_sigma[i]]
        if vis:
            covs.append(float(np.mean([1.0 if covered[i] else 0.0 for i in vis])))
    def ci(vals: list[float]) -> list[float] | None:
        if not vals:
            return None
        return [round(float(x), 3) for x in np.percentile(vals, [2.5, 97.5])]
    return ci(maes), ci(covs)


def summarize(samples: list[dict], *, tier: str, seed: int, views: int) -> dict:
    if not samples:
        raise RuntimeError(f"tier {tier}: no samples scored")
    sig = sigma_map()
    errs = np.array([s["err"] for s in samples], dtype=float)
    gts = np.array([s["gt"] for s in samples], dtype=float)
    has_sigma, covered, widths = [], [], []
    skipped = 0
    for s in samples:
        g = sig.get(s["dish"])
        if g is None:
            skipped += 1
            has_sigma.append(False)
            covered.append(False)
            continue
        lo, hi = s["pred"] - Z90 * g, s["pred"] + Z90 * g
        has_sigma.append(True)
        covered.append(bool(lo <= s["gt"] <= hi))
        widths.append(hi - lo)
    per_dish: dict[str, list[float]] = defaultdict(list)
    for s in samples:
        per_dish[s["dish"]].append(abs(s["err"]))
    per_dish_mae = {k: round(float(np.mean(v)), 2) for k, v in
                    sorted(per_dish.items(), key=lambda kv: -np.mean(kv[1]))}
    mae_ci, cov_ci = bootstrap(samples, has_sigma, covered, seed)
    valid_cov = [1.0 if covered[i] else 0.0
                 for i in range(len(covered)) if has_sigma[i]]
    # MAPE: gt < 1 g is excluded (WED carries a handful of weight_g = 0 rows;
    # a percentage error against a zero label is meaningless)
    pct_ok = gts >= 1.0
    mape = (round(float((np.abs(errs)[pct_ok] / gts[pct_ok]).mean()) * 100, 2)
            if pct_ok.any() else None)
    return {
        "tier": tier,
        "n_views": views,
        "n_plates": len({s["plate"] for s in samples}),
        "n_samples": len(samples),
        "mae_g": round(float(np.abs(errs).mean()), 3),
        "mae_g_bootstrap_95ci": mae_ci,
        "mape_pct": mape,
        "n_mape_excluded_lt1g": int((~pct_ok).sum()),
        "coverage_90": round(float(np.mean(valid_cov)), 4) if valid_cov else None,
        "coverage_bootstrap_95ci": cov_ci,
        "mean_interval_width_g": (round(float(np.mean(widths)), 2) if widths else None),
        "n_skipped_no_sigma": skipped,
        "per_dish_mae_g": per_dish_mae,
        "worst3_dishes": list(per_dish_mae.items())[:3],
    }


# ------------------------------------------------------------- reporting --
def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       cwd=_ROOT, text=True, timeout=10).strip()
    except Exception:
        return "unknown"


def _print_block(rep: dict) -> None:
    t = rep["tier"]
    print(f"tier={t} views={rep['n_views']} plates={rep['n_plates']} "
          f"samples={rep['n_samples']} skipped_no_sigma={rep['n_skipped_no_sigma']}",
          flush=True)
    print(f"tier={t} mae_g={rep['mae_g']} "
          f"mae_g_bootstrap_95ci={rep['mae_g_bootstrap_95ci']} "
          f"mape_pct={rep['mape_pct']} "
          f"n_mape_excluded_lt1g={rep['n_mape_excluded_lt1g']}", flush=True)
    print(f"tier={t} coverage_90={rep['coverage_90']} "
          f"coverage_bootstrap_95ci={rep['coverage_bootstrap_95ci']} "
          f"mean_interval_width_g={rep['mean_interval_width_g']}", flush=True)
    print(f"tier={t} worst3_dishes={rep['worst3_dishes']}", flush=True)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(_ROOT))
    except ValueError:
        return str(path)


def _append_locked_log(rep: dict, out: Path) -> None:
    line = (f"{datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}"
            f" | git={_git_sha()} | tier=locked | seed={rep['seed']}"
            f" | flag=--i-know-this-is-locked"
            f" | views={rep['n_views']} samples={rep['n_samples']}"
            f" | mae_g={rep['mae_g']} mape_pct={rep['mape_pct']}"
            f" | coverage_90={rep['coverage_90']}"
            f" | n_skipped_no_sigma={rep['n_skipped_no_sigma']}"
            f" | out={_rel(out)}\n")
    with LOCKED_LOG.open("a") as fh:
        fh.write(line)


# ------------------------------------------------------------------ main --
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", choices=("train", "dev", "locked"), required=True)
    ap.add_argument("--seed", type=int, default=42,
                    help="bootstrap seed (the split carve seed is fixed at 42)")
    ap.add_argument("--out", default=None,
                    help="JSON report path (default data/reports/run_eval_<tier>.json)")
    ap.add_argument("--stress", action="store_true",
                    help="also run the frozen five-perturbation suite (DEV only)")
    ap.add_argument("--i-know-this-is-locked", action="store_true",
                    help="required for --tier locked: read the WED test split "
                         "and append to docs/locked_access_log.txt")
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None,
                    help="smoke only: score the first N views (recorded in the report)")
    args = ap.parse_args(argv)

    if args.tier == "locked" and not args.i_know_this_is_locked:
        ap.error("--tier locked requires --i-know-this-is-locked "
                 "(the WED test split is read once, deliberately)")
    if args.stress and args.tier != "dev":
        ap.error("--stress is DEV-only (the WED stress suite runs on the "
                 "DEV carve, never on train or locked)")

    if args.tier == "train":
        rows = train_rows()
        split_note = "WED train split (in-sample: contains the DEV carve)"
    elif args.tier == "dev":
        rows = dev_rows()
        split_note = "WED val carve from train plates (seed 42, 10% of plates)"
    else:
        rows = _manifest("test")
        split_note = "WED test split (locked)"
    if "test" in LOADED and args.tier != "locked":
        raise RuntimeError(f"split guard: test read for tier {args.tier}")
    if args.limit is not None:
        rows = rows[:args.limit]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out = Path(args.out) if args.out else (
        _ROOT / "data" / "reports" / f"run_eval_{args.tier}"
        f"{'_stress' if args.stress else ''}.json")
    model = WeightHead.load(_ROOT / "data" / "weight_head.pt", device=device)

    samples = score(model, rows, wed_root(), device, batch=args.batch)
    rep = summarize(samples, tier=args.tier, seed=args.seed, views=len(rows))
    rep.update({"split": split_note, "seed": args.seed,
                "split_seed": SPLIT_SEED, "val_frac": VAL_FRAC,
                "bootstrap_reps": BOOTSTRAP_REPS, "z90": round(Z90, 6),
                "device": str(device), "checkpoint": "data/weight_head.pt",
                "limit": args.limit, "stress": None, "dev_real": None})
    _print_block(rep)

    if args.tier == "dev":
        dr = dev_real_rows()
        if dr is not None:
            dr_rows, dr_root = dr
            dr_samples = score(model, dr_rows, dr_root, device, batch=args.batch)
            dr_rep = summarize(dr_samples, tier=args.tier, seed=args.seed,
                               views=len(dr_rows))
            rep["dev_real"] = dr_rep
            _print_block({**dr_rep, "tier": f"{args.tier}/dev_real"})
        if args.stress:
            stress = {}
            for name, fn in PERTURBATIONS.items():
                s_samples = score(model, rows, wed_root(), device,
                                  batch=args.batch, perturb=fn)
                s_rep = summarize(s_samples, tier=args.tier, seed=args.seed,
                                  views=len(rows))
                s_rep["label"] = STRESS_LABEL
                stress[name] = s_rep
                print(f"tier={args.tier} stress={name} mae_g={s_rep['mae_g']} "
                      f"n_samples={s_rep['n_samples']} label={STRESS_LABEL!r}",
                      flush=True)
            rep["stress"] = stress

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=2) + "\n")
    print(f"tier={args.tier} wrote {_rel(out)}", flush=True)
    if args.tier == "locked":
        _append_locked_log(rep, out)
        print(f"tier=locked appended {LOCKED_LOG.relative_to(_ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
