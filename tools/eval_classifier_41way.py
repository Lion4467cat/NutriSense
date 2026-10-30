"""Ledger 009 — 41-way recognizer: spatial MLP + hybrid vs gallery argmax.

Pre-registered experiment (docs/ledger/009-recognizer-round2.md, extends
docs/ledger/008-recognizer-41way.md): on the held-out DEV-plate ROI crops
(the seed-42 val carve, same arithmetic as tools.run_eval.dev_rows),
compare against the deployed gallery argmax measured on the SAME crops
(ledger 008 baseline 0.8103):

  linear8 — entry-008 candidate repeated for continuity (7×7 mean pool,
            384-d, linear, no augmentation),
  mlp     — max+mean pool over the full ROI grid (768-d concat), 2-layer
            MLP with dropout 0.2, feature-level horizontal-flip
            augmentation (flip the patch grid, mirror the boxes),
  hybrid  — mean of the MLP's softmax and the gallery's per-class
            top-3-mean scores (softmaxed, tau 0.05 as classify_dish).

Reports per-variant accuracy, the PROPERLY PAIRED plate-bootstrap Δacc 95%
CI vs the gallery (both accuracies recomputed on every replicate), per-class
tables for the best variant, top confusions, the gallery/DEV-plate overlap
count. Diagnostic only: no serving change in this entry.

Run: .venv/bin/python -m tools.eval_classifier_41way [--skip-linear8]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
import torch

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from torch.nn import functional as F  # noqa: E402
from torchvision.ops import roi_align  # noqa: E402

from models.food_classifier import MODEL_ID as SIGLIP_ID  # noqa: E402
from models.weight_head import ROI_RES  # noqa: E402
from tools.train_weight_head import (  # noqa: E402
    cache_file_path, load_manifest, plate_key)

GALLERY_PATH = _ROOT / "data" / "gallery.npz"
CACHE_DIR = _ROOT / "data" / "cache"
REPORT_PATH = _ROOT / "data" / "reports" / "classifier_41way_dev.json"
SPLIT_SEED = 42                   # val carve seed — fixed, never user-tunable
VAL_FRAC = 0.10
SELECT_FRAC = 0.10                # selection carve inside the train plates
BOOTSTRAP_REPS = 2000
EPOCHS = 400
N_CLASSES = 41
ENCODER = "dinov2"
FEATURES_CACHE_RECIPE = "strong"  # the blob that exists for dinov2
GRID_ROT = 16                     # DINOv2-S/14 @ 224: 16×16 patch grid


# ------------------------------------------------------------- carve maths --
def _carve_plates(rows: list[dict], seed: int, frac: float) -> set[str]:
    plates = sorted({plate_key(r) for r in rows})
    random.Random(seed).shuffle(plates)
    return set(plates[:max(1, int(len(plates) * frac))])


def dev_plates(rows: list[dict]) -> set[str]:
    """Identical arithmetic to tools.run_eval.dev_rows (seed 42)."""
    return _carve_plates(rows, SPLIT_SEED, VAL_FRAC)


# -------------------------------------------------------- pooled features --
@torch.no_grad()
def collect_split(items: list[dict]) -> dict:
    """Raw per-view patch grids + ROI bundles for one set of manifest rows."""
    views: list[tuple[torch.Tensor, list[list[int]], int, int]] = []
    labels: list[int] = []
    plates: list[str] = []
    for it in items:
        if not it["bboxes"]:
            continue
        f = it["feats"].detach().clone().float()          # (C, 16, 16)
        views.append((f, [list(b) for b in it["bboxes"]],
                      it["H"], it["W"]))
        labels.extend(int(c) for c in it["cls_ids"])
        plates.extend([it["key"]] * len(it["bboxes"]))
    return {"views": views, "labels": torch.tensor(labels, dtype=torch.long),
            "plates": plates}


def _pooled(views: list, flipped: bool = False) -> dict[str, torch.Tensor]:
    """Per-ROI pools over the full patch grid.

    mm   max+mean concat -> (K, 2C); plain -> (K, C) overall ROI mean
    (the 7×7-mean value of ledger 008, evaluated on the same grid).
    The flip axis mirrors the patch grid width AND the box x-extent, the
    exact feature-space image of the WED hflip viewed as data augmentation.
    """
    if not views:
        raise ValueError("no ROI-bearing views in this split")
    C = views[0][0].shape[0]
    plain, mm = [], []
    for f, boxes, h, w in views:
        fv = f.flip(-1) if flipped else f
        for (x1, y1, x2, y2) in boxes:
            xx1, xx2 = ((w - x2, w - x1) if flipped else (x1, x2))
            gx1, gx2 = xx1 / w * GRID_ROT, xx2 / w * GRID_ROT
            gy1, gy2 = y1 / h * GRID_ROT, y2 / h * GRID_ROT
            if gx2 - gx1 < 1e-6 or gy2 - gy1 < 1e-6:
                gx2, gy2 = gx1 + 1e-3, gy1 + 1e-3
            roi = torch.tensor([[0.0, gx1, gy1, gx2, gy2]],
                               dtype=torch.float32)
            sample = roi_align(fv.unsqueeze(0), roi,
                               output_size=(ROI_RES, ROI_RES))
            maxp = F.adaptive_max_pool2d(sample, 1).view(-1)
            meanp = F.adaptive_avg_pool2d(sample, 1).view(-1)
            mm.append(torch.cat([maxp, meanp]))
            if not flipped:
                plain.append(meanp)
    out_mm = torch.stack(mm)
    out = {"mm": out_mm}
    if not flipped:
        out["plain"] = torch.stack(plain)
    return out


class PooledDataset(NamedTuple):
    """Per-ROI pooled features for one split (see _pooled for the axes)."""
    mm_tr: torch.Tensor      # clean + hflip-augmented rows
    plain: torch.Tensor      # clean 7×7-mean vectors (entry-008 recipe)
    mm_clean: torch.Tensor   # clean max+mean vectors
    labels: torch.Tensor
    labels_aug: torch.Tensor # labels aligned with mm_tr
    plates: list[str]


def pooled_dataset(split: dict) -> PooledDataset:
    """plain + mm tensors; the training callers append the flip copy."""
    pw = _pooled(split["views"], flipped=False)
    pf = _pooled(split["views"], flipped=True)
    return PooledDataset(
        mm_tr=torch.cat([pw["mm"], pf["mm"]]),
        plain=pw["plain"],
        mm_clean=pw["mm"],
        labels=split["labels"],
        labels_aug=torch.cat([split["labels"], split["labels"]]),
        plates=split["plates"])


# ------------------------------------------------------------- candidates ----
def _class_weights(y: torch.Tensor) -> torch.Tensor:
    n = torch.bincount(y, minlength=N_CLASSES).float()
    cw = (n.sum() / n.clamp(min=1)).sqrt()
    return cw / cw.mean()


def train_linear(x_tr: torch.Tensor, y_tr: torch.Tensor,
                 x_sel: torch.Tensor, y_sel: torch.Tensor,
                 device: torch.device) -> torch.Tensor:
    torch.manual_seed(SPLIT_SEED)
    w = torch.zeros(N_CLASSES, x_tr.shape[1], device=device,
                    requires_grad=True)
    b = torch.zeros(N_CLASSES, device=device, requires_grad=True)
    opt = torch.optim.AdamW([w, b], lr=1e-3)
    cw = _class_weights(y_tr).to(device)
    best, best_w = -1.0, w.detach().clone()
    for _ in range(EPOCHS):
        opt.zero_grad()
        F.cross_entropy(x_tr @ w.T + b, y_tr, weight=cw).backward()
        opt.step()
        with torch.no_grad():
            acc = ((x_sel @ w.T + b).argmax(1) == y_sel).float().mean().item()
            if acc > best:
                best, best_w = acc, w.detach().clone()
    return best_w


class MlpHead(torch.nn.Module):
    def __init__(self, c_in: int, hidden: int = 512):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Linear(c_in, hidden), torch.nn.ReLU(inplace=True),
            torch.nn.Dropout(0.2), torch.nn.Linear(hidden, N_CLASSES))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def train_mlp(x_tr: torch.Tensor, y_tr: torch.Tensor,
              x_sel: torch.Tensor, y_sel: torch.Tensor,
              device: torch.device) -> MlpHead:
    torch.manual_seed(SPLIT_SEED)
    model = MlpHead(x_tr.shape[1]).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    cw = _class_weights(y_tr).to(device)
    best, best_state = -1.0, None
    for _ in range(EPOCHS):
        model.train()
        opt.zero_grad()
        F.cross_entropy(model(x_tr), y_tr, weight=cw).backward()
        opt.step()
        model.eval()
        with torch.no_grad():
            acc = (model(x_sel).argmax(1) == y_sel).float().mean().item()
        if acc > best:
            best = acc
            best_state = {k: v.detach().clone()
                          for k, v in model.state_dict().items()}
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    return model


# --------------------------------------------------------------- baseline ----
@torch.no_grad()
def gallery_scores(crops_bgr: list[np.ndarray]) -> torch.Tensor:
    """Per-crop gallery scores over the 41 WED classes (the recognizer's own
    top-3-mean cosine, restricted to class-name labels), softmaxed per crop
    with classify_dish's tau=0.05 — units used by the hybrid fusion."""
    gallery = np.load(GALLERY_PATH, allow_pickle=True)
    E = torch.tensor(gallery["emb"], dtype=torch.float32)
    by_cls: dict[str, list[int]] = defaultdict(list)
    for i, lab in enumerate(map(str, gallery["labels"])):
        by_cls.setdefault(lab, []).append(i)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    from transformers import AutoProcessor, AutoModel
    proc = AutoProcessor.from_pretrained(SIGLIP_ID)
    model = AutoModel.from_pretrained(SIGLIP_ID).to(dev).eval()
    names = json.loads((_ROOT / "data" / "wed" / "index_map.json").read_text())
    cls_name = [names[str(i + 1)] for i in range(N_CLASSES)]
    rows_out = []
    for crop in crops_bgr:
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        inp = proc(images=rgb, return_tensors="pt").to(dev)
        e = model.get_image_features(**inp)
        if hasattr(e, "pooler_output"):
            e = e.pooler_output
        e = (e / e.norm(dim=-1, keepdim=True))[0].cpu().float()
        sims = E @ e
        scores = torch.zeros(N_CLASSES)
        for ci, lab in enumerate(cls_name):
            if lab in by_cls:
                vals = sims[by_cls[lab]]
                k = min(3, len(vals))
                scores[ci] = float(np.sort(vals.numpy())[-k:].mean())
        rows_out.append(F.softmax(scores / 0.05, dim=0))
    return torch.stack(rows_out)


def load_eval_crops(row: dict, wed_root: Path) -> list[np.ndarray]:
    img = cv2.imread(str(wed_root / row["image"]))
    if img is None:
        raise FileNotFoundError(f"wed image failed to decode: {row['image']}")
    mask = cv2.imread(str(wed_root / row["mask"]), cv2.IMREAD_GRAYSCALE)
    if mask is None:
        raise FileNotFoundError(f"wed mask failed to decode: {row['mask']}")
    crops = []
    for d in row["dishes"]:
        cid = int(d["class_id"])
        vs, us = np.nonzero(mask == cid)
        if vs.size:
            crops.append(np.ascontiguousarray(
                img[vs.min():vs.max() + 1, us.min():us.max() + 1]))
    return crops


# ------------------------------------------------------------------ stats ----
def paired_delta(pred: torch.Tensor, base: torch.Tensor,
                 truth: torch.Tensor, plates: list[str]) -> dict:
    """Paired plate bootstrap of Δacc (cand − base): both accuracies are
    recomputed on every replicate, so the CI is genuinely paired."""
    plate_list = sorted(set(plates))
    per_plate: dict[str, list[int]] = defaultdict(list)
    for i, p in enumerate(plates):
        per_plate[p].append(i)
    pred_np, base_np, truth_np = pred.cpu().numpy(), base.cpu().numpy(), \
        truth.cpu().numpy()
    rng = random.Random(SPLIT_SEED)
    deltas = []
    for _ in range(BOOTSTRAP_REPS):
        pick = [rng.choice(plate_list) for _ in plate_list]
        idx = [i for p in pick for i in per_plate[p]]
        pc = float(np.mean(pred_np[idx] == truth_np[idx]))
        pb = float(np.mean(base_np[idx] == truth_np[idx]))
        deltas.append(pc - pb)
    return {"delta_mean": float(np.mean(deltas)),
            "delta_ci95": [float(x) for x in np.percentile(deltas, [2.5, 97.5])],
            "reps": BOOTSTRAP_REPS, "seed": SPLIT_SEED}


def per_class_table(pred: torch.Tensor, truth: torch.Tensor,
                    cls_name: list[str]) -> dict:
    pred_np, truth_np = pred.cpu().numpy(), truth.cpu().numpy()
    out = {}
    for c in np.unique(truth_np):
        m = truth_np == c
        out[cls_name[int(c)]] = {"n": int(m.sum()),
                                 "acc": round(float((pred_np[m] ==
                                                     truth_np[m]).mean()), 3)}
    return out


def top_confusions(pred: torch.Tensor, truth: torch.Tensor,
                   cls_name: list[str]) -> list[dict]:
    counts: dict[str, int] = defaultdict(int)
    for p, g in zip(pred.cpu().numpy(), truth.cpu().numpy()):
        if int(p) != int(g):
            counts[f"{cls_name[int(g)]}->{cls_name[int(p)]}"] += 1
    return [{"pair": k, "n": v}
            for k, v in sorted(counts.items(), key=lambda kv: -kv[1])[:10]]


def contamination(rows_all: list[dict], dev: set[str]) -> dict:
    gallery = np.load(GALLERY_PATH, allow_pickle=True)
    gal_src = {str(s) for s in gallery["sources"]}
    imgs = sorted({r["image"] for r in rows_all if plate_key(r) in dev})
    return {"dev_plate_images_in_gallery_sources":
            sum(1 for p in imgs if p in gal_src),
            "dev_plate_images": len(imgs)}


# ------------------------------------------------------------------ main ----
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-linear8", action="store_true",
                    help="skip the entry-008 continuity recipe")
    args = ap.parse_args(argv)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rows_all = load_manifest("train")
    dev = dev_plates(rows_all)
    sel = _carve_plates([r for r in rows_all if plate_key(r) not in dev],
                        SPLIT_SEED, SELECT_FRAC)

    cache_p = cache_file_path(str(CACHE_DIR), ENCODER,
                              FEATURES_CACHE_RECIPE, None)
    if not cache_p.is_file():
        matches = sorted(CACHE_DIR.glob(
            f"wed-{ENCODER}-{FEATURES_CACHE_RECIPE}-*.pt"))
        if not matches:
            raise FileNotFoundError(
                f"no {ENCODER}/{FEATURES_CACHE_RECIPE} feature blob under "
                f"{CACHE_DIR} — build it via a train_weight_head run")
        cache_p = matches[0]
    print(f"feature blob: {cache_p.name}", flush=True)
    blob = torch.load(cache_p, map_location="cpu", weights_only=True)
    tr = pooled_dataset(collect_split(
        [it for it in blob["train"]
         if it["key"] not in dev and it["key"] not in sel]))
    se = pooled_dataset(collect_split(
        [it for it in blob["train"] if it["key"] in sel]))
    de = pooled_dataset(collect_split(
        [it for it in blob["val"] if it["key"] in dev]))
    names = json.loads((_ROOT / "data" / "wed" / "index_map.json").read_text())
    cls_name = [names[str(i + 1)] for i in range(N_CLASSES)]

    variants: dict[str, dict] = {}

    if not args.skip_linear8:
        W = train_linear(tr.plain.to(device),
                         tr.labels.to(device),
                         se.plain.to(device),
                         se.labels.to(device), device)
        pred = (de.plain.to(device) @ W.T).argmax(1)
        variants["linear8"] = {"acc": float((pred == de.labels.to(device))
                                            .float().mean()),
                               "pred": pred.cpu()}

    mlp = train_mlp(tr.mm_tr.to(device),
                    tr.labels_aug.to(device),
                    se.mm_clean.to(device),
                    se.labels.to(device), device)
    mlp_pred = mlp(de.mm_clean.to(device)).argmax(1).cpu()
    variants["mlp"] = {"acc": float((mlp_pred == de.labels).float().mean()),
                       "pred": mlp_pred}

    # --- baseline gallery scores on the same crops ---------------------------
    wed_root = _ROOT / "data" / "wed"
    rows = [r for r in rows_all if plate_key(r) in dev]
    crops: list[np.ndarray] = []
    for row in rows:
        crops.extend(load_eval_crops(row, wed_root))
    assert len(crops) == len(de.labels), (
        f"crop count (masked gt) {len(crops)} != feature ROI count "
        f"{len(de.labels)} — manifest/mask drift")
    print(f"embedding {len(crops)} DEV crops with SigLIP...", flush=True)
    g_prob = gallery_scores(crops)
    g_pred = g_prob.argmax(1)
    variants["gallery"] = {"acc": float((g_pred == de.labels)
                                        .float().mean()), "pred": g_pred}

    fused = 0.5 * F.softmax(mlp(de.mm_clean.to(device)), 1).cpu() \
        + 0.5 * g_prob
    f_pred = fused.argmax(1)
    variants["hybrid"] = {"acc": float((f_pred == de.labels)
                                       .float().mean()), "pred": f_pred}

    boots = {name: paired_delta(v["pred"], g_pred, de.labels, de.plates)
             for name, v in variants.items() if name != "gallery"}
    best_name = max((k for k in variants if k != "gallery"),
                    key=lambda k: variants[k]["acc"])

    report = {
        "ledger": "009",
        "date": datetime.now(UTC).isoformat(),
        "n_crops": int(len(de.labels)),
        "n_dev_plates": len(set(de.plates)),
        "variants": {k: {"acc": v["acc"]} for k, v in variants.items()},
        "baseline_gallery": {"acc": variants["gallery"]["acc"],
                             "method": "siglip_gallery_argmax_41",
                             "model": SIGLIP_ID},
        "paired_delta_vs_gallery": boots,
        "best_variant": best_name,
        "gallery_contamination": contamination(rows_all, dev),
        "per_class_best": per_class_table(variants[best_name]["pred"],
                                          de.labels, cls_name),
        "per_class_gallery": per_class_table(g_pred, de.labels, cls_name),
        "top_confusions_best": top_confusions(variants[best_name]["pred"],
                                              de.labels, cls_name),
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    summary = {k: report[k] for k in ("n_crops", "variants",
                                      "paired_delta_vs_gallery",
                                      "best_variant",
                                      "gallery_contamination")}
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
