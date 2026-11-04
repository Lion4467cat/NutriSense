"""Run paired 20-epoch WED DeepLabV3 loss confirmation across seeds."""
from __future__ import annotations

import argparse
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
from torch.utils.data import DataLoader, RandomSampler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.wed_segmentation_variants import build_variant, pretrained_weight_path  # noqa: E402
from models.wed_semantic_segmenter import N_CLASSES  # noqa: E402
from nutrisense_synth.parameters import (  # noqa: E402
    read_wed_train_manifest, wed_dev_group_ids, wed_group_id,
)
from tools.run_wed_segmentation_study import (  # noqa: E402
    BASE_SIZE, WEDStudyDataset, _class_weights, _evaluate, _group_hash,
    _loss, _split_groups,
)

SPLIT_SEED = 42
SEEDS = (42, 43, 44)
EPOCHS = 20


def _state_hash(state: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(state.items()):
        digest.update(name.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def _order_hash(indices: list[int]) -> str:
    return hashlib.sha256(np.asarray(indices, dtype=np.int64).tobytes()).hexdigest()


class _RecordingRandomSampler(RandomSampler):
    def __iter__(self):
        self.last_indices = list(super().__iter__())
        return iter(self.last_indices)


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _make_initializations(seeds: tuple[int, ...], output: Path,
                          device: torch.device) -> dict[int, dict[str, Any]]:
    init_dir = output / "initializations"
    init_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    for seed in seeds:
        _seed_everything(seed)
        model = build_variant("deeplabv3", pretrained=True)
        state = {name: tensor.detach().cpu().clone()
                 for name, tensor in model.state_dict().items()}
        digest = _state_hash(state)
        path = init_dir / f"seed_{seed}.pt"
        if path.is_file():
            saved = torch.load(path, map_location="cpu", weights_only=False)
            if saved.get("state_sha256") != digest:
                raise ValueError(f"Existing initialization does not match seed {seed}")
        else:
            torch.save({"seed": seed, "architecture": "deeplabv3",
                        "state_sha256": digest, "model_state_dict": state}, path)
        result[seed] = {"path": path, "sha256": digest}
        del model, state
        if device.type == "cuda":
            torch.cuda.empty_cache()
    return result


def _candidate_rows(rows: list[dict[str, Any]], group_set: set[str]
                    ) -> list[dict[str, Any]]:
    return [row for row in rows if wed_group_id(row) in group_set]


def _train_run(*, seed: int, loss_kind: str,
               initialization: dict[str, Any], train_rows: list[dict[str, Any]],
               val_rows: list[dict[str, Any]], train_groups: list[str],
               val_groups: list[str], dev_groups: set[str], wed_root: Path,
               output: Path, device: torch.device, workers: int,
               max_new_epochs: int | None = None) -> dict[str, Any]:
    run_dir = output / "candidates" / f"seed_{seed}" / loss_kind
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "training_report.json"
    checkpoint_path = run_dir / "model_best.pt"
    resume_path = run_dir / "resume_state.pt"
    if report_path.is_file() and checkpoint_path.is_file():
        cached = json.loads(report_path.read_text())
        if (cached.get("training_seed") == seed
                and cached.get("loss_kind") == loss_kind
                and cached.get("initialization_sha256") == initialization["sha256"]
                and cached.get("checkpoint_sha256") == hashlib.sha256(
                    checkpoint_path.read_bytes()).hexdigest()
                and cached.get("training_budget", {}).get("epochs_completed") == EPOCHS):
            print(json.dumps({"seed": seed, "loss": loss_kind,
                              "status": "resume_skip_valid"}), flush=True)
            return cached

    _seed_everything(seed)
    width, height = BASE_SIZE
    train_ds = WEDStudyDataset(train_rows, wed_root, (width, height),
                               training=True, food_augmentation=False)
    val_ds = WEDStudyDataset(val_rows, wed_root, (width, height),
                             training=False, food_augmentation=False)
    val_loader = DataLoader(
        val_ds, batch_size=1, shuffle=False, num_workers=workers,
        pin_memory=device.type == "cuda", persistent_workers=False,
    )
    weights = _class_weights(train_rows, wed_root, device)
    initialization_data = torch.load(initialization["path"], map_location="cpu",
                                     weights_only=False)
    if initialization_data["state_sha256"] != initialization["sha256"]:
        raise ValueError("Initialization checkpoint hash mismatch")
    model = build_variant("deeplabv3", pretrained=False).to(device)
    model.load_state_dict(initialization_data["model_state_dict"])
    current_hash = _state_hash(model.state_dict())
    if current_hash != initialization["sha256"]:
        raise ValueError("Loaded model parameters differ from the paired initialization")
    backbone = model.backbone
    optimizer = torch.optim.AdamW([
        {"params": list(backbone.parameters()), "lr": 2e-5},
        {"params": list(model.classifier.parameters()), "lr": 2e-4},
    ], weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=EPOCHS, eta_min=1e-6)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    history: list[dict[str, Any]] = []
    order_hashes: list[str] = []
    best_iou = -1.0
    best_epoch = 0
    best_val: dict[str, Any] | None = None
    elapsed_before = 0.0
    peak_vram_before = 0.0
    start = time.perf_counter()
    first_epoch = 1
    if resume_path.is_file():
        resume = torch.load(resume_path, map_location="cpu", weights_only=False)
        if (resume.get("training_seed") != seed
                or resume.get("loss_kind") != loss_kind
                or resume.get("initialization_sha256") != initialization["sha256"]):
            raise ValueError(f"Resume state does not match paired run: {resume_path}")
        model.load_state_dict(resume["model_state_dict"])
        optimizer.load_state_dict(resume["optimizer_state_dict"])
        scheduler.load_state_dict(resume["scheduler_state_dict"])
        scaler.load_state_dict(resume["scaler_state_dict"])
        first_epoch = int(resume["next_epoch"])
        history = list(resume["history"])
        order_hashes = list(resume["train_example_order_sha256_per_epoch"])
        best_iou = float(resume["best_internal_val_macro_food_iou"])
        best_epoch = int(resume["selected_epoch"])
        best_val = resume["internal_val_metrics_selected"]
        elapsed_before = float(resume["training_wall_s_so_far"])
        peak_vram_before = float(resume["peak_training_vram_mb_so_far"])
    chunk_limit = max_new_epochs if max_new_epochs is not None else EPOCHS
    last_epoch = min(EPOCHS, first_epoch + chunk_limit - 1)
    for epoch in range(first_epoch, last_epoch + 1):
        epoch_seed = seed + epoch * 10007
        _seed_everything(epoch_seed)
        sampler = _RecordingRandomSampler(
            train_ds, generator=torch.Generator().manual_seed(seed + epoch * 1013))
        train_loader = DataLoader(
            train_ds, batch_size=2, sampler=sampler, num_workers=workers,
            pin_memory=device.type == "cuda", persistent_workers=False,
            generator=torch.Generator().manual_seed(seed + epoch * 2027),
        )
        model.train()
        losses = []
        optimizer.zero_grad(set_to_none=True)
        for step, (images, targets) in enumerate(train_loader, start=1):
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            with torch.autocast(device_type="cuda", enabled=device.type == "cuda"):
                logits = model(images)["out"]
                loss = _loss(logits, targets, weights,
                             boundary_aware=loss_kind == "boundary_aware")
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)
            losses.append(float(loss.detach().cpu()))
        order_hashes.append(_order_hash(sampler.last_indices))
        scheduler.step()
        val_metrics = _evaluate(model, val_loader, device)
        score = float(val_metrics["macro_food_iou"])
        record = {
            "epoch": epoch,
            "train_loss": float(np.mean(losses)),
            "internal_val_macro_food_iou": score,
            "internal_val_foreground_iou": float(
                val_metrics["foreground_union"]["iou"]),
            "learning_rates": [float(group["lr"]) for group in optimizer.param_groups],
            "elapsed_s": round(elapsed_before + time.perf_counter() - start, 2),
        }
        history.append(record)
        print(json.dumps({"seed": seed, "loss": loss_kind, **record}), flush=True)
        if score > best_iou:
            best_iou, best_epoch, best_val = score, epoch, val_metrics
            torch.save({
                "architecture_id": "deeplabv3",
                "n_classes": N_CLASSES,
                "input_width": width,
                "input_height": height,
                "model_state_dict": model.state_dict(),
                "selected_epoch": epoch,
                "training_seed": seed,
                "loss_kind": loss_kind,
                "initialization_sha256": initialization["sha256"],
                "internal_val_metrics": val_metrics,
            }, checkpoint_path)
        is_chunk_end = (epoch == last_epoch or epoch == EPOCHS)
        if is_chunk_end and epoch < EPOCHS:
            temporary_resume = resume_path.with_suffix(".tmp")
            torch.save({
                "training_seed": seed,
                "loss_kind": loss_kind,
                "initialization_sha256": initialization["sha256"],
                "next_epoch": epoch + 1,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "scaler_state_dict": scaler.state_dict(),
                "history": history,
                "train_example_order_sha256_per_epoch": order_hashes,
                "best_internal_val_macro_food_iou": best_iou,
                "selected_epoch": best_epoch,
                "internal_val_metrics_selected": best_val,
                "training_wall_s_so_far": round(
                    elapsed_before + time.perf_counter() - start, 2),
                "peak_training_vram_mb_so_far": max(
                    peak_vram_before,
                    torch.cuda.max_memory_allocated(device) / (1024 ** 2)
                    if device.type == "cuda" else 0.0),
            }, temporary_resume)
            temporary_resume.replace(resume_path)
        del train_loader

    if len(history) < EPOCHS:
        progress = {
            "training_seed": seed,
            "loss_kind": loss_kind,
            "initialization_sha256": initialization["sha256"],
            "epochs_completed": len(history),
            "next_epoch": last_epoch + 1,
            "training_budget_epochs": EPOCHS,
            "selected_epoch_so_far": best_epoch,
            "best_internal_val_macro_food_iou_so_far": best_iou,
            "resume_state": str(resume_path),
            "locked_accessed": False,
            "aruco_accessed": False,
            "wed_test_split_accessed": False,
            "synthetic_data_used": False,
        }
        (run_dir / "progress_report.json").write_text(
            json.dumps(progress, indent=2) + "\n")
        del model, optimizer, scheduler, scaler, val_loader
        if device.type == "cuda":
            torch.cuda.empty_cache()
        return progress

    init_tensor_sha = initialization["sha256"]
    checkpoint_sha = hashlib.sha256(checkpoint_path.read_bytes()).hexdigest()
    backbone_path = pretrained_weight_path("deeplabv3")
    report = {
        "training_seed": seed,
        "loss_kind": loss_kind,
        "candidate": "boundary_aware_deeplabv3" if loss_kind == "boundary_aware"
        else "standard_loss_deeplabv3",
        "initialization_checkpoint": str(initialization["path"]),
        "initialization_sha256": init_tensor_sha,
        "train_example_order_sha256_per_epoch": order_hashes,
        "train_example_order_matched_pair": True,
        "data_groups": {
            "train_group_sha256": _group_hash(train_groups),
            "internal_val_group_sha256": _group_hash(val_groups),
            "dev_group_sha256": _group_hash(dev_groups),
        },
        "training_budget": {
            "epochs_requested": EPOCHS,
            "epochs_completed": len(history),
            "selected_epoch": best_epoch,
            "train_views_per_epoch": len(train_rows),
            "internal_val_views": len(val_rows),
            "batch_size": 2,
            "optimizer_updates_per_epoch": (len(train_rows) + 1) // 2,
            "optimizer_updates_total": ((len(train_rows) + 1) // 2) * EPOCHS,
        },
        "selection_metric": "best internal-validation macro food IoU",
        "optimizer": "AdamW; backbone LR 2e-5, head LR 2e-4; cosine schedule T_max=20; weight decay 1e-4",
        "augmentations": "horizontal flip 0.5; brightness/contrast alpha 0.88-1.12, beta -12..12; no extra augmentation",
        "loss": ("0.7 boundary-weighted class-weighted CE + 0.3 foreground soft Dice"
                 if loss_kind == "boundary_aware"
                 else "0.7 class-weighted CE + 0.3 foreground soft Dice"),
        "pretrained_backbone": "torchvision ResNet-50 IMAGENET1K_V2",
        "pretrained_backbone_sha256": hashlib.sha256(
            backbone_path.read_bytes()).hexdigest() if backbone_path else None,
        "internal_val_best_macro_food_iou": best_iou,
        "internal_val_metrics_selected": best_val,
        "checkpoint": str(checkpoint_path),
        "checkpoint_sha256": checkpoint_sha,
        "training_wall_s": round(elapsed_before + time.perf_counter() - start, 2),
        "peak_training_vram_mb": (round(max(
            peak_vram_before,
            torch.cuda.max_memory_allocated(device) / (1024 ** 2)), 1)
            if device.type == "cuda" else None),
        "history": history,
        "locked_accessed": False,
        "aruco_accessed": False,
        "wed_test_split_accessed": False,
        "synthetic_data_used": False,
        "geometry_or_weight_code_changed": False,
    }
    report["trainer_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    if resume_path.exists():
        resume_path.unlink()
    progress_path = run_dir / "progress_report.json"
    if progress_path.exists():
        progress_path.unlink()
    del model, optimizer, scheduler, scaler, val_loader
    if device.type == "cuda":
        torch.cuda.empty_cache()
    return report


def run(*, manifest: Path, wed_root: Path, output: Path,
        seeds: tuple[int, ...] = SEEDS, workers: int = 1,
        device_name: str = "cuda") -> dict[str, Any]:
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; use the approved GPU runtime")
    device = torch.device(device_name)
    _seed_everything(SPLIT_SEED)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    rows = read_wed_train_manifest(manifest)
    dev_groups = wed_dev_group_ids(rows)
    eligible = [row for row in rows if wed_group_id(row) not in dev_groups]
    train_rows, val_rows, train_groups, val_groups = _split_groups(eligible)
    output.mkdir(parents=True, exist_ok=True)
    initializations = _make_initializations(seeds, output, device)
    weights = _class_weights(train_rows, wed_root, device)
    results = []
    for seed in seeds:
        pair = []
        for loss_kind in ("standard", "boundary_aware"):
            pair.append(_train_run(
                seed=seed, loss_kind=loss_kind,
                initialization=initializations[seed], train_rows=train_rows,
                val_rows=val_rows, train_groups=train_groups,
                val_groups=val_groups, dev_groups=dev_groups,
                wed_root=wed_root, output=output, device=device,
                workers=workers))
        if (pair[0]["initialization_sha256"]
                != pair[1]["initialization_sha256"]
                or pair[0]["train_example_order_sha256_per_epoch"]
                != pair[1]["train_example_order_sha256_per_epoch"]):
            raise AssertionError(f"Paired initialization/data order differ for seed {seed}")
        results.extend(pair)
    report = {
        "stage": "paired_wed_boundary_loss_confirmatory_training",
        "created_at": datetime.now(UTC).isoformat(),
        "seeds": list(seeds),
        "epochs_per_run": EPOCHS,
        "eligible_train_views": len(eligible),
        "internal_train_views": len(train_rows),
        "internal_val_views": len(val_rows),
        "dev_views": sum(wed_group_id(row) in dev_groups for row in rows),
        "internal_train_group_sha256": _group_hash(train_groups),
        "internal_val_group_sha256": _group_hash(val_groups),
        "dev_group_sha256": _group_hash(dev_groups),
        "class_weight_sha256": hashlib.sha256(
            weights.detach().cpu().numpy().tobytes()).hexdigest(),
        "runs": results,
        "pair_checks_passed": True,
        "execution_notes": [
            "An initial attempt logged seed 42 standard-loss through epoch 19 without a complete run report; its partial best checkpoint is preserved separately and excluded.",
            "A later standalone seed 42 standard-loss run reached 20 epochs but used persistent-worker random augmentation draws; it is preserved as a legacy artifact and excluded because it cannot be paired with the deterministic epoch-boundary-resumable runs.",
            "A concurrent restart attempt exited with CUDA OOM while the prior process still occupied the GPU; it produced no accepted run report or checkpoint.",
            "Only runs with all 20 epochs, a matching paired initialization hash, matching per-epoch example-order hashes, and a completed training report are eligible for final DEV evaluation.",
        ],
        "locked_accessed": False,
        "aruco_accessed": False,
        "wed_test_split_accessed": False,
        "synthetic_data_used": False,
        "geometry_or_weight_code_changed": False,
        "recommendation_status": "awaiting frozen DEV evaluation",
    }
    (output / "training_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def run_chunk(*, manifest: Path, wed_root: Path, output: Path, seed: int,
              loss_kind: str, epoch_chunk: int = 10, workers: int = 1,
              device_name: str = "cuda") -> dict[str, Any]:
    """Run or resume one short chunk of a single paired 20-epoch model."""
    if loss_kind not in {"standard", "boundary_aware"}:
        raise ValueError(f"Unknown loss condition: {loss_kind}")
    if not 1 <= epoch_chunk <= EPOCHS:
        raise ValueError("epoch_chunk must be between 1 and 20")
    if device_name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; use the approved GPU runtime")
    device = torch.device(device_name)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    rows = read_wed_train_manifest(manifest)
    dev_groups = wed_dev_group_ids(rows)
    eligible = [row for row in rows if wed_group_id(row) not in dev_groups]
    train_rows, val_rows, train_groups, val_groups = _split_groups(eligible)
    output.mkdir(parents=True, exist_ok=True)
    initialization = _make_initializations((seed,), output, device)[seed]
    return _train_run(
        seed=seed, loss_kind=loss_kind, initialization=initialization,
        train_rows=train_rows, val_rows=val_rows, train_groups=train_groups,
        val_groups=val_groups, dev_groups=dev_groups, wed_root=wed_root,
        output=output, device=device, workers=workers,
        max_new_epochs=epoch_chunk)


def finalize_report(*, output: Path, seeds: tuple[int, ...] = SEEDS
                    ) -> dict[str, Any]:
    runs = []
    for seed in seeds:
        pair = []
        for loss_kind in ("standard", "boundary_aware"):
            path = (output / "candidates" / f"seed_{seed}" / loss_kind
                    / "training_report.json")
            if not path.is_file():
                raise FileNotFoundError(f"Incomplete 20-epoch run: {path}")
            report = json.loads(path.read_text())
            if report.get("training_budget", {}).get("epochs_completed") != EPOCHS:
                raise ValueError(f"Run did not complete {EPOCHS} epochs: {path}")
            pair.append(report)
        if (pair[0]["initialization_sha256"] != pair[1]["initialization_sha256"]
                or pair[0]["train_example_order_sha256_per_epoch"]
                != pair[1]["train_example_order_sha256_per_epoch"]):
            raise AssertionError(f"Paired initialization/data order differ for seed {seed}")
        for item in pair:
            item["train_example_order_matched_pair"] = True
            runs.append(item)
    report = {
        "stage": "paired_wed_boundary_loss_confirmatory_training",
        "created_at": datetime.now(UTC).isoformat(),
        "seeds": list(seeds),
        "epochs_per_run": EPOCHS,
        "runs": runs,
        "pair_checks_passed": True,
        "execution_notes": [
            "An initial attempt logged seed 42 standard-loss through epoch 19 without a complete run report; its partial best checkpoint is preserved separately and excluded.",
            "A later standalone seed 42 standard-loss run reached 20 epochs but used persistent-worker random augmentation draws; it is preserved as a legacy artifact and excluded because it cannot be paired with the deterministic epoch-boundary-resumable runs.",
            "A concurrent restart attempt exited with CUDA OOM while the prior process still occupied the GPU; it produced no accepted run report or checkpoint.",
            "The accepted runs were resumed from epoch-boundary optimizer checkpoints in two 10-epoch chunks; per-epoch data and augmentation seeds preserve the matched examples and random transforms across each pair.",
            "Only runs with all 20 epochs, matching paired initialization hashes, matching per-epoch example-order hashes, and completed reports are eligible for final DEV evaluation.",
        ],
        "locked_accessed": False,
        "aruco_accessed": False,
        "wed_test_split_accessed": False,
        "synthetic_data_used": False,
        "geometry_or_weight_code_changed": False,
        "recommendation_status": "awaiting frozen DEV evaluation",
    }
    (output / "training_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--wed-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "experiments/wed_boundary_confirmatory")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(SEEDS))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--loss-kind", choices=("standard", "boundary_aware"))
    parser.add_argument("--epoch-chunk", type=int, default=10)
    args = parser.parse_args()
    if args.seed is not None or args.loss_kind is not None:
        if args.seed is None or args.loss_kind is None:
            parser.error("--seed and --loss-kind must be supplied together")
        result = run_chunk(
            manifest=args.manifest, wed_root=args.wed_root,
            output=args.output, seed=args.seed, loss_kind=args.loss_kind,
            epoch_chunk=args.epoch_chunk, workers=args.workers,
            device_name=args.device)
        print(json.dumps({"seed": args.seed, "loss_kind": args.loss_kind,
                          "epochs_completed": result.get("epochs_completed", 0),
                          "status": "complete" if "training_budget" in result
                          else "chunk_complete"}, indent=2))
        return
    result = run(manifest=args.manifest, wed_root=args.wed_root,
                 output=args.output, workers=args.workers,
                 device_name=args.device, seeds=tuple(args.seeds))
    print(json.dumps({"runs": len(result["runs"]),
                      "training_report": str(args.output / "training_report.json")},
                     indent=2))


if __name__ == "__main__":
    main()
