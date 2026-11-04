"""Train the WED-native 42-label semantic segmentation baseline.

Only WED manifest TRAIN rows are parsed. The fixed DEV groups are excluded,
then a deterministic group-held-out subset of the remaining TRAIN groups is
used for checkpoint selection. WED test / LOCKED / ArUco files are not read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.wed_semantic_segmenter import (  # noqa: E402
    ARCHITECTURE, IMAGE_MEAN, IMAGE_STD, INPUT_HEIGHT, INPUT_WIDTH, N_CLASSES,
    build_model,
)
from nutrisense_synth.parameters import (  # noqa: E402
    read_wed_train_manifest, wed_dev_group_ids, wed_group_id,
)
from nutrisense_synth.wed_segmentation import class_metrics, confusion_matrix  # noqa: E402


class WEDSemanticDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], wed_root: Path,
                 *, training: bool):
        self.rows = rows
        self.wed_root = wed_root
        self.training = training
        self.mean = np.asarray(IMAGE_MEAN, dtype=np.float32)[None, None, :]
        self.std = np.asarray(IMAGE_STD, dtype=np.float32)[None, None, :]

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[index]
        image = cv2.imread(str(self.wed_root / row["image"]), cv2.IMREAD_COLOR)
        labels = cv2.imread(str(self.wed_root / row["mask"]), cv2.IMREAD_GRAYSCALE)
        if image is None or labels is None:
            raise FileNotFoundError(f"Cannot decode WED TRAIN pair: {row['image']}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (INPUT_WIDTH, INPUT_HEIGHT),
                            interpolation=cv2.INTER_LINEAR)
        labels = cv2.resize(labels, (INPUT_WIDTH, INPUT_HEIGHT),
                            interpolation=cv2.INTER_NEAREST)
        if int(labels.max()) >= N_CLASSES:
            raise ValueError(f"Unexpected WED label id in {row['mask']}")
        if self.training:
            if random.random() < 0.5:
                image = image[:, ::-1].copy()
                labels = labels[:, ::-1].copy()
            alpha = random.uniform(0.88, 1.12)
            beta = random.uniform(-12.0, 12.0)
            image = np.clip(image.astype(np.float32) * alpha + beta,
                            0, 255).astype(np.uint8)
        image = image.astype(np.float32) / 255.0
        image = (image - self.mean) / self.std
        tensor = torch.from_numpy(np.ascontiguousarray(image.transpose(2, 0, 1)))
        target = torch.from_numpy(np.ascontiguousarray(labels.astype(np.int64)))
        return tensor, target


def split_groups(rows: list[dict[str, Any]], *, seed: int,
                 fraction: float) -> tuple[list[dict[str, Any]], list[dict[str, Any]],
                                          list[str], list[str]]:
    groups = sorted({wed_group_id(row) for row in rows})
    random.Random(seed).shuffle(groups)
    val_count = max(1, int(len(groups) * fraction))
    val_groups = set(groups[:val_count])
    train_groups = set(groups[val_count:])
    train_rows = [row for row in rows if wed_group_id(row) in train_groups]
    val_rows = [row for row in rows if wed_group_id(row) in val_groups]
    if train_groups & val_groups:
        raise AssertionError("internal TRAIN/validation group leakage")
    return (train_rows, val_rows, sorted(train_groups), sorted(val_groups))


def pixel_class_weights(rows: list[dict[str, Any]], wed_root: Path,
                        device: torch.device) -> torch.Tensor:
    counts = np.zeros(N_CLASSES, dtype=np.int64)
    for row in rows:
        labels = cv2.imread(str(wed_root / row["mask"]), cv2.IMREAD_GRAYSCALE)
        if labels is None:
            raise FileNotFoundError(row["mask"])
        counts += np.bincount(labels.ravel(), minlength=N_CLASSES)[:N_CLASSES]
    if np.any(counts[1:] == 0):
        missing = np.flatnonzero(counts[1:] == 0) + 1
        raise ValueError(f"TRAIN partition has no pixels for classes {missing.tolist()}")
    frequencies = counts[1:] / counts[1:].sum()
    median_frequency = float(np.median(frequencies))
    food_weights = np.sqrt(median_frequency / frequencies)
    food_weights = np.clip(food_weights, 0.5, 4.0)
    food_weights /= food_weights.mean()
    weights = np.concatenate(([0.2], food_weights)).astype(np.float32)
    return torch.tensor(weights, dtype=torch.float32, device=device)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _loss(logits: torch.Tensor, target: torch.Tensor,
          class_weights: torch.Tensor) -> torch.Tensor:
    ce = F.cross_entropy(logits, target, weight=class_weights)
    probabilities = logits.softmax(dim=1)
    one_hot = F.one_hot(target, num_classes=N_CLASSES).permute(0, 3, 1, 2)
    one_hot = one_hot.to(dtype=probabilities.dtype)
    dims = (0, 2, 3)
    intersection = (probabilities * one_hot).sum(dims)
    denominator = probabilities.sum(dims) + one_hot.sum(dims)
    dice_per_class = (2 * intersection + 1) / (denominator + 1)
    dice = 1 - dice_per_class[1:].mean()
    return 0.7 * ce + 0.3 * dice


def _evaluate(model: torch.nn.Module, loader: DataLoader,
              device: torch.device) -> dict[str, Any]:
    model.eval()
    confusions = []
    with torch.inference_mode():
        for images, targets in loader:
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            with torch.autocast(device_type="cuda", enabled=device.type == "cuda"):
                logits = model(images)["out"]
            predictions = logits.argmax(dim=1)
            for target, prediction in zip(targets, predictions):
                confusions.append(confusion_matrix(
                    target.cpu().numpy(), prediction.cpu().numpy()))
    names = json.loads((ROOT / "data/wed/index_map.json").read_text())
    class_names = {int(key): value for key, value in names.items() if int(key) > 0}
    return class_metrics(confusions, class_names)


def train(*, manifest: Path, wed_root: Path, out_dir: Path, seed: int = 42,
          epochs: int = 20, batch_size: int = 2, workers: int = 1,
          val_fraction: float = 0.10, device_name: str = "cuda",
          patience: int = 6) -> dict[str, Any]:
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; use an approved GPU runtime")
    device = torch.device(device_name)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark = True

    manifest_rows = read_wed_train_manifest(manifest)
    dev_groups = wed_dev_group_ids(manifest_rows)
    eligible_rows = [row for row in manifest_rows
                     if wed_group_id(row) not in dev_groups]
    train_rows, val_rows, train_groups, val_groups = split_groups(
        eligible_rows, seed=seed, fraction=val_fraction)
    if not train_rows or not val_rows:
        raise ValueError("group split produced an empty training or validation set")

    out_dir.mkdir(parents=True, exist_ok=True)
    train_ds = WEDSemanticDataset(train_rows, wed_root, training=True)
    val_ds = WEDSemanticDataset(val_rows, wed_root, training=False)
    generator = torch.Generator().manual_seed(seed)
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=workers,
        pin_memory=device.type == "cuda", persistent_workers=workers > 0,
        generator=generator, drop_last=False,
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False, num_workers=workers,
        pin_memory=device.type == "cuda", persistent_workers=workers > 0,
    )
    weights = pixel_class_weights(train_rows, wed_root, device)
    model = build_model(pretrained_backbone=True).to(device)
    backbone = list(model.backbone.parameters())
    classifier = list(model.classifier.parameters())
    optimizer = torch.optim.AdamW([
        {"params": backbone, "lr": 2e-5},
        {"params": classifier, "lr": 2e-4},
    ], weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="max", factor=0.5, patience=2, min_lr=1e-6)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    history: list[dict[str, Any]] = []
    best_score = -1.0
    best_epoch = 0
    no_improvement = 0
    started = time.time()

    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for images, targets in train_loader:
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type="cuda", enabled=device.type == "cuda"):
                logits = model(images)["out"]
                loss = _loss(logits, targets, weights)
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            scaler.step(optimizer)
            scaler.update()
            losses.append(float(loss.detach().cpu()))
        validation = _evaluate(model, val_loader, device)
        score = float(validation["macro_food_iou"])
        scheduler.step(score)
        record = {
            "epoch": epoch,
            "train_loss": float(np.mean(losses)),
            "val_macro_food_iou": score,
            "val_macro_food_dice": float(validation["macro_food_dice"]),
            "val_foreground_union_iou": float(validation["foreground_union"]["iou"]),
            "learning_rates": [float(group["lr"]) for group in optimizer.param_groups],
            "elapsed_s": round(time.time() - started, 2),
        }
        history.append(record)
        print(json.dumps(record), flush=True)
        if score > best_score:
            best_score, best_epoch = score, epoch
            no_improvement = 0
            torch.save({
                "architecture": ARCHITECTURE,
                "n_classes": N_CLASSES,
                "input_height": INPUT_HEIGHT,
                "input_width": INPUT_WIDTH,
                "model_state_dict": model.state_dict(),
                "selected_epoch": epoch,
                "val_metrics": validation,
            }, out_dir / "model_best.pt")
        else:
            no_improvement += 1
            if no_improvement >= patience:
                break

    group_ids = sorted({wed_group_id(row) for row in manifest_rows})
    payload: dict[str, Any] = {
        "stage": "wed_native_semantic_segmentation_training",
        "architecture": ARCHITECTURE,
        "n_classes": N_CLASSES,
        "label_mapping": json.loads((ROOT / "data/wed/index_map.json").read_text()),
        "data_split": {
            "eligible_train_views": len(eligible_rows),
            "eligible_train_groups": len({wed_group_id(r) for r in eligible_rows}),
            "internal_train_views": len(train_rows),
            "internal_train_groups": train_groups,
            "internal_val_views": len(val_rows),
            "internal_val_groups": val_groups,
            "dev_groups_excluded": sorted(dev_groups),
            "seed42_dev_carve_hash": hashlib.sha256(
                "\n".join(sorted(dev_groups)).encode()).hexdigest(),
            "eligible_train_group_hash": hashlib.sha256(
                "\n".join(sorted({wed_group_id(row) for row in eligible_rows})).encode()
            ).hexdigest(),
            "internal_train_group_hash": hashlib.sha256(
                "\n".join(train_groups).encode()).hexdigest(),
            "internal_val_group_hash": hashlib.sha256(
                "\n".join(val_groups).encode()).hexdigest(),
        },
        "training": {
            "seed": seed, "epochs_requested": epochs, "epochs_completed": len(history),
            "selected_epoch": best_epoch, "batch_size": batch_size,
            "workers": workers, "validation_group_fraction": val_fraction,
            "device": str(device), "image_size_wh": [INPUT_WIDTH, INPUT_HEIGHT],
            "optimizer": "AdamW", "backbone_lr": 2e-5, "head_lr": 2e-4,
            "weight_decay": 1e-4, "loss": "0.7 weighted CE + 0.3 foreground soft Dice",
            "class_weights": weights.detach().cpu().tolist(),
            "early_stopping": {"metric": "internal val macro food IoU",
                               "patience": patience},
            "pretrained_backbone": "torchvision ResNet50_Weights.IMAGENET1K_V2",
            "torch": torch.__version__, "torchvision": __import__("torchvision").__version__,
        },
        "best_val_macro_food_iou": best_score,
        "history": history,
        "locked_accessed": False,
        "aruco_accessed": False,
        "test_split_accessed": False,
        "source_sha256": {
            "training_script": _file_sha256(Path(__file__).resolve()),
            "model_definition": _file_sha256(ROOT / "models/wed_semantic_segmenter.py"),
            "metric_definition": _file_sha256(ROOT / "nutrisense_synth/wed_segmentation.py"),
        },
    }
    (out_dir / "training_report.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--wed-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--out-dir", type=Path,
                        default=ROOT / "experiments/wed_native_segmentation")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--val-fraction", type=float, default=0.10)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--patience", type=int, default=6)
    args = parser.parse_args()
    result = train(manifest=args.manifest, wed_root=args.wed_root,
                   out_dir=args.out_dir, seed=args.seed, epochs=args.epochs,
                   batch_size=args.batch_size, workers=args.workers,
                   val_fraction=args.val_fraction, device_name=args.device,
                   patience=args.patience)
    print(json.dumps({"selected_epoch": result["training"]["selected_epoch"],
                      "best_val_macro_food_iou": result["best_val_macro_food_iou"],
                      "out_dir": str(args.out_dir)}, indent=2))


if __name__ == "__main__":
    main()
