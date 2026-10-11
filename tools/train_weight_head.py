"""P2: train the WED weight head (port of the paper's baseline recipe).

Data: data/wed_manifest.jsonl (images + labelIds masks + per-dish grams).
Model: models/weight_head.py — frozen ResNet-50, ROI-align 7x7, class-
conditional MLP head. Recipe faithful to Arora et al. ICVGIP 2025 baseline:
SmoothL1 loss, AdamW + OneCycleLR (max_lr 1e-3), random hflip, 224x224.

Methodology (keeps the test split clean):
  train      — fit head weights (90% of train plates)
  val        — 10% of train plates, by plate (date_key+set): model selection
               + per-class residual sigma -> data/weight_head_sigma.yaml
  test       — final MAE report only (P5 graduation evidence)
  merge check— steamed-rice + sambar slots read on the UNION mask vs summed
               GT (validates the composite rice_sambar fallback); if poor,
               the pipeline keeps the geometry prior for composites.

Run:  .venv/bin/python -m tools.train_weight_head [--epochs 100] [--batch 4]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml
from PIL import Image
from torch.optim import AdamW
from torch.optim.lr_scheduler import OneCycleLR
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.transforms import functional as TF

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from models.weight_head import RESIZE, WED_NUM_CLASSES, WeightHead  # noqa: E402

RGB_TF = transforms.Compose([
    transforms.Resize(RESIZE),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
MASK_TF = transforms.Compose([
    transforms.Resize(RESIZE, Image.NEAREST),
    transforms.PILToTensor(),
])


def load_manifest(split: str) -> list[dict]:
    rows = []
    with (_ROOT / "data" / "wed_manifest.jsonl").open() as fh:
        for line in fh:
            r = json.loads(line)
            if r["split"] == split:
                rows.append(r)
    return rows


def plate_key(row: dict) -> str:
    return f"{row['date_key']}_{row['set']}"


class WedPlates(Dataset):
    """One item = one multi-view image with all its dish ROIs (like the paper)."""

    def __init__(self, rows: list[dict], wed_root: Path, train: bool):
        self.rows, self.wed_root, self.train = rows, wed_root, train

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict:
        r = self.rows[idx]
        img = Image.open(self.wed_root / r["image"]).convert("RGB")
        mask = Image.open(self.wed_root / r["mask"]).convert("L")
        if self.train and random.random() < 0.5:
            img = TF.hflip(img)
            mask = TF.hflip(mask)
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
            cls_ids.append(cid - 1)  # 1..41 -> 0..40
        return {"img": img_t, "H": H, "W": W, "bboxes": bboxes,
                "weights": weights, "cls_ids": cls_ids,
                "key": plate_key(r)}


def collate(batch: list[dict]) -> list[dict]:
    return batch


def build_rois(batch: list[dict], feats: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """rois (K,5) in feature coords; weights (K,); cls_ids (K,)."""
    rois, weights, cls_ids = [], [], []
    B, _, fh, fw = feats.shape
    for i, s in enumerate(batch):
        H, W = s["H"], s["W"]
        for (x1, y1, x2, y2), w, c in zip(s["bboxes"], s["weights"], s["cls_ids"]):
            rois.append([i, x1 / W * fw, y1 / H * fh, x2 / W * fw, y2 / H * fh])
            weights.append(w)
            cls_ids.append(c)
    return (torch.tensor(rois, dtype=torch.float32, device=feats.device),
            torch.tensor(weights, dtype=torch.float32, device=feats.device),
            torch.tensor(cls_ids, dtype=torch.long, device=feats.device))


def run_epoch(model, loader, device, optimizer=None, scheduler=None):
    train = optimizer is not None
    model.train(train)
    crit = nn.SmoothL1Loss()
    total, n = 0.0, 0
    for batch in loader:
        imgs = torch.stack([s["img"] for s in batch]).to(device)
        if train:
            optimizer.zero_grad()
        with torch.set_grad_enabled(train):
            feats = model.encode(imgs) if not train else model.encoder(imgs)
            rois, weights, cls_ids = build_rois(batch, feats)
            preds_all = model(feats, rois)
            preds = preds_all[torch.arange(preds_all.size(0), device=device), cls_ids]
            loss = crit(preds, weights)
            if train:
                loss.backward()
                optimizer.step()
                if scheduler:
                    scheduler.step()
        total += float(loss.item()) * weights.size(0)
        n += weights.size(0)
    return total / max(n, 1)


@torch.no_grad()
def evaluate_mae(model, loader, device) -> tuple[float, dict[int, list[float]]]:
    model.eval()
    errs: list[float] = []
    per_class: dict[int, list[float]] = defaultdict(list)
    for batch in loader:
        imgs = torch.stack([s["img"] for s in batch]).to(device)
        feats = model.encode(imgs)
        rois, weights, cls_ids = build_rois(batch, feats)
        preds_all = model(feats, rois)
        preds = preds_all[torch.arange(preds_all.size(0), device=device), cls_ids]
        for p, g, c in zip(preds.cpu().numpy(), weights.cpu().numpy(), cls_ids.cpu().numpy()):
            errs.append(float(p - g))
            per_class[int(c)].append(float(p - g))
    mae = float(np.abs(np.array(errs)).mean()) if errs else float("nan")
    return mae, per_class


@torch.no_grad()
def merge_check(model, test_rows: list[dict], wed_root: Path, device,
                slots=(33, 32)) -> dict:
    """steamed-rice (id34 -> slot33) + sambar (id33 -> slot32) on the union
    mask vs summed GT. Reports merge MAE vs the per-ROI upper reference."""
    from torchvision import transforms as T
    model.eval()
    merge_errs, roi_sum_errs, n = [], [], 0
    for r in test_rows:
        names = {d["name"]: d for d in r["dishes"]}
        if "steamed-rice" not in names or "sambar" not in names:
            continue
        n += 1
        img = Image.open(wed_root / r["image"]).convert("RGB")
        mask = np.array(Image.open(wed_root / r["mask"]).convert("L"))
        union = np.isin(mask, [33, 34])  # sambar + steamed-rice labels
        gt_sum = names["steamed-rice"]["weight_g"] + names["sambar"]["weight_g"]
        rgb = np.array(img)[:, :, ::-1]
        try:
            out = model.predict(rgb, union, slot_ids=list(slots), device=device)
            merge_errs.append(out["grams"] - gt_sum)
        except ValueError:
            continue
        # per-ROI reference (each pure mask, its own slot)
        est_roi = 0.0
        for label, slot in ((34, 33), (33, 32)):
            roi = mask == label
            if int(roi.sum()) < 64:
                est_roi = None
                break
            est_roi += model.predict(rgb, roi, slot_ids=[slot], device=device)["grams"]
        if est_roi is not None:
            roi_sum_errs.append(est_roi - gt_sum)
    def _m(e):
        return {"n": len(e), "mae": float(np.abs(np.array(e)).mean())} if e else {"n": 0}
    return {"plates": n, "merged_union_mae": _m(merge_errs),
            "per_roi_sum_mae": _m(roi_sum_errs)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--val-frac", type=float, default=0.10)
    ap.add_argument("--workers", type=int, default=2,
                    help="dataloader workers (keep low on small-RAM boxes)")
    ap.add_argument("--out", default=str(_ROOT / "data" / "weight_head.pt"))
    ap.add_argument("--sigma-out", default=str(_ROOT / "data" / "weight_head_sigma.yaml"))
    ap.add_argument("--report-out", default=str(_ROOT / "data" / "reports" / "weight_head_train.json"))
    args = ap.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    cfg = yaml.safe_load((_ROOT / "data" / "wed_dishes.yaml").read_text())
    wed_root = Path(cfg["dataset"]["root"])
    if not wed_root.is_absolute():
        wed_root = _ROOT / wed_root

    rows = load_manifest("train")
    test_rows = load_manifest("test")
    plates = sorted({plate_key(r) for r in rows})
    random.Random(args.seed).shuffle(plates)
    n_val = max(1, int(len(plates) * args.val_frac))
    val_plates = set(plates[:n_val])
    train_rows = [r for r in rows if plate_key(r) not in val_plates]
    val_rows = [r for r in rows if plate_key(r) in val_plates]
    print(f"train views {len(train_rows)} | val views {len(val_rows)} "
          f"({len(val_plates)} plates) | test views {len(test_rows)}", flush=True)

    train_loader = DataLoader(WedPlates(train_rows, wed_root, train=True),
                              batch_size=args.batch, shuffle=True,
                              collate_fn=collate, num_workers=args.workers)
    val_loader = DataLoader(WedPlates(val_rows, wed_root, train=False),
                            batch_size=args.batch, shuffle=False,
                            collate_fn=collate, num_workers=args.workers)
    test_loader = DataLoader(WedPlates(test_rows, wed_root, train=False),
                             batch_size=args.batch, shuffle=False,
                             collate_fn=collate, num_workers=args.workers)

    model = WeightHead().to(device)
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = AdamW(params, lr=args.lr, weight_decay=1e-4)
    steps = args.epochs * len(train_loader)
    scheduler = OneCycleLR(optimizer, max_lr=args.lr, total_steps=steps,
                           pct_start=0.3)

    best_val, best_state = float("inf"), None
    t0 = time.time()
    for epoch in range(1, args.epochs + 1):
        tr = run_epoch(model, train_loader, device, optimizer, scheduler)
        va, _ = evaluate_mae(model, val_loader, device)
        if va < best_val:
            best_val = va
            best_state = {k: v.detach().clone() for k, v in model.head_mlp.state_dict().items()}
        if epoch % 10 == 0 or epoch == 1:
            print(f"epoch {epoch:3d}  train_loss {tr:.3f}  val_mae {va:.2f}g "
                  f"(best {best_val:.2f})  [{time.time() - t0:.0f}s]", flush=True)

    model.head_mlp.load_state_dict(best_state)
    _, per_class_val = evaluate_mae(model, val_loader, device)
    test_mae, per_class_test = evaluate_mae(model, test_loader, device)

    id_map = json.loads((_ROOT / "data" / "wed" / "index_map.json").read_text())
    id2name = {int(k) - 1: v for k, v in id_map.items() if v != "background"}
    sigma = {id2name[c]: round(float(np.std(v)), 2)
             for c, v in sorted(per_class_val.items()) if len(v) >= 3}
    rel = {name: round(sigma[name] / max(1.0, float(np.mean(per_class_val[c]))), 4)
           for c, name in id2name.items() if name in sigma}

    from datetime import date
    meta = {"dataset": "WED (ICVGIP 2025)", "recipe": "baseline rgb/no-attn/geom-none",
            "val_mae_g": round(best_val, 2), "test_mae_g": round(test_mae, 2),
            "epochs": args.epochs, "seed": args.seed,
            "trained": date.today().isoformat(), "paper_baseline_mae_g": 14.51}
    model.save(args.out, meta=meta)

    sigma_doc = {
        "_meta": meta,
        "sigma_g": sigma,
        "sigma_rel": rel,
        "note": "per-class residual std on the carved val split (train plates); "
                "feeds MC lognormal grams sigma in engine/mc.py",
    }
    Path(args.sigma_out).write_text(yaml.safe_dump(sigma_doc, sort_keys=False))

    merge = merge_check(model, test_rows, wed_root, device)
    report = {"meta": meta, "test_mae_g": test_mae,
              "test_per_class_mae": {id2name[c]: round(float(np.abs(np.array(v)).mean()), 2)
                                     for c, v in sorted(per_class_test.items())},
              "merge_check": merge}
    out = Path(args.report_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"meta": meta, "test_mae_g": test_mae, "merge_check": merge},
                     indent=2))
    print(f"wrote {args.out}, {args.sigma_out}, {out}")


if __name__ == "__main__":
    main()
