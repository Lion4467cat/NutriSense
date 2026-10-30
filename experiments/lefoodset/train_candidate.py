"""Train one research-only single-food mass candidate on LeFood train classes."""
from __future__ import annotations

import csv
import copy
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MANIFEST = HERE / "manifest.csv"
CHECKPOINT = HERE / "candidate.pt"
REPORT = HERE / "TRAIN_REPORT.json"
SEED = 42
EPOCHS = 80
BATCH_SIZE = 16
DEVICE = "cuda"
RESIZE = (224, 224)
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_split(split: str) -> list[dict]:
    with MANIFEST.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["split"] == split]
    for row in rows:
        row["grams"] = float(row["before_g"])
        row["path"] = ROOT / row["before_path"]
    return rows


def encode_rows(model, rows: list[dict], transform, batch_size: int = 16) -> list[dict]:
    encoded = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(rows), batch_size):
            batch_rows = rows[start:start + batch_size]
            tensors = []
            for row in batch_rows:
                with Image.open(row["path"]) as image:
                    tensors.append(transform(image.convert("RGB")))
            pixels = torch.stack(tensors).to(DEVICE)
            features = model.encode(pixels, no_grad=True).cpu()
            encoded.extend({**row, "features": features[i]} for i, row in enumerate(batch_rows))
    return encoded


def evaluate(model, rows: list[dict]) -> float:
    model.eval()
    errors = []
    with torch.inference_mode():
        for row in rows:
            features = row["features"].unsqueeze(0).to(DEVICE)
            h, w = features.shape[-2:]
            roi = torch.tensor([[0.0, 0.0, 0.0, float(w), float(h)]],
                               dtype=torch.float, device=DEVICE)
            estimate = float(model(features, roi)[0, 0].clamp(min=0).square().item())
            errors.append(abs(estimate - row["grams"]))
    return float(np.mean(errors)) if errors else float("inf")


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; refusing CPU fallback")
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    transform = transforms.Compose([
        transforms.Resize(RESIZE),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    train = read_split("train")
    dev = read_split("dev")
    if not train or not dev:
        raise RuntimeError("train and dev splits must both be non-empty")

    from models.weight_head import WeightHead
    model = WeightHead(num_classes=1, pretrained=True, encoder_id="dinov2").to(DEVICE)
    train = encode_rows(model, train, transform)
    dev = encode_rows(model, dev, transform)
    train_median = float(np.median([row["grams"] for row in train]))
    median_dev_mae = float(np.mean([abs(train_median - row["grams"]) for row in dev]))

    optimizer = torch.optim.AdamW(model.head_mlp.parameters(), lr=1e-3)
    steps = max(1, (len(train) + BATCH_SIZE - 1) // BATCH_SIZE)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=1e-3, total_steps=EPOCHS * steps)
    loss_fn = nn.SmoothL1Loss()
    rng = random.Random(SEED)
    best_dev = float("inf")
    best_epoch = 0
    best_state = None
    history = []
    for epoch in range(1, EPOCHS + 1):
        order = list(range(len(train)))
        rng.shuffle(order)
        model.head_mlp.train()
        epoch_loss = 0.0
        n_batches = 0
        for start in range(0, len(order), BATCH_SIZE):
            indices = order[start:start + BATCH_SIZE]
            feats = torch.stack([train[index]["features"] for index in indices]).to(DEVICE)
            h, w = feats.shape[-2:]
            rois = torch.tensor([[i, 0.0, 0.0, float(w), float(h)]
                                 for i in range(len(indices))],
                                dtype=torch.float, device=DEVICE)
            target = torch.tensor([[np.sqrt(train[index]["grams"])]
                                   for index in indices], dtype=torch.float, device=DEVICE)
            prediction = model(feats, rois)
            loss = loss_fn(prediction, target)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            scheduler.step()
            epoch_loss += float(loss.detach())
            n_batches += 1
        dev_mae = evaluate(model, dev)
        row = {"epoch": epoch, "train_sqrt_smooth_l1": epoch_loss / max(1, n_batches),
               "dev_mae_g": dev_mae}
        history.append(row)
        if dev_mae < best_dev:
            best_dev = dev_mae
            best_epoch = epoch
            best_state = copy.deepcopy(model.head_mlp.state_dict())
        if epoch == 1 or epoch % 10 == 0:
            print(json.dumps(row, sort_keys=True), flush=True)

    assert best_state is not None
    model.head_mlp.load_state_dict(best_state)
    checkpoint = {
        "head_mlp": best_state,
        "num_classes": 1,
        "roi_res": model.roi_res,
        "encoder_id": "dinov2",
        "meta": {
            "dataset": "LeFood-Set V1",
            "target": "source-reported Weight Before Eaten (g)",
            "tare_caveat": "paper does not document tare handling",
            "split_rule": "food-category-disjoint hash split",
            "seed": SEED,
            "best_epoch": best_epoch,
        },
    }
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, CHECKPOINT)
    report = {
        "dataset": "LeFood-Set V1",
        "manifest_sha256": sha256(MANIFEST),
        "train_count": len(train),
        "dev_count": len(dev),
        "train_category_count": len({row["food_name"] for row in train}),
        "dev_category_count": len({row["food_name"] for row in dev}),
        "train_global_median_g": train_median,
        "dev_global_median_baseline_mae_g": median_dev_mae,
        "candidate_dev_mae_g": best_dev,
        "best_epoch": best_epoch,
        "epochs": EPOCHS,
        "batch_size": BATCH_SIZE,
        "seed": SEED,
        "cuda_device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "cuda_version": torch.version.cuda,
        "train_script_sha256": sha256(Path(__file__).resolve()),
        "checkpoint_sha256": sha256(CHECKPOINT),
        "history": history,
        "test_accessed": False,
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items()
                      if key != "history"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
