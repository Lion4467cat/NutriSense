"""07b: ingredient-conditional teacher head on Nutrition5k (ticket 07b).

Same frozen-encoder + ROI + MLP family as the WED weight head
(models/weight_head.py) but conditionally emitting **per-ingredient grams**
(K slots from data/n5k_ingredient_table.yaml) instead of 41 dish slots.
Supervision: Nutrition5k per-ingredient grams, sqrt-transformed
(`target = sqrt(g)`) to tame the long tail; loss = SmoothL1 over present
slots only. ROI = the full overhead frame (the plate fills the image).

Feature-cache pattern per spec 002 decision 10: the frozen encoder runs
ONCE per run; augmentation that acts on feature maps (hflip = spatial flip
of the feature grid) applies at feature level, so every epoch is a head-only
pass. Head init/shuffling are reseeded after feature prep.

Evaluation is honest by construction:
  - in-domain: test-split per-ingredient MAE in GRAMS, reported against the
    Nutrition5k paper's 29.4 g (13.7%) mass-regression reference;
  - leave-ingredient-out (--lio <name>): retrain with every dish
    containing that ingredient dropped from train, then measure that
    ingredient's grams MAE on the untouched val+test dishes that contain
    it — the "transfer is real, not memorised" check. Pre-registered gates
    live in docs/ledger/012 before the runs.

No N5k geometry exists in this repo (no card, no device depth), so this is
the F1-style feature teacher; the F2 residual (geometry-floor) fusion is a
WED-side follow-up and is NOT claimed here.

Run:  .venv/bin/python -m tools.train_ingredient_head [--epochs 60]
      [--batch 8] [--encoder dinov2] [--lio "white rice"] [--skip-test]
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml
from PIL import Image
from torchvision.transforms import functional as TF

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from models.weight_head import RESIZE, WeightHead  # noqa: E402

TABLE_PATH = Path("data") / "n5k_ingredient_table.yaml"
IMAGERY_DIR = Path("data") / "nutrition5k" / "imagery" / "realsense_overhead"
CKPT_PATH = Path("data") / "ingredient_head.pt"

DINO_MEAN, DINO_STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


def _seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_table(lio: str | None = None):
    table = yaml.safe_load(TABLE_PATH.read_bytes())
    slot_to_idx = {str(k): v for k, v in table["slot_index"].items()}
    k = len(table["slots"])
    held = slot_to_idx.get(lio) if lio else None
    impurity = 0
    dishes = {}
    for did, row in table["dishes"].items():
        names = {n for n, _g in row["labeled"]}
        if lio is not None and lio in names:
            # ledger 012 rule: drop the ingredient's dishes from TRAIN only —
            # the untouched val/test dishes that contain it ARE the held set
            # a first cut dropped them from every split, which made
            # held_dishes 0 for all four LIO runs (fixed before any gate read).
            if row["split"] == "train":
                impurity += 1
            dishes[did] = row
            continue
        dishes[did] = row
    return table, dishes, slot_to_idx, k, held, impurity


def resolve_png(dish_dir: Path, did: str) -> Path | None:
    png = dish_dir / f"{did}_rgb.png"
    if png.exists():
        return png
    cands = sorted(dish_dir.glob("*")) if dish_dir.is_dir() else []
    return cands[0] if cands else None


def build_eval(model: WeightHead, item: dict, held: int | None,
               device: str):
    """Full-frame ROI forward for one item; returns gram predictions dict."""
    x = item["feat"]
    rois = torch.tensor([[0, 0, 0, x.shape[1], x.shape[2]]],
                        dtype=torch.float, device=device)
    with torch.no_grad():
        out = model(x.unsqueeze(0).to(device), rois)[0]
    pred = torch.clamp(out, min=0) ** 2
    grams: dict[int, float] = {}
    for slot in item["slots"]:
        grams[slot] = float(pred[slot])
    if held is not None:
        grams.setdefault(held, float(pred[held]))
    return grams


def evaluate(model: WeightHead, items: list[dict], held: int | None,
             device: str) -> tuple[float, dict[int, float]]:
    """Per-present-slot grams MAE (macro over slots) + per-slot dict."""
    errs: dict[int, list[float]] = {}
    for it in items:
        grams = build_eval(model, it, held, device)
        for slot, truth in it["slots"].items():
            errs.setdefault(slot, []).append(abs(grams.get(slot, 0.0)
                                                 - truth))
    per = {s: float(np.mean(v)) for s, v in errs.items()}
    macro = float(np.mean(list(per.values()))) if per else float("nan")
    return macro, per


def run_training(args) -> tuple[WeightHead, dict]:
    _seed_all(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    table, dishes, slot_to_idx, k, held, impurity = load_table(args.lio)
    if not dishes:
        raise SystemExit("no dishes available — finish the imagery pull first")

    def build(split: str) -> list[dict]:
        out = []
        for did, row in sorted(dishes.items()):
            if row["split"] != split:
                continue
            slots = {slot_to_idx[n]: g for n, g in row["labeled"]}
            if not slots:
                continue
            png = resolve_png(IMAGERY_DIR / did, did)
            if png is None:
                continue
            img = Image.open(png).convert("RGB").resize(RESIZE)
            t = TF.pil_to_tensor(img).float() / 255.0
            out.append({"id": did, "png": png, "slots": slots,
                        "img_t": TF.normalize(t, DINO_MEAN, DINO_STD)})
        return out

    items: dict[str, list[dict]] = {}
    for s in ("train", "val", "test"):
        items[s] = build(s)
        print(f"  {s}: {len(items[s])} dishes")

    model = WeightHead(num_classes=k, encoder_id=args.encoder,
                       pretrained=True)
    # encode once — frozen-encoder feature cache (in-memory form)
    model.to(device).eval()
    with torch.no_grad():
        for s, lst in items.items():
            for it in lst:
                x = model.encode(it["img_t"].unsqueeze(0).to(device),
                                 no_grad=True)[0].cpu()
                it["feat"] = x
                it["feat_flip"] = x.flip(-1)
    _seed_all(args.seed)  # head init + shuffling reseed (cache-pattern rule)

    targets, masks = {}, {}
    for s, lst in items.items():
        for j, it in enumerate(lst):
            tgt = torch.zeros(k)
            msk = torch.zeros(k, dtype=torch.bool)
            for i, g in it["slots"].items():
                tgt[i] = float(np.sqrt(g))
                msk[i] = True
            targets[(s, j)], masks[(s, j)] = tgt, msk

    rng = random.Random(args.seed)
    opt = torch.optim.AdamW(model.head_mlp.parameters(), lr=1e-3)
    n_batches = max(1, (len(items["train"]) + args.batch - 1) // args.batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt, max_lr=1e-3, total_steps=args.epochs * n_batches)
    lossf = nn.SmoothL1Loss()
    best_val, best_state, val_hist = float("inf"), None, []
    for ep in range(args.epochs):
        order = list(range(len(items["train"])))
        rng.shuffle(order)
        model.train()
        tot, nb = 0.0, 0
        for b0 in range(0, len(order), args.batch):
            b = order[b0:b0 + args.batch]
            fs, tg, mk, rois = [], [], [], []
            for i in b:
                f = items["train"][i]["feat_flip"] \
                    if rng.random() < 0.5 else items["train"][i]["feat"]
                fs.append(f)
                rois.append([0, 0, 0, f.shape[1], f.shape[2]])
                tg.append(targets[("train", i)])
                mk.append(masks[("train", i)])
            feats_b = torch.stack(fs).to(device)
            rois_t = torch.tensor(rois, dtype=torch.float, device=device)
            tgt_b = torch.stack(tg).to(device)
            mk_b = torch.stack(mk).to(device)
            out = model(feats_b, rois_t)[mk_b]
            loss = lossf(out, tgt_b[mk_b])
            opt.zero_grad()
            loss.backward()
            opt.step()
            sched.step()
            tot += float(loss.detach())
            nb += 1
        val_mae, _per = evaluate(model, items["val"], None, device)
        val_hist.append(round(val_mae, 1))
        if val_mae < best_val:
            best_val, best_state = val_mae, \
                copy.deepcopy(model.head_mlp.state_dict())
        print(f"    epoch {ep:>3} loss {tot / max(nb, 1):.4f} "
              f"val_grams_mae {val_mae:.1f} g")
    if best_state is not None:
        model.head_mlp.load_state_dict(best_state)
    model = model.to("cpu")

    report: dict = {"encoder": args.encoder, "slots": k, "seed": args.seed,
                    "best_val_grams_mae": round(best_val, 1),
                    "val_hist_last10": val_hist[-10:]}
    if not args.skip_test and items["test"]:
        test_mae, per = evaluate(model, items["test"], None, "cpu")
        report["test_grams_mae"] = round(test_mae, 1)
        report["test_per_ingredient_mae"] = {
            table["slots"][s]: round(v, 1) for s, v in sorted(per.items())}
        report["reference"] = ("Nutrition5k paper: 29.4 g (13.7%) dish-level "
                               "mass MAE, RGB+volume fusion; ours is "
                               "per-ingredient RGB-only in-domain")
    if args.lio:
        hold_errs = []
        for s in ("val", "test"):
            for it in items[s]:
                if held is not None and held in it["slots"]:
                    grams = build_eval(model, it, held, "cpu")
                    hold_errs.append(abs(grams[held] - it["slots"][held]))
        report["lio"] = {
            "ingredient": args.lio,
            "held_dishes": len(hold_errs),
            "held_ingredient_grams_mae":
                round(float(np.mean(hold_errs)), 1) if hold_errs else None,
            "train_dishes_removed": impurity,
        }

    state = {"head": best_state, "slots": table["slots"],
             "encoder": args.encoder, "seed": args.seed}
    torch.save(state, args.out)
    report["checkpoint"] = args.out
    return model, report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--encoder", default="dinov2",
                    choices=("dinov2", "resnet50"))
    ap.add_argument("--lio", default=None,
                    help="ingredient name for the leave-ingredient-out run")
    ap.add_argument("--skip-test", action="store_true")
    ap.add_argument("--out", default=str(CKPT_PATH))
    args = ap.parse_args()

    _model, report = run_training(args)
    print(json.dumps(report, indent=2))
    Path(str(args.out).replace(".pt", "_train_report.json")).write_text(
        json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
