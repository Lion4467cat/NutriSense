"""P2: train the WED weight head (port of the paper's baseline recipe).

Data: data/wed_manifest.jsonl (images + labelIds masks + per-dish grams).
Model: models/weight_head.py — frozen ResNet-50, ROI-align 7x7, class-
conditional MLP head. Recipe faithful to Arora et al. ICVGIP 2025 baseline:
SmoothL1 loss, AdamW + OneCycleLR (max_lr 1e-3), random hflip, 224x224.

Methodology (keeps the test split clean):
  train      — fit head weights (90% of train plates); STAGE 1A option A: the
               encoder is frozen (no grads) and pinned to eval() during
               training so BN keeps stock ImageNet running stats — the
               deployable path (WeightHead.load + .eval()) then sees the exact
               same statistics (option B, train-mode BN, was rejected at the
               1A gate: perspective-warp MAE blew up 24.7 -> 74.7 g).
  val        — 10% of train plates, by plate (date_key+set): model selection
               + per-class residual sigma -> data/weight_head_sigma.yaml;
               MAE / residuals are always re-measured after a save->load
               round-trip through WeightHead (deployable path), never from
               the in-process training model.
  test       — final MAE report only (P5 graduation evidence); skipped
               entirely (not even loaded) with --skip-test.
  merge check— steamed-rice + sambar slots read on the UNION mask vs summed
               GT (validates the composite rice_sambar fallback); if poor,
               the pipeline keeps the geometry prior for composites.

Run:  .venv/bin/python -m tools.train_weight_head [--epochs 100] [--batch 4]
      [--seed 42] [--workers 1] [--skip-test]

Ledger 001 (branch loop-aug-run1): train-only photometric augmentation
(brightness/contrast/saturation jitter, Gaussian blur, JPEG re-compression)
plus RandomErasing cutout was added after the hflip — single-variable
change vs the entry-000 recipe; val/test paths stay unaugmented.

Feature cache (spec 002 decision 10): the encoder never trains, so its
per-view features are prepared once — one unaugmented window (val/test
semantics) and one augmented window (ledger 001 transforms, drawn from the
run's seeded RNG) per train-manifest row — and every epoch trains the head
on those prepared tensors. Augmentation is therefore applied at feature
prep time: one fixed draw per view per run, not a fresh draw every epoch.
A cache directory (default data/cache, git-ignored) holds one blob per
encoder + dataset fingerprint; the first run builds it, later runs reuse
it, `--features-cache none` keeps everything in memory. The training
stream (head init, batch shuffling, head dropout) is reseeded after
feature prep, so build / reuse / live paths are bitwise identical for a
given seed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
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

from models.weight_head import RESIZE, WeightHead  # noqa: E402

RGB_TF = transforms.Compose([
    transforms.Resize(RESIZE),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
MASK_TF = transforms.Compose([
    transforms.Resize(RESIZE, Image.NEAREST),
    transforms.PILToTensor(),
])


class RandomJpeg:
    """Train-only: PIL-frame JPEG re-compression (compression-noise axis of
    the frozen stress suite). Callable on an already-resized 224px frame so
    the encode cost is per-tile, not per-original-image."""

    def __init__(self, p: float = 0.3, q_range: tuple[int, int] = (45, 95)):
        self.p, self.q_range = p, q_range

    def __call__(self, img: Image.Image) -> Image.Image:
        if random.random() >= self.p:
            return img
        buf = io.BytesIO()
        img.save(buf, format="JPEG",
                 quality=random.randint(*self.q_range))
        buf.seek(0)
        return Image.open(buf).convert("RGB")

    def __repr__(self) -> str:
        return f"RandomJpeg(p={self.p}, q_range={self.q_range})"


# Train-only RGB pipeline (ledger 001). Photometric ops run on the PIL frame
# AFTER Resize (cheap at 224px) and BEFORE ToTensor/Normalize; RandomErasing
# runs on the normalized tensor with value=0 (= ImageNet-mean gray fill,
# matching Cutout semantics). Val/test keep the plain RGB_TF path.
RGB_TRAIN_TF = transforms.Compose([
    transforms.Resize(RESIZE),
    transforms.RandomApply([
        transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3)],
        p=0.8),
    transforms.RandomApply([transforms.GaussianBlur(kernel_size=5,
                                                    sigma=(0.5, 1.5))],
                           p=0.3),
    RandomJpeg(p=0.3, q_range=(45, 95)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    transforms.RandomErasing(p=0.25, scale=(0.02, 0.12), ratio=(0.3, 3.3),
                             value=0),
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
        img_t = RGB_TRAIN_TF(img) if self.train else RGB_TF(img)
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
    if train:
        model.encoder.eval()
    crit = nn.SmoothL1Loss()
    total, n = 0.0, 0
    for batch in loader:
        imgs = torch.stack([s["img"] for s in batch]).to(device)
        if train:
            optimizer.zero_grad()
        with torch.set_grad_enabled(train):
            feats = model.encode(imgs, no_grad=not train)
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
def evaluate_mae(model, loader, device) -> tuple[float, dict[int, list[float]],
                                                  dict[int, list[float]]]:
    """-> (overall MAE, per-class residuals pred-gt, per-class ground truth).

    The ground-truth map is kept alongside the residuals because sigma_rel
    must be normalised by the class's mean gram weight (sigma / mean_gt) —
    residuals are signed and average to the model's bias, which is ~0 and
    would collapse the divisor to the max(1.0, ...) floor."""
    model.eval()
    errs: list[float] = []
    per_class: dict[int, list[float]] = defaultdict(list)
    per_class_gt: dict[int, list[float]] = defaultdict(list)
    for batch in loader:
        imgs = torch.stack([s["img"] for s in batch]).to(device)
        feats = model.encode(imgs)
        rois, weights, cls_ids = build_rois(batch, feats)
        preds_all = model(feats, rois)
        preds = preds_all[torch.arange(preds_all.size(0), device=device), cls_ids]
        for p, g, c in zip(preds.cpu().numpy(), weights.cpu().numpy(), cls_ids.cpu().numpy()):
            errs.append(float(p - g))
            per_class[int(c)].append(float(p - g))
            per_class_gt[int(c)].append(float(g))
    mae = float(np.abs(np.array(errs)).mean()) if errs else float("nan")
    return mae, per_class, per_class_gt


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


def encoder_fingerprint(encoder: WeightHead) -> str:
    """SHA-256 over the frozen backbone's parameters — the cache must never
    outlive the exact pretrained weights it was built against."""
    h = hashlib.sha256()
    for p in encoder.encoder.parameters():
        h.update(p.detach().cpu().numpy().tobytes())
    return h.hexdigest()[:12]


def dataset_fingerprint(limit: int | None) -> str:
    """Identity of the dataset a cache blob was built for: the manifest
    bytes (protected split definition) plus the smoke --limit cap."""
    h = hashlib.sha256()
    h.update((_ROOT / "data" / "wed_manifest.jsonl").read_bytes())
    h.update(str(limit).encode())
    return h.hexdigest()[:12]


def cache_file_path(features_cache: str, encoder_id: str,
                    limit: int | None) -> Path:
    return (Path(features_cache)
            / f"wed-{encoder_id}-{dataset_fingerprint(limit)}.pt")


@torch.no_grad()
def extract_features(rows: list[dict], wed_root: Path, encoder: WeightHead,
                     device: torch.device, train: bool) -> list[dict]:
    """One item per manifest row: the frozen encoder's feature map from a
    batch=1 encode (bitwise-stable across runs) plus its ROI bundle.
    train=True draws ONE augmented window (ledger 001 transforms, from the
    run's seeded RNG); train=False is fully deterministic."""
    encoder.encoder.eval()  # STAGE 1A pin: train-mode BN would drift stats
    items: list[dict] = []
    for r in rows:
        s = WedPlates([r], wed_root, train=train)[0]
        feats = encoder.encode(s["img"].unsqueeze(0).to(device),
                               no_grad=True)[0].cpu()
        items.append({"feats": feats, "H": s["H"], "W": s["W"],
                      "bboxes": s["bboxes"], "weights": s["weights"],
                      "cls_ids": s["cls_ids"], "key": s["key"]})
    return items


def prepare_features(args: argparse.Namespace, rows: list[dict],
                     test_rows: list[dict], wed_root: Path, model: WeightHead,
                     device: torch.device) -> tuple[dict, dict]:
    """-> ({"train": aug items, "val": clean items, "test": clean items},
    cache info dict).

    "train"/"val" cover the train-manifest rows in manifest order (the val
    carve indexes into them); "test" exists only when the test split is
    loaded (--skip-test never touches it). With a cache directory the blob
    is reused when it matches encoder + dataset fingerprint, the encoder
    weight fingerprint, and covers every split this run needs; otherwise it
    is built in one piece and written once. Tensors travel through the CPU
    (fp32 copies are bitwise-exact), so reuse cannot perturb training.
    """
    t0 = time.time()

    def _build() -> dict:
        blob = {"v": 1, "encoder_id": args.encoder,
                "encoder_fp": encoder_fingerprint(model),
                "dataset_fp": dataset_fingerprint(args.limit),
                "limit": args.limit, "seed": args.seed}
        blob["val"] = extract_features(rows, wed_root, model, device,
                                       train=False)
        if test_rows:
            blob["test"] = extract_features(test_rows, wed_root, model,
                                            device, train=False)
        blob["train"] = extract_features(rows, wed_root, model, device,
                                         train=True)
        return blob

    if args.features_cache == "none":
        return _build(), {"mode": "live",
                          "build_s": round(time.time() - t0, 1)}
    p = cache_file_path(args.features_cache, args.encoder, args.limit)
    if p.is_file():
        try:
            blob = torch.load(p, map_location="cpu", weights_only=True)
        except Exception:
            blob = None
        if (isinstance(blob, dict)
                and blob.get("v") == 1
                and blob.get("encoder_id") == args.encoder
                and blob.get("encoder_fp") == encoder_fingerprint(model)
                and blob.get("dataset_fp") == dataset_fingerprint(args.limit)
                and blob.get("limit") == args.limit
                and isinstance(blob.get("train"), list)
                and isinstance(blob.get("val"), list)
                and len(blob["train"]) == len(rows)
                and len(blob["val"]) == len(rows)
                and (not test_rows or isinstance(blob.get("test"), list)
                     and len(blob["test"]) == len(test_rows))):
            return blob, {"mode": "reuse", "file": str(p)}
    blob = _build()
    p.parent.mkdir(parents=True, exist_ok=True)
    torch.save(blob, p)
    return blob, {"mode": "build", "file": str(p),
                  "build_s": round(time.time() - t0, 1)}


def _batches(items: list[dict], batch: int, shuffle: bool):
    order = (torch.randperm(len(items)).tolist() if shuffle
             else list(range(len(items))))
    for i in range(0, len(items), batch):
        yield [items[j] for j in order[i:i + batch]]


def epoch_items(model, items: list[dict], batch: int, device,
                optimizer=None, scheduler=None) -> float:
    """One head-only epoch over prepared feature items (the frozen encoder
    is never re-run). Same loss accounting as run_epoch."""
    train = optimizer is not None
    model.train(train)
    if train:
        model.encoder.eval()
    crit = nn.SmoothL1Loss()
    total, n = 0.0, 0
    for b in _batches(items, batch, shuffle=train):
        feats = torch.stack([s["feats"] for s in b]).to(device)
        rois, weights, cls_ids = build_rois(b, feats)
        with torch.set_grad_enabled(train):
            preds_all = model(feats, rois)
            preds = preds_all[torch.arange(preds_all.size(0), device=device),
                              cls_ids]
            loss = crit(preds, weights)
            if train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                if scheduler:
                    scheduler.step()
        total += float(loss.item()) * weights.size(0)
        n += weights.size(0)
    return total / max(n, 1)


@torch.no_grad()
def eval_items_mae(model, items: list[dict], batch: int, device):
    """Same contract as evaluate_mae (MAE, per-class residuals, per-class
    ground truth), over prepared feature items."""
    model.eval()
    errs: list[float] = []
    per_class: dict[int, list[float]] = defaultdict(list)
    per_class_gt: dict[int, list[float]] = defaultdict(list)
    for b in _batches(items, batch, shuffle=False):
        feats = torch.stack([s["feats"] for s in b]).to(device)
        rois, weights, cls_ids = build_rois(b, feats)
        preds_all = model(feats, rois)
        preds = preds_all[torch.arange(preds_all.size(0), device=device),
                          cls_ids]
        for p, g, c in zip(preds.cpu().numpy(), weights.cpu().numpy(),
                           cls_ids.cpu().numpy()):
            errs.append(float(p - g))
            per_class[int(c)].append(float(p - g))
            per_class_gt[int(c)].append(float(g))
    mae = float(np.abs(np.array(errs)).mean()) if errs else float("nan")
    return mae, per_class, per_class_gt


def run_training(args: argparse.Namespace) -> dict:
    """The full training pipeline; returns the report dict.

    Feature prep runs before training and consumes the augmentation RNG
    when a cache is built (or prepared live); all global seeds are then
    re-established so the training stream — head init already done, batch
    shuffling, head dropout — starts identically for build / reuse / live
    paths and every run with the same seed is bitwise reproducible.
    """
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    cfg = yaml.safe_load((_ROOT / "data" / "wed_dishes.yaml").read_text())
    wed_root = Path(cfg["dataset"]["root"])
    if not wed_root.is_absolute():
        wed_root = _ROOT / wed_root

    rows = load_manifest("train")
    if args.limit:
        rows = rows[:args.limit]
    test_rows = [] if args.skip_test else load_manifest("test")
    plates = sorted({plate_key(r) for r in rows})
    random.Random(args.seed).shuffle(plates)
    n_val = max(1, int(len(plates) * args.val_frac))
    val_plates = set(plates[:n_val])
    train_rows = [r for r in rows if plate_key(r) not in val_plates]
    val_rows = [r for r in rows if plate_key(r) in val_plates]
    print(f"train views {len(train_rows)} | val views {len(val_rows)} "
          f"({len(val_plates)} plates) | test views {len(test_rows)}", flush=True)

    model = WeightHead(encoder_id=args.encoder).to(device)
    enc_sd = model.encoder.state_dict()
    bn_names = [k for k in enc_sd
                if k.endswith(("running_mean", "running_var",
                               "num_batches_tracked"))]
    if args.encoder == "dinov2":
        # ViT-S has no BatchNorm buffers; STAGE 1B's eval() pin below instead
        # freezes the dropout/drop-path behaviour, keeping the deployable
        # forward identical to the training forward. The empty-BN guard only
        # applies to the ResNet path (test_weight_head_load pins it there).
        assert not bn_names, "dinov2 encoder unexpectedly carries BN buffers"
    else:
        assert bn_names, "no BN buffers found in encoder"
    bn_stock = {k: enc_sd[k].clone() for k in bn_names}

    cache, cache_info = prepare_features(args, rows, test_rows, wed_root,
                                         model, device)
    train_items = [it for i, it in enumerate(cache["train"])
                   if plate_key(rows[i]) not in val_plates]
    val_items = [it for i, it in enumerate(cache["val"])
                 if plate_key(rows[i]) in val_plates]
    test_items = cache.get("test", [])

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = AdamW(params, lr=args.lr, weight_decay=1e-4)
    n_batches = (len(train_items) + args.batch - 1) // args.batch
    scheduler = OneCycleLR(optimizer, max_lr=args.lr,
                           total_steps=args.epochs * n_batches, pct_start=0.3)

    best_val, best_state = float("inf"), None
    t0 = time.time()
    for epoch in range(1, args.epochs + 1):
        tr = epoch_items(model, train_items, args.batch, device, optimizer,
                         scheduler)
        va, _, _ = eval_items_mae(model, val_items, args.batch, device)
        if va < best_val:
            best_val = va
            best_state = {k: v.detach().clone() for k, v in model.head_mlp.state_dict().items()}
        if epoch % 10 == 0 or epoch == 1:
            print(f"epoch {epoch:3d}  train_loss {tr:.3f}  val_mae {va:.2f}g "
                  f"(best {best_val:.2f})  [{time.time() - t0:.0f}s]", flush=True)

    model.head_mlp.load_state_dict(best_state)
    enc_now = model.encoder.state_dict()
    drifted = [k for k in bn_names if not torch.equal(bn_stock[k], enc_now[k])]
    assert not drifted, (f"encoder BN statistics changed during training "
                         f"({len(drifted)} of {len(bn_names)} buffers): "
                         f"{drifted[:3]}")

    from datetime import date
    meta = {"dataset": "WED (ICVGIP 2025)", "recipe": "baseline rgb/no-attn/geom-none",
            "bn_mode": "frozen_encoder_eval", "epochs": args.epochs,
            "encoder": args.encoder,
            "seed": args.seed, "trained": date.today().isoformat(),
            "val_mae_in_process_g": round(best_val, 2),
            "paper_baseline_mae_g": 14.51,
            "feature_cache": cache_info}
    model.save(args.out, meta=meta)

    deployable = WeightHead.load(args.out, device=device)
    deploy_mae, per_class_val, gt_val = eval_items_mae(deployable, val_items,
                                                       args.batch, device)
    meta["val_mae_g"] = round(deploy_mae, 2)

    id_map = json.loads((_ROOT / "data" / "wed" / "index_map.json").read_text())
    id2name = {int(k) - 1: v for k, v in id_map.items() if v != "background"}
    sigma = {id2name[c]: round(float(np.std(v)), 2)
             for c, v in sorted(per_class_val.items()) if len(v) >= 3}
    rel = {name: round(sigma[name] / max(1.0, float(np.mean(gt_val[c]))), 4)
           for c, name in id2name.items() if name in sigma}

    report = {"meta": meta, "val_mae_in_process_g": round(best_val, 2),
              "val_mae_deployable_g": round(deploy_mae, 2)}
    if not args.skip_test:
        test_mae, per_class_test, _ = eval_items_mae(deployable, test_items,
                                                     args.batch, device)
        meta["test_mae_g"] = round(test_mae, 2)
        report["test_mae_g"] = test_mae
        report["test_per_class_mae"] = {
            id2name[c]: round(float(np.abs(np.array(v)).mean()), 2)
            for c, v in sorted(per_class_test.items())}
        report["merge_check"] = merge_check(deployable, test_rows, wed_root, device)
    model.save(args.out, meta=meta)

    sigma_doc = {
        "_meta": meta,
        "sigma_g": sigma,
        "sigma_rel": rel,
        "note": "per-class residual std on the carved val split (train plates), "
                "measured on the reloaded checkpoint (deployable path, "
                "WeightHead.load); sigma_rel = sigma_g / mean GT grams on the "
                "same split; feeds MC lognormal grams sigma in engine/mc.py",
    }
    Path(args.sigma_out).write_text(yaml.safe_dump(sigma_doc, sort_keys=False))

    out = Path(args.report_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"wrote {args.out}, {args.sigma_out}, {out}")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--encoder", default="resnet50",
                    choices=("resnet50", "dinov2"),
                    help="frozen backbone (ledger 002 lever b); encoder_id "
                         "is recorded in the checkpoint for load()")
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--val-frac", type=float, default=0.10)
    ap.add_argument("--workers", type=int, default=2,
                    help="legacy dataloader knob (feature prep is "
                         "single-threaded; kept for command-line compat)")
    ap.add_argument("--limit", type=int, default=None,
                    help="smoke runs: cap train-manifest rows in manifest "
                         "order (part of the cache key)")
    ap.add_argument("--features-cache", dest="features_cache",
                    default=str(_ROOT / "data" / "cache"),
                    help="directory for the git-ignored encoder feature "
                         "cache (default data/cache; 'none' prepares "
                         "features in memory every run)")
    ap.add_argument("--skip-test", action="store_true",
                    help="never load or evaluate the WED test split "
                         "(no test MAE, no merge_check) — rebuild the "
                         "deployable artifact from train+val only")
    ap.add_argument("--out", default=str(_ROOT / "data" / "weight_head.pt"))
    ap.add_argument("--sigma-out", default=str(_ROOT / "data" / "weight_head_sigma.yaml"))
    ap.add_argument("--report-out", default=str(_ROOT / "data" / "reports" / "weight_head_train.json"))
    args = ap.parse_args()
    run_training(args)


if __name__ == "__main__":
    main()
