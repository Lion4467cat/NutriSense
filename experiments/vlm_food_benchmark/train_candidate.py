"""Fit one participant-separated DINOv2-S plate-total research candidate."""
from __future__ import annotations

import copy
import csv
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
DATA = ROOT / "datasets/raw/portion/vlm-food-benchmark"
MANIFEST = HERE / "manifest.csv"
CHECKPOINT = HERE / "candidate.pt"
REPORT = HERE / "TRAIN_REPORT.json"
DEVICE = "cuda"
SEED = 42
EPOCHS = 80
BATCH_SIZE = 16
RESIZE = (224, 224)
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
        row["grams"] = float(row["total_food_g"])
        row["path"] = DATA / "GT_Mensa_2025/resized_images" / row["image"]
    return rows


def encode_rows(model, rows: list[dict], transform) -> list[dict]:
    encoded = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start:start + BATCH_SIZE]
            tensors = []
            for row in batch:
                with Image.open(row["path"]) as image:
                    tensors.append(transform(image.convert("RGB")))
            pixels = torch.stack(tensors).to(DEVICE)
            features = model.encode(pixels, no_grad=True).cpu()
            encoded.extend(
                {**row, "features": features[index]}
                for index, row in enumerate(batch)
            )
    return encoded


def fit(model, rows: list[dict], epochs: int,
        dev: list[dict] | None = None) -> tuple[int, float, list[dict]]:
    optimizer = torch.optim.AdamW(model.head_mlp.parameters(), lr=1e-3)
    steps = max(1, (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=1e-3, total_steps=epochs * steps
    )
    loss_fn = nn.SmoothL1Loss()
    rng = random.Random(SEED)
    best_mae = float("inf")
    best_epoch = epochs
    best_state = None
    history = []
    for epoch in range(1, epochs + 1):
        order = list(range(len(rows)))
        rng.shuffle(order)
        model.head_mlp.train()
        loss_sum = 0.0
        batch_count = 0
        for start in range(0, len(order), BATCH_SIZE):
            indexes = order[start:start + BATCH_SIZE]
            features = torch.stack([rows[index]["features"] for index in indexes]).to(DEVICE)
            height, width = features.shape[-2:]
            rois = torch.tensor(
                [[i, 0.0, 0.0, float(width), float(height)]
                 for i in range(len(indexes))],
                dtype=torch.float32, device=DEVICE,
            )
            target = torch.tensor(
                [[np.sqrt(rows[index]["grams"])] for index in indexes],
                dtype=torch.float32, device=DEVICE,
            )
            prediction = model(features, rois)
            loss = loss_fn(prediction, target)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            scheduler.step()
            loss_sum += float(loss.detach())
            batch_count += 1
        epoch_row = {
            "epoch": epoch,
            "train_sqrt_smooth_l1": loss_sum / max(1, batch_count),
        }
        if dev is not None:
            model.eval()
            errors = []
            with torch.inference_mode():
                for row in dev:
                    features = row["features"].unsqueeze(0).to(DEVICE)
                    height, width = features.shape[-2:]
                    roi = torch.tensor(
                        [[0.0, 0.0, 0.0, float(width), float(height)]],
                        dtype=torch.float32, device=DEVICE,
                    )
                    estimate = float(model(features, roi)[0, 0].clamp(min=0).square())
                    errors.append(abs(estimate - row["grams"]))
            dev_mae = float(np.mean(errors))
            epoch_row["dev_mae_g"] = dev_mae
            if dev_mae < best_mae:
                best_mae = dev_mae
                best_epoch = epoch
                best_state = copy.deepcopy(model.head_mlp.state_dict())
        history.append(epoch_row)
        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(json.dumps(epoch_row, sort_keys=True), flush=True)
    if dev is not None:
        if best_state is None:
            raise RuntimeError("no development checkpoint selected")
        model.head_mlp.load_state_dict(best_state)
    return best_epoch, best_mae, history


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
        raise RuntimeError("train and dev splits must be non-empty")

    from models.weight_head import WeightHead
    model = WeightHead(num_classes=1, pretrained=True, encoder_id="dinov2").to(DEVICE)
    train = encode_rows(model, train, transform)
    dev = encode_rows(model, dev, transform)
    median = float(np.median([row["grams"] for row in train]))
    median_dev_mae = float(np.mean([abs(median - row["grams"]) for row in dev]))
    best_epoch, best_dev_mae, history = fit(model, train, EPOCHS, dev)

    # Freeze epoch using DEV, then refit fresh on train+dev for that epoch count.
    torch.manual_seed(SEED)
    combined = train + dev
    final_model = WeightHead(num_classes=1, pretrained=True, encoder_id="dinov2").to(DEVICE)
    _, _, refit_history = fit(final_model, combined, best_epoch)
    final_model.save(CHECKPOINT, meta={
        "dataset": "VLM Food Benchmark",
        "source_revision": "d715df0c0debe65da805618431e67f6d0fa01c71",
        "target": "sum of scale-measured item weights; empty-plate tare subtracted",
        "split": "participant groups; train participants 1,2,4,5; dev 3; test 6",
        "seed": SEED,
        "selected_epoch": best_epoch,
    })
    report = {
        "dataset": "VLM Food Benchmark",
        "manifest_sha256": sha256(MANIFEST),
        "source_revision": "d715df0c0debe65da805618431e67f6d0fa01c71",
        "train_count": len(train), "dev_count": len(dev),
        "train_participants": sorted({row["participant_id"] for row in train}),
        "dev_participants": sorted({row["participant_id"] for row in dev}),
        "train_median_total_g": median,
        "dev_median_baseline_mae_g": median_dev_mae,
        "candidate_dev_mae_g": best_dev_mae,
        "selected_epoch": best_epoch,
        "final_refit_count": len(combined),
        "final_refit_epochs": len(refit_history),
        "epochs_searched": EPOCHS,
        "batch_size": BATCH_SIZE,
        "seed": SEED,
        "cuda_device": torch.cuda.get_device_name(0),
        "torch": torch.__version__, "cuda_version": torch.version.cuda,
        "train_script_sha256": sha256(Path(__file__).resolve()),
        "checkpoint_sha256": sha256(CHECKPOINT),
        "test_accessed": False,
        "history": history,
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "history"},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
