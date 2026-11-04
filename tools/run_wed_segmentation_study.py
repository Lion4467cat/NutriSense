"""Run controlled WED TRAIN-only segmentation ablations and architecture study."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import random
import sys
import time
from typing import Any

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.wed_segmentation_variants import (  # noqa: E402
    SEGFORMER_ID, build_variant, pretrained_weight_path,
)
from models.wed_semantic_segmenter import (  # noqa: E402
    IMAGE_MEAN, IMAGE_STD, N_CLASSES,
)
from nutrisense_synth.parameters import (  # noqa: E402
    read_wed_train_manifest, wed_dev_group_ids, wed_group_id,
)
from nutrisense_synth.wed_segmentation import class_metrics, confusion_matrix  # noqa: E402

BASE_SIZE = (768, 1024)
HIGH_SIZE = (864, 1152)
EPOCHS = 10
INTERNAL_VAL_FRACTION = 0.10
SEED = 42
CLASS_BALANCE = "capped_mean_inverse_sqrt_class_presence"


def _sha(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _group_hash(groups: list[str] | set[str]) -> str:
    return hashlib.sha256("\n".join(sorted(groups)).encode()).hexdigest()


class WEDStudyDataset(Dataset):
    def __init__(self, rows: list[dict[str, Any]], root: Path,
                 size: tuple[int, int], *, training: bool,
                 food_augmentation: bool):
        self.rows = rows
        self.root = root
        self.width, self.height = size
        self.training = training
        self.food_augmentation = food_augmentation
        self.mean = np.asarray(IMAGE_MEAN, dtype=np.float32)[None, None, :]
        self.std = np.asarray(IMAGE_STD, dtype=np.float32)[None, None, :]

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[index]
        image = cv2.imread(str(self.root / row["image"]), cv2.IMREAD_COLOR)
        labels = cv2.imread(str(self.root / row["mask"]), cv2.IMREAD_GRAYSCALE)
        if image is None or labels is None:
            raise FileNotFoundError(f"Cannot decode eligible WED TRAIN pair: {row['image']}")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (self.width, self.height),
                            interpolation=cv2.INTER_LINEAR)
        labels = cv2.resize(labels, (self.width, self.height),
                            interpolation=cv2.INTER_NEAREST)
        if self.training:
            if random.random() < 0.5:
                image, labels = image[:, ::-1].copy(), labels[:, ::-1].copy()
            if self.food_augmentation and random.random() < 0.5:
                image, labels = image[::-1].copy(), labels[::-1].copy()
            if self.food_augmentation:
                angle = random.uniform(-10.0, 10.0)
                scale = random.uniform(0.95, 1.05)
                matrix = cv2.getRotationMatrix2D(
                    (self.width / 2.0, self.height / 2.0), angle, scale)
                image = cv2.warpAffine(
                    image, matrix, (self.width, self.height),
                    flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
                labels = cv2.warpAffine(
                    labels, matrix, (self.width, self.height),
                    flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT,
                    borderValue=0)
            alpha = random.uniform(0.88, 1.12)
            beta = random.uniform(-12.0, 12.0)
            image = np.clip(image.astype(np.float32) * alpha + beta,
                            0, 255).astype(np.uint8)
            if self.food_augmentation:
                hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV).astype(np.float32)
                hsv[:, :, 1] *= random.uniform(0.88, 1.12)
                hsv[:, :, 2] *= random.uniform(0.94, 1.06)
                hsv = np.clip(hsv, (0, 0, 0), (179, 255, 255)).astype(np.uint8)
                image = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        image = image.astype(np.float32) / 255.0
        image = (image - self.mean) / self.std
        image_tensor = torch.from_numpy(np.ascontiguousarray(
            image.transpose(2, 0, 1)))
        target_tensor = torch.from_numpy(np.ascontiguousarray(
            labels.astype(np.int64)))
        return image_tensor, target_tensor


def _split_groups(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]],
                                                       list[dict[str, Any]],
                                                       list[str], list[str]]:
    groups = sorted({wed_group_id(row) for row in rows})
    random.Random(SEED).shuffle(groups)
    val_count = max(1, int(len(groups) * INTERNAL_VAL_FRACTION))
    val_groups = set(groups[:val_count])
    train_groups = set(groups[val_count:])
    train_rows = [row for row in rows if wed_group_id(row) in train_groups]
    val_rows = [row for row in rows if wed_group_id(row) in val_groups]
    if train_groups & val_groups:
        raise AssertionError("physical group appears in both training and validation")
    return train_rows, val_rows, sorted(train_groups), sorted(val_groups)


def _class_weights(rows: list[dict[str, Any]], root: Path,
                   device: torch.device) -> torch.Tensor:
    counts = np.zeros(N_CLASSES, dtype=np.int64)
    for row in rows:
        labels = cv2.imread(str(root / row["mask"]), cv2.IMREAD_GRAYSCALE)
        if labels is None:
            raise FileNotFoundError(row["mask"])
        counts += np.bincount(labels.ravel(), minlength=N_CLASSES)[:N_CLASSES]
    if np.any(counts[1:] == 0):
        raise ValueError("The internal training split lacks one or more WED classes")
    freq = counts[1:] / counts[1:].sum()
    weights = np.sqrt(np.median(freq) / freq)
    weights = np.clip(weights, 0.5, 4.0)
    weights /= weights.mean()
    return torch.tensor(np.r_[0.2, weights], dtype=torch.float32, device=device)


class _RecordingWeightedSampler(WeightedRandomSampler):
    def __iter__(self):
        self.last_indices = list(super().__iter__())
        return iter(self.last_indices)


def _balanced_sampler(rows: list[dict[str, Any]], generator: torch.Generator
                      ) -> WeightedRandomSampler:
    frequencies = np.zeros(N_CLASSES, dtype=np.int64)
    row_classes = []
    for row in rows:
        classes = sorted({int(dish["class_id"]) for dish in row["dishes"]})
        row_classes.append(classes)
        frequencies[classes] += 1
    class_weights = np.zeros(N_CLASSES, dtype=np.float64)
    present = frequencies[1:] > 0
    class_weights[1:][present] = 1.0 / np.sqrt(frequencies[1:][present])
    weights = np.asarray([
        float(np.mean(class_weights[classes])) if classes else 1.0
        for classes in row_classes
    ])
    weights /= max(1e-12, float(weights.mean()))
    weights = np.clip(weights, 0.5, 3.0)
    return _RecordingWeightedSampler(weights.tolist(), len(rows),
                                     replacement=True, generator=generator)


def _boundary_weight_map(target: torch.Tensor) -> torch.Tensor:
    one_hot = F.one_hot(target, num_classes=N_CLASSES).permute(0, 3, 1, 2)
    one_hot = one_hot.to(torch.float32)
    maximum = F.max_pool2d(one_hot, kernel_size=3, stride=1, padding=1)
    minimum = -F.max_pool2d(-one_hot, kernel_size=3, stride=1, padding=1)
    edge = (maximum - minimum).sum(dim=1) > 0
    return 1.0 + 2.0 * edge.to(torch.float32)


def _loss(logits: torch.Tensor, target: torch.Tensor,
          class_weights: torch.Tensor, *, boundary_aware: bool) -> torch.Tensor:
    if logits.shape[-2:] != target.shape[-2:]:
        logits = F.interpolate(logits, size=target.shape[-2:], mode="bilinear",
                               align_corners=False)
    if boundary_aware:
        pixel_loss = F.cross_entropy(logits, target, weight=class_weights,
                                     reduction="none")
        edge_weights = _boundary_weight_map(target)
        ce = (pixel_loss * edge_weights).sum() / edge_weights.sum().clamp_min(1.0)
    else:
        ce = F.cross_entropy(logits, target, weight=class_weights)
    probabilities = logits.softmax(dim=1)
    one_hot = F.one_hot(target, num_classes=N_CLASSES).permute(0, 3, 1, 2)
    one_hot = one_hot.to(probabilities.dtype)
    dims = (0, 2, 3)
    intersection = (probabilities * one_hot).sum(dims)
    denominator = probabilities.sum(dims) + one_hot.sum(dims)
    dice = 1 - ((2 * intersection[1:] + 1)
                / (denominator[1:] + 1)).mean()
    return 0.7 * ce + 0.3 * dice


def _freeze_global_pool_batch_norm(model: torch.nn.Module) -> None:
    """Avoid singleton BatchNorm failure in ASPP's 1×1 pooling branch."""
    for name, module in model.named_modules():
        is_global_pool_norm = (
            name == "classifier.0.convs.4.2" or name == "aspp.pool.2")
        if is_global_pool_norm and isinstance(module, torch.nn.modules.batchnorm._BatchNorm):
            module.eval()


def _evaluate(model: torch.nn.Module, loader: DataLoader,
              device: torch.device) -> dict[str, Any]:
    model.eval()
    matrices = []
    with torch.inference_mode():
        for images, targets in loader:
            images, targets = images.to(device), targets.to(device)
            with torch.autocast(device_type="cuda", enabled=device.type == "cuda"):
                logits = model(images)["out"]
            predictions = logits.argmax(1)
            for truth, prediction in zip(targets, predictions):
                matrices.append(confusion_matrix(truth.cpu().numpy(),
                                                 prediction.cpu().numpy()))
    id_map = json.loads((ROOT / "data/wed/index_map.json").read_text())
    names = {int(key): str(value) for key, value in id_map.items() if int(key) > 0}
    return class_metrics(matrices, names)


def _candidate_configs() -> list[dict[str, Any]]:
    return [
        {"name": "dlv3_control", "architecture": "deeplabv3",
         "size": list(BASE_SIZE), "balanced_sampling": False,
         "food_augmentation": False, "boundary_aware_loss": False},
        {"name": "dlv3_highres", "architecture": "deeplabv3",
         "size": list(HIGH_SIZE), "balanced_sampling": False,
         "food_augmentation": False, "boundary_aware_loss": False},
        {"name": "dlv3_class_balanced", "architecture": "deeplabv3",
         "size": list(BASE_SIZE), "balanced_sampling": True,
         "food_augmentation": False, "boundary_aware_loss": False},
        {"name": "dlv3_food_augmentation", "architecture": "deeplabv3",
         "size": list(BASE_SIZE), "balanced_sampling": False,
         "food_augmentation": True, "boundary_aware_loss": False},
        {"name": "dlv3_boundary_loss", "architecture": "deeplabv3",
         "size": list(BASE_SIZE), "balanced_sampling": False,
         "food_augmentation": False, "boundary_aware_loss": True},
    ]


def _train_candidate(config: dict[str, Any], *, train_rows: list[dict[str, Any]],
                     val_rows: list[dict[str, Any]], train_groups: list[str],
                     val_groups: list[str], dev_groups: set[str],
                     wed_root: Path, out_root: Path, device: torch.device,
                     epochs: int, workers: int) -> dict[str, Any]:
    candidate_dir = out_root / "candidates" / config["name"]
    candidate_dir.mkdir(parents=True, exist_ok=True)
    existing_report = candidate_dir / "training_report.json"
    existing_checkpoint = candidate_dir / "model_best.pt"
    if existing_report.is_file() and existing_checkpoint.is_file():
        cached = json.loads(existing_report.read_text())
        if (cached.get("candidate") == config
                and cached.get("training_budget", {}).get("epochs_requested") == epochs
                and cached.get("training_budget", {}).get("epochs_completed") == epochs
                and cached.get("checkpoint_sha256") == _sha(existing_checkpoint)):
            print(json.dumps({"candidate": config["name"], "status": "resume_skip_valid"}),
                  flush=True)
            return cached
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(SEED)
    width, height = map(int, config["size"])
    physical_batch = 1 if config["name"] == "dlv3_highres" else 2
    accumulation = 2 if physical_batch == 1 else 1
    training_ds = WEDStudyDataset(
        train_rows, wed_root, (width, height), training=True,
        food_augmentation=bool(config["food_augmentation"]))
    validation_ds = WEDStudyDataset(
        val_rows, wed_root, (width, height), training=False,
        food_augmentation=False)
    sampler_generator = torch.Generator().manual_seed(SEED)
    sampler = (_balanced_sampler(train_rows, sampler_generator)
               if config["balanced_sampling"] else None)
    loader_generator = torch.Generator().manual_seed(SEED)
    train_loader = DataLoader(
        training_ds, batch_size=physical_batch,
        shuffle=sampler is None, sampler=sampler,
        num_workers=workers, pin_memory=device.type == "cuda",
        persistent_workers=workers > 0, generator=loader_generator,
    )
    val_loader = DataLoader(
        validation_ds, batch_size=1, shuffle=False, num_workers=workers,
        pin_memory=device.type == "cuda", persistent_workers=workers > 0,
    )
    class_weights = _class_weights(train_rows, wed_root, device)
    model = build_variant(config["architecture"], pretrained=True).to(device)
    backbone_params: list[torch.nn.Parameter]
    head_params: list[torch.nn.Parameter]
    if config["architecture"] in {"deeplabv3", "deeplabv3plus"}:
        backbone = getattr(model, "backbone", None)
        if backbone is None:
            backbone_params = [p for name, p in model.named_parameters()
                               if name.startswith(("stem.", "layer1.", "layer2.",
                                                   "layer3.", "layer4."))]
            head_params = [p for name, p in model.named_parameters()
                           if not name.startswith(("stem.", "layer1.", "layer2.",
                                                   "layer3.", "layer4."))]
        else:
            backbone_params = list(backbone.parameters())
            head_params = list(model.classifier.parameters())
    else:
        transformer = getattr(model, "model")
        backbone_params = list(transformer.segformer.parameters())
        head_params = list(transformer.decode_head.parameters())
    optimizer = torch.optim.AdamW([
        {"params": backbone_params, "lr": 2e-5},
        {"params": head_params, "lr": 2e-4},
    ], weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=epochs, eta_min=1e-6)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    history: list[dict[str, Any]] = []
    exposure_history = []
    best_iou = -1.0
    best_epoch = 0
    best_val_metrics: dict[str, Any] | None = None
    start = time.perf_counter()
    optimizer.zero_grad(set_to_none=True)
    for epoch in range(1, epochs + 1):
        model.train()
        if physical_batch == 1:
            _freeze_global_pool_batch_norm(model)
        losses = []
        optimizer.zero_grad(set_to_none=True)
        for step, (images, targets) in enumerate(train_loader, start=1):
            images, targets = images.to(device, non_blocking=True), targets.to(
                device, non_blocking=True)
            with torch.autocast(device_type="cuda", enabled=device.type == "cuda"):
                logits = model(images)["out"]
                loss = _loss(logits, targets, class_weights,
                             boundary_aware=bool(config["boundary_aware_loss"]))
            scaler.scale(loss / accumulation).backward()
            losses.append(float(loss.detach().cpu()))
            update = (step % accumulation == 0 or step == len(train_loader))
            if update:
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad(set_to_none=True)
        if sampler is None:
            sampled_indices = list(range(len(train_rows)))
        else:
            sampled_indices = sampler.last_indices
        class_exposure = np.zeros(N_CLASSES, dtype=np.int64)
        for sampled_index in sampled_indices:
            for class_id in {int(d["class_id"])
                             for d in train_rows[sampled_index]["dishes"]}:
                class_exposure[class_id] += 1
        exposure_history.append({
            "epoch": epoch,
            "sampled_views": len(sampled_indices),
            "class_presence_view_counts": class_exposure[1:].tolist(),
        })
        scheduler.step()
        val_metrics = _evaluate(model, val_loader, device)
        score = float(val_metrics["macro_food_iou"])
        record = {
            "epoch": epoch,
            "train_loss": float(np.mean(losses)),
            "internal_val_macro_food_iou": score,
            "internal_val_foreground_iou": float(val_metrics["foreground_union"]["iou"]),
            "learning_rates": [float(g["lr"]) for g in optimizer.param_groups],
            "elapsed_s": round(time.perf_counter() - start, 2),
        }
        history.append(record)
        print(json.dumps({"candidate": config["name"], **record}), flush=True)
        if score > best_iou:
            best_iou, best_epoch = score, epoch
            best_val_metrics = val_metrics
            torch.save({
                "architecture_id": config["architecture"],
                "n_classes": N_CLASSES,
                "input_width": width,
                "input_height": height,
                "model_state_dict": model.state_dict(),
                "selected_epoch": epoch,
                "internal_val_metrics": val_metrics,
            }, candidate_dir / "model_best.pt")

    pretrained_path = pretrained_weight_path(config["architecture"])
    report = {
        "candidate": config,
        "training_budget": {
            "epochs_requested": epochs,
            "epochs_completed": len(history),
            "selected_epoch": best_epoch,
            "train_views_per_epoch": len(train_rows),
            "internal_val_views": len(val_rows),
            "physical_batch_size": physical_batch,
            "gradient_accumulation": accumulation,
            "effective_batch_size": physical_batch * accumulation,
            "train_loader_batches_per_epoch": len(train_loader),
        },
        "data_groups": {
            "train_group_hash": _group_hash(train_groups),
            "internal_val_group_hash": _group_hash(val_groups),
            "dev_group_hash": _group_hash(dev_groups),
        },
        "internal_val_macro_food_iou_best": best_iou,
        "internal_val_metrics_selected": best_val_metrics,
        "optimizer": "AdamW; encoder 2e-5, head 2e-4; cosine schedule; weight decay 1e-4",
        "loss": ("boundary-weighted 0.7 CE + 0.3 foreground soft Dice"
                 if config["boundary_aware_loss"] else
                 "0.7 weighted CE + 0.3 foreground soft Dice"),
        "class_weight_sha256": hashlib.sha256(
            class_weights.detach().cpu().numpy().tobytes()).hexdigest(),
        "pretrained_weight_path": str(pretrained_path) if pretrained_path else None,
        "pretrained_weight_sha256": _sha(pretrained_path),
        "checkpoint": str(candidate_dir / "model_best.pt"),
        "checkpoint_sha256": _sha(candidate_dir / "model_best.pt"),
        "source_sha256": {
            "study_runner": _sha(Path(__file__).resolve()),
            "variant_definitions": _sha(ROOT / "models/wed_segmentation_variants.py"),
            "study_protocol": _sha(ROOT / "experiments/wed_native_segmentation/study_protocol.md"),
        },
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "training_wall_s": round(time.perf_counter() - start, 2),
        "peak_training_vram_mb": (round(torch.cuda.max_memory_allocated(device)
                                         / (1024 ** 2), 1)
                                  if device.type == "cuda" else None),
        "history": history,
        "class_exposure_per_epoch": exposure_history,
        "locked_accessed": False,
        "aruco_accessed": False,
        "test_split_accessed": False,
        "synthetic_data_used": False,
    }
    (candidate_dir / "training_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    del model, optimizer, scheduler, scaler, train_loader, val_loader
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return report


def run_study(*, manifest: Path, wed_root: Path, out_root: Path,
              epochs: int = EPOCHS, workers: int = 1,
              device_name: str = "cuda") -> dict[str, Any]:
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; run on the approved GPU runtime")
    device = torch.device(device_name)
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if device.type == "cuda":
        torch.cuda.manual_seed_all(SEED)
        torch.backends.cudnn.benchmark = True
    manifest_train = read_wed_train_manifest(manifest)
    dev_groups = wed_dev_group_ids(manifest_train)
    eligible = [row for row in manifest_train
                if wed_group_id(row) not in dev_groups]
    train_rows, val_rows, train_groups, val_groups = _split_groups(eligible)
    out_root.mkdir(parents=True, exist_ok=True)
    stage_a = []
    for config in _candidate_configs():
        stage_a.append(_train_candidate(
            config, train_rows=train_rows, val_rows=val_rows,
            train_groups=train_groups, val_groups=val_groups,
            dev_groups=dev_groups, wed_root=wed_root, out_root=out_root,
            device=device, epochs=epochs, workers=workers))
    selected = max(stage_a, key=lambda report: (
        report["internal_val_macro_food_iou_best"],
        report["candidate"]["name"] == "dlv3_control"))
    selected_recipe = selected["candidate"]
    architecture_runs = [selected]
    for architecture, name in (("deeplabv3plus", "architecture_deeplabv3plus"),
                               ("segformer_b0", "architecture_segformer_b0")):
        config = {**selected_recipe, "name": name, "architecture": architecture}
        architecture_runs.append(_train_candidate(
            config, train_rows=train_rows, val_rows=val_rows,
            train_groups=train_groups, val_groups=val_groups,
            dev_groups=dev_groups, wed_root=wed_root, out_root=out_root,
            device=device, epochs=epochs, workers=workers))

    summary = {
        "stage": "controlled_wed_segmentation_study_training",
        "created_at": datetime.now(UTC).isoformat(),
        "seed": SEED,
        "epochs_per_candidate": epochs,
        "eligible_train_views": len(eligible),
        "eligible_train_groups": len({wed_group_id(r) for r in eligible}),
        "internal_train_views": len(train_rows),
        "internal_val_views": len(val_rows),
        "dev_views": len([r for r in manifest_train if wed_group_id(r) in dev_groups]),
        "internal_train_group_hash": _group_hash(train_groups),
        "internal_val_group_hash": _group_hash(val_groups),
        "dev_group_hash": _group_hash(dev_groups),
        "stage_a_runs": stage_a,
        "selected_recipe": selected_recipe,
        "architecture_runs": architecture_runs,
        "locked_accessed": False,
        "aruco_accessed": False,
        "test_split_accessed": False,
        "synthetic_data_used": False,
        "geometry_or_weight_code_changed": False,
        "recommendation_status": "awaiting final frozen DEV comparison",
    }
    (out_root / "training_study_report.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--wed-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--out-dir", type=Path,
                        default=ROOT / "experiments/wed_segmentation_study")
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    result = run_study(manifest=args.manifest, wed_root=args.wed_root,
                       out_root=args.out_dir, epochs=args.epochs,
                       workers=args.workers, device_name=args.device)
    print(json.dumps({
        "selected_recipe": result["selected_recipe"],
        "training_report": str(args.out_dir / "training_study_report.json"),
    }, indent=2))


if __name__ == "__main__":
    main()
