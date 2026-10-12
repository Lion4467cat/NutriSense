"""STAGE 1A: BatchNorm train/deploy mismatch — controlled experiment (MEASURE ONLY).

Writes ONLY to /tmp/bn_exp/ (checkpoints, per-run results JSON, aggregate,
logs) — never into the repo, never into data/.

Context: the deployed head loads with stock ImageNet BN statistics, but
training ran the frozen encoder in train mode so its BN running stats adapted
to WED and were never saved (deployed WED val MAE was 24.65 g at the time;
20.30 g after the decision below). Compare:

  A) frozen encoder pinned to eval() during training (BN stays ImageNet)
  B) current behaviour (BN adapts), but the adapted encoder BN buffers are
     saved in the checkpoint and restored by the script-local loader

DECISION (rule-based gate): A won and was adopted in
tools/train_weight_head.py + redeployed data/weight_head.pt. B's clean val
MAE was only ~0.5 g better (19.70 vs 20.23, seed spread 0.44 g) but its
perspective-warp stress MAE blew up 24.7 -> 74.7 g — far beyond noise.

Rules enforced here:
  * WED VAL split only — load_manifest is called with "train" only; any
    "test" split request raises (runtime guard, fails the run).
  * Val plates carved exactly like train_weight_head.main with shuffle seed
    42 and held fixed across runs; only the training seed varies (42/43/44).
  * Model selection mirrors train_weight_head.main (best in-process val MAE
    -> best head state); that in-process number is NEVER reported — every
    reported metric is measured after save -> WeightHead.load -> evaluate.
  * All checkpoints/outputs go to /tmp/bn_exp/, never into the repo.

Run (one option/seed per invocation; stress rides along every seed):
  .venv/bin/python -m tools.bn_experiment --option A --seed 42 --stress
"""
from __future__ import annotations

import argparse
import io
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml
from PIL import Image
from torch.optim import AdamW
from torch.optim.lr_scheduler import OneCycleLR
from torch.utils.data import DataLoader
from torchvision.transforms import functional as TF

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from models.weight_head import WeightHead  # noqa: E402
from tools import train_weight_head as TWH  # noqa: E402
from tools.train_weight_head import (  # noqa: E402
    RGB_TF, MASK_TF, WedPlates, build_rois, collate, plate_key,
)

OUT_DIR = Path("/tmp/bn_exp")
SPLIT_SEED = 42          # val-plate carve — fixed for every run
BN_SUFFIXES = ("running_mean", "running_var", "num_batches_tracked")
CALL_LOG: list[tuple[str, ...]] = []  # split names requested via load_manifest


def _guarded_load_manifest(split: str) -> list[dict]:
    CALL_LOG.append((split,))
    if split == "test":
        raise RuntimeError("bn_experiment: WED TEST split is forbidden")
    return TWH.load_manifest(split)


def wed_root() -> Path:
    cfg = yaml.safe_load((_ROOT / "data" / "wed_dishes.yaml").read_text())
    root = Path(cfg["dataset"]["root"])
    return root if root.is_absolute() else _ROOT / root


def slot_names() -> dict[int, str]:
    raw = json.loads((_ROOT / "data" / "wed" / "index_map.json").read_text())
    return {int(k) - 1: v for k, v in raw.items() if v != "background"}


def carve_split() -> tuple[list[dict], list[dict]]:
    """Val plates carved exactly like train_weight_head.main (seed 42)."""
    rows = _guarded_load_manifest("train")
    plates = sorted({plate_key(r) for r in rows})
    random.Random(SPLIT_SEED).shuffle(plates)
    n_val = max(1, int(len(plates) * 0.10))
    val_plates = set(plates[:n_val])
    train_rows = [r for r in rows if plate_key(r) not in val_plates]
    val_rows = [r for r in rows if plate_key(r) in val_plates]
    return train_rows, val_rows


def local_eval_mae(model, loader, dev) -> float:
    """Deployable-shaped scorer (no-grad encode/ROI/slot-read).

    Same arithmetic as train_weight_head.evaluate_mae; script-local so the
    reported path never depends on in-process training state.
    """
    model.eval()
    errs: list[float] = []
    with torch.no_grad():
        for batch in loader:
            imgs = torch.stack([s["img"] for s in batch]).to(dev)
            feats = model.encoder(imgs)
            rois, weights, cls_ids = build_rois(batch, feats)
            out = model(feats, rois)
            pred = out[torch.arange(out.size(0), device=dev), cls_ids]
            for p, g in zip(pred.cpu().numpy(), weights.cpu().numpy()):
                errs.append(float(p) - float(g))
    return float(np.abs(np.array(errs)).mean()) if errs else float("nan")


def train_epoch(model, loader, dev, optimizer, scheduler,
                pin_encoder_eval: bool) -> float:
    """Mirrors train_weight_head.run_epoch (train branch: SmoothL1, AdamW,
    OneCycleLR step per batch) with one controlled difference: option A pins
    the frozen encoder to eval() so BN keeps the ImageNet statistics."""
    model.train()
    if pin_encoder_eval:
        model.encoder.eval()
    crit = nn.SmoothL1Loss()
    total, n = 0.0, 0
    for batch in loader:
        imgs = torch.stack([s["img"] for s in batch]).to(dev)
        optimizer.zero_grad()
        feats = model.encoder(imgs)
        rois, weights, cls_ids = build_rois(batch, feats)
        preds_all = model(feats, rois)
        preds = preds_all[torch.arange(preds_all.size(0), device=dev), cls_ids]
        loss = crit(preds, weights)
        loss.backward()
        optimizer.step()
        scheduler.step()
        total += float(loss.item()) * weights.size(0)
        n += weights.size(0)
    return total / max(n, 1)


def encoder_bn_state(model: WeightHead) -> dict[str, torch.Tensor]:
    return {k: v.detach().clone() for k, v in model.encoder.state_dict().items()
            if k.endswith(BN_SUFFIXES)}


def save_ckpt(path: Path, model: WeightHead, option: str, meta: dict) -> None:
    payload = {"head_mlp": model.head_mlp.state_dict(),
               "num_classes": model.num_classes,
               "roi_res": model.roi_res,
               "meta": meta}
    if option == "B":
        payload["encoder_bn"] = encoder_bn_state(model)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(payload, path)


def deployable_load(path: Path, dev, option: str) -> WeightHead:
    """The ONLY measured load path: WeightHead.load (+ BN restore for B)."""
    model = WeightHead.load(path, device=dev)
    if option == "B":
        ckpt = torch.load(path, map_location=dev, weights_only=True)
        enc_bn = ckpt.get("encoder_bn")
        if enc_bn is None:
            raise RuntimeError("option B checkpoint lacks encoder_bn buffers")
        missing, unexpected = model.encoder.load_state_dict(enc_bn, strict=False)
        assert not unexpected, f"unexpected BN keys: {unexpected}"
        bad = [k for k in missing if k.endswith(BN_SUFFIXES)]
        assert not bad, f"BN buffers unrestored: {bad}"
    return model


def train_one(option: str, seed: int, epochs: int, dev) -> tuple[Path, dict]:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    train_rows, val_rows = carve_split()
    root = wed_root()
    train_loader = DataLoader(WedPlates(train_rows, root, train=True),
                              batch_size=4, shuffle=True, collate_fn=collate,
                              num_workers=0)
    val_loader = DataLoader(WedPlates(val_rows, root, train=False),
                            batch_size=4, shuffle=False, collate_fn=collate,
                            num_workers=0)
    model = WeightHead(pretrained=True).to(dev)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = AdamW(params, lr=1e-3, weight_decay=1e-4)
    steps = epochs * len(train_loader)
    scheduler = OneCycleLR(optimizer, max_lr=1e-3, total_steps=steps,
                           pct_start=0.3)
    t0 = time.time()
    best_val, best_epoch, best_head = float("inf"), 0, None
    best_bn = None
    for epoch in range(1, epochs + 1):
        train_epoch(model, train_loader, dev, optimizer, scheduler,
                    pin_encoder_eval=(option == "A"))
        va = local_eval_mae(model, val_loader, dev)  # selection only
        if va < best_val:
            best_val, best_epoch = va, epoch
            best_head = {k: v.detach().clone()
                         for k, v in model.head_mlp.state_dict().items()}
            if option == "B":
                best_bn = encoder_bn_state(model)
        if epoch % 10 == 0 or epoch == 1:
            print(f"[{option}/seed{seed}] epoch {epoch:3d} "
                  f"[{time.time() - t0:.0f}s]", flush=True)
    model.head_mlp.load_state_dict(best_head)
    if option == "B":
        # BN buffers at the selected epoch travel with the checkpoint.
        model.encoder.load_state_dict(best_bn, strict=False)
    else:
        fresh = WeightHead(pretrained=True)
        s_cur = model.encoder.state_dict()
        s_new = fresh.encoder.state_dict()
        drift = [k for k in s_cur if k.endswith(BN_SUFFIXES)
                 and not torch.equal(s_cur[k].cpu(), s_new[k].cpu())]
        assert not drift, f"option A BN stats drifted: {drift[:3]}"
    meta = {"option": option, "seed": seed, "epochs": epochs,
            "best_epoch": best_epoch, "val_split_seed": SPLIT_SEED,
            "note": "STAGE 1A experiment checkpoint — not the deployed artifact"}
    ckpt_path = OUT_DIR / f"{option}_seed{seed}.pt"
    save_ckpt(ckpt_path, model, option, meta)
    return ckpt_path, {"train_s": round(time.time() - t0, 1)}


def evaluate_ckpt(ckpt_path: Path, option: str, rows: list[dict], dev,
                  perturb=None) -> dict:
    """Deployable-path eval on VAL rows: save -> WeightHead.load -> score."""
    root = wed_root()
    ds = WedPlates(rows, root, train=False) if perturb is None \
        else PerturbedWedPlates(rows, root, perturb)
    loader = DataLoader(ds, batch_size=4, shuffle=False, collate_fn=collate,
                        num_workers=0)
    model = deployable_load(ckpt_path, dev, option)  # reload; then score
    model.eval()
    residuals: list[float] = []
    cls_all: list[int] = []
    with torch.no_grad():
        for batch in loader:
            imgs = torch.stack([s["img"] for s in batch]).to(dev)
            feats = model.encoder(imgs)
            rois, weights, cls_ids = build_rois(batch, feats)
            out = model(feats, rois)
            pred = out[torch.arange(out.size(0), device=dev), cls_ids]
            for p, g, c in zip(pred.cpu().numpy(), weights.cpu().numpy(),
                               cls_ids.cpu().numpy()):
                residuals.append(float(p) - float(g))
                cls_all.append(int(c))
    names = slot_names()
    per_dish: dict[str, list[float]] = {}
    for r, c in zip(residuals, cls_all):
        per_dish.setdefault(names.get(c, f"slot{c}"), []).append(r)
    mae = float(np.abs(np.array(residuals)).mean()) if residuals else float("nan")
    return {"mae_g": round(mae, 3), "n": len(residuals),
            "per_dish_mae_g": {k: round(float(np.abs(np.array(v)).mean()), 2)
                               for k, v in sorted(per_dish.items())}}


class PerturbedWedPlates(WedPlates):
    """VAL views with a PIL-level perturbation; geometric ones hit mask too."""

    def __init__(self, rows, root, perturb):
        super().__init__(rows, root, train=False)
        self.perturb = perturb

    def __getitem__(self, idx: int) -> dict:
        r = self.rows[idx]
        img = Image.open(self.wed_root / r["image"]).convert("RGB")
        mask = Image.open(self.wed_root / r["mask"]).convert("L")
        img, mask = self.perturb(img, mask)
        img_t = RGB_TF(img)
        mask_arr = np.array(MASK_TF(mask).squeeze(0))
        H, W = img_t.shape[1:]
        bboxes, weights, cls_ids = [], [], []
        for d in r["dishes"]:
            cid = d["class_id"]
            vs, us = np.nonzero(mask_arr == cid)
            if vs.size == 0:
                continue
            bboxes.append([int(us.min()), int(vs.min()), int(us.max()), int(vs.max())])
            weights.append(float(d["weight_g"]))
            cls_ids.append(cid - 1)
        return {"img": img_t, "H": H, "W": W, "bboxes": bboxes,
                "weights": weights, "cls_ids": cls_ids,
                "key": plate_key(r)}


def _brightness_contrast(img, mask):
    return (TF.adjust_contrast(TF.adjust_brightness(img, 0.7), 0.7), mask)


def _blur(img, mask):
    return TF.gaussian_blur(img, kernel_size=9, sigma=[3.0, 3.0]), mask


def _perspective(img, mask):
    W, H = img.size
    # ~30 degree oblique tilt: top edge compressed, bottom flared
    start = [[0, 0], [W, 0], [W, H], [0, H]]
    end = [[W * 0.18, H * 0.12], [W * 0.82, 0], [W, H], [0, H * 0.92]]
    img = TF.perspective(img, start, end,
                         interpolation=TF.InterpolationMode.BILINEAR)
    mask = TF.perspective(mask, start, end,
                          interpolation=TF.InterpolationMode.NEAREST)
    return img, mask


def _jpeg30(img, mask):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=30)
    buf.seek(0)
    return Image.open(buf).convert("RGB"), mask


def _half_res(img, mask):
    W, H = img.size
    nw, nh = max(1, W // 2), max(1, H // 2)
    return (img.resize((nw, nh), Image.BILINEAR),
            mask.resize((nw, nh), Image.NEAREST))


STRESS = {
    "brightness_contrast_0.7": _brightness_contrast,
    "gaussian_blur_k9": _blur,
    "perspective_30deg": _perspective,
    "jpeg_q30": _jpeg30,
    "half_resolution": _half_res,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--option", choices=["A", "B"], required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--stress", action="store_true")
    args = ap.parse_args()

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _, val_rows = carve_split()
    print(f"option={args.option} seed={args.seed} epochs={args.epochs} "
          f"device={dev} val_views={len(val_rows)}", flush=True)

    ckpt_path, info = train_one(args.option, args.seed, args.epochs, dev)
    clean = evaluate_ckpt(ckpt_path, args.option, val_rows, dev)
    result = {"option": args.option, "seed": args.seed, "epochs": args.epochs,
              "clean_val": clean, **info}
    print("CLEAN", json.dumps({"option": args.option, "seed": args.seed,
                               **clean}), flush=True)

    if args.stress:
        stress = {}
        for name, fn in STRESS.items():
            r = evaluate_ckpt(ckpt_path, args.option, val_rows, dev, perturb=fn)
            stress[name] = r
            print("STRESS", name, json.dumps(r), flush=True)
        result["stress_val"] = stress

    splits = sorted({s for (s,) in CALL_LOG})
    assert splits == ["train"], f"split guard violated: {splits}"
    out = OUT_DIR / f"results_{args.option}_seed{args.seed}.json"
    out.write_text(json.dumps(result, indent=2))
    print(f"wrote {out} splits={splits}", flush=True)


if __name__ == "__main__":
    main()
