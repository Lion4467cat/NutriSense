"""Small, project-authored SPADE-style WED layout-to-RGB research pilot.

Outputs and checkpoints belong under ignored datasets/processed; no product
checkpoint, renderer label, or production model is modified.
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

import cv2
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from nutrisense_synth.parameters import (  # noqa: E402
    DEFAULT_MANIFEST, eligible_wed_train_rows, read_wed_train_manifest, wed_group_id,
)

N_CLASSES = 42
SIDE = 256
TARGET_CLASSES = {1, 12, 28, 32, 34}
DEFAULT_OUT = ROOT / "datasets/processed/conditional_gan_pilot_20261103"


class WedPairs(Dataset):
    def __init__(self):
        self.rows = eligible_wed_train_rows(read_wed_train_manifest(DEFAULT_MANIFEST))
        self.group_counts = Counter(wed_group_id(row) for row in self.rows)
        self.class_groups: dict[int, set[str]] = {}
        for row in self.rows:
            group = wed_group_id(row)
            for dish in row.get("dishes", []):
                cid = int(dish["class_id"])
                self.class_groups.setdefault(cid, set()).add(group)
        self.weights = []
        for row in self.rows:
            group = wed_group_id(row)
            classes = {int(dish["class_id"]) for dish in row.get("dishes", [])}
            inverse = [1.0 / max(1, len(self.class_groups.get(cid, ()))) for cid in classes]
            class_weight = sum(inverse) / max(1, len(inverse))
            self.weights.append(class_weight / self.group_counts[group])
        if len(self.rows) != 1038 or len(self.group_counts) != 198:
            raise RuntimeError("Eligible WED TRAIN views/groups changed from the frozen carve")

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index: int):
        row = self.rows[index]
        image = cv2.imread(str(ROOT / "data/wed" / row["image"]), cv2.IMREAD_COLOR)
        label = cv2.imread(str(ROOT / "data/wed" / row["mask"]), cv2.IMREAD_GRAYSCALE)
        if image is None or label is None:
            raise FileNotFoundError(f"Missing eligible TRAIN pair: {row['image']} / {row['mask']}")
        if image.shape[:2] != label.shape or int(label.max()) >= N_CLASSES:
            raise ValueError(f"Invalid paired RGB/semantic label: {row['image']}")
        image = cv2.cvtColor(cv2.resize(image, (SIDE, SIDE), interpolation=cv2.INTER_AREA),
                             cv2.COLOR_BGR2RGB)
        label = cv2.resize(label, (SIDE, SIDE), interpolation=cv2.INTER_NEAREST).astype(np.int64)
        if random.random() < 0.5:
            image, label = image[:, ::-1].copy(), label[:, ::-1].copy()
        condition = np.eye(N_CLASSES, dtype=np.float32)[label].transpose(2, 0, 1)
        target = image.astype(np.float32).transpose(2, 0, 1) / 127.5 - 1.0
        return torch.from_numpy(condition), torch.from_numpy(target)


class SPADE(nn.Module):
    """Spatially-adaptive normalization from a resized semantic label map."""

    def __init__(self, channels: int):
        super().__init__()
        self.norm = nn.BatchNorm2d(channels, affine=False)
        self.shared = nn.Sequential(nn.Conv2d(N_CLASSES, 64, 3, padding=1), nn.ReLU(True))
        self.gamma = nn.Conv2d(64, channels, 3, padding=1)
        self.beta = nn.Conv2d(64, channels, 3, padding=1)

    def forward(self, x: torch.Tensor, condition: torch.Tensor) -> torch.Tensor:
        semantic = F.interpolate(condition, size=x.shape[-2:], mode="nearest")
        hidden = self.shared(semantic)
        return self.norm(x) * (1.0 + self.gamma(hidden)) + self.beta(hidden)


class SPADEResBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.norm1 = SPADE(in_channels)
        self.norm2 = SPADE(out_channels)
        self.conv1 = nn.Conv2d(in_channels, out_channels, 3, padding=1)
        self.conv2 = nn.Conv2d(out_channels, out_channels, 3, padding=1)
        self.shortcut = nn.Conv2d(in_channels, out_channels, 1) if in_channels != out_channels else None
        self.norm_shortcut = SPADE(in_channels) if self.shortcut is not None else None

    def forward(self, x: torch.Tensor, condition: torch.Tensor) -> torch.Tensor:
        shortcut = x if self.shortcut is None else self.shortcut(
            F.leaky_relu(self.norm_shortcut(x, condition), 0.2))
        h = self.conv1(F.leaky_relu(self.norm1(x, condition), 0.2))
        h = self.conv2(F.leaky_relu(self.norm2(h, condition), 0.2))
        return shortcut + h


class LayoutGenerator(nn.Module):
    """256px semantic generator; renderer labels never enter its output API."""

    architecture = "nutrisense_spade_layout_256_v1"

    def __init__(self, noise_dim: int = 32):
        super().__init__()
        self.noise_dim = noise_dim
        self.seed = nn.Conv2d(N_CLASSES, 512, 3, padding=1)
        self.noise = nn.Linear(noise_dim, 512)
        self.blocks = nn.ModuleList([
            SPADEResBlock(512, 512),
            SPADEResBlock(512, 256),
            SPADEResBlock(256, 128),
            SPADEResBlock(128, 64),
            SPADEResBlock(64, 32),
            SPADEResBlock(32, 32),
        ])
        self.norm_out = SPADE(32)
        self.out = nn.Conv2d(32, 3, 3, padding=1)

    def forward(self, condition: torch.Tensor, z: torch.Tensor | None = None) -> torch.Tensor:
        if z is None:
            z = torch.randn(condition.shape[0], self.noise_dim, device=condition.device)
        low = F.interpolate(condition, size=(8, 8), mode="nearest")
        x = self.seed(low) + self.noise(z)[:, :, None, None]
        sizes = ((8, 8), (16, 16), (32, 32), (64, 64), (128, 128), (256, 256))
        for i, block in enumerate(self.blocks):
            if i:
                x = F.interpolate(x, size=sizes[i], mode="nearest")
            x = block(x, condition)
        return torch.tanh(self.out(F.relu(self.norm_out(x, condition))))


class PatchDiscriminator(nn.Module):
    def __init__(self):
        super().__init__()
        channels = N_CLASSES + 3
        layers = []
        features = []
        for i, out_channels in enumerate((64, 128, 256, 512)):
            layer = nn.Sequential(nn.Conv2d(channels, out_channels, 4, 2, 1),
                                  *( [] if i == 0 else [nn.InstanceNorm2d(out_channels)] ),
                                  nn.LeakyReLU(0.2, True))
            layers.append(layer)
            channels = out_channels
        self.layers = nn.ModuleList(layers)
        self.head = nn.Conv2d(channels, 1, 3, padding=1)

    def forward(self, condition: torch.Tensor, image: torch.Tensor):
        x = torch.cat((condition, image), 1)
        features = []
        for layer in self.layers:
            x = layer(x)
            features.append(x)
        return self.head(x), features


class MultiScaleDiscriminator(nn.Module):
    def __init__(self):
        super().__init__()
        self.scales = nn.ModuleList([PatchDiscriminator(), PatchDiscriminator()])

    def forward(self, condition: torch.Tensor, image: torch.Tensor):
        results = []
        cond, img = condition, image
        for i, discriminator in enumerate(self.scales):
            if i:
                cond = F.avg_pool2d(cond, 3, stride=2, padding=1, count_include_pad=False)
                img = F.avg_pool2d(img, 3, stride=2, padding=1, count_include_pad=False)
            results.append(discriminator(cond, img))
        return results


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def train(args: argparse.Namespace) -> dict:
    if args.device != "cpu" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable in this environment; do not run the full pilot on CPU")
    device = torch.device(args.device)
    torch.manual_seed(args.seed); np.random.seed(args.seed); random.seed(args.seed)
    dataset = WedPairs()
    sampler = WeightedRandomSampler(dataset.weights, len(dataset), replacement=True,
                                    generator=torch.Generator().manual_seed(args.seed))
    loader = DataLoader(dataset, batch_size=args.batch_size, sampler=sampler,
                        num_workers=args.workers, pin_memory=device.type == "cuda",
                        persistent_workers=args.workers > 0)
    generator = LayoutGenerator().to(device)
    discriminator = MultiScaleDiscriminator().to(device)
    opt_g = torch.optim.Adam(generator.parameters(), lr=args.lr, betas=(0.0, 0.9))
    opt_d = torch.optim.Adam(discriminator.parameters(), lr=args.lr, betas=(0.0, 0.9))
    amp = bool(args.amp and device.type == "cuda")
    scaler = torch.amp.GradScaler("cuda", enabled=amp)
    args.out.mkdir(parents=True, exist_ok=True)
    log_path = args.out / "spade_training_log.jsonl"
    manifest_rows = eligible_wed_train_rows(read_wed_train_manifest(DEFAULT_MANIFEST))
    manifest_digest = hashlib.sha256("\n".join(
        json.dumps(row, sort_keys=True) for row in manifest_rows).encode()).hexdigest()
    global_step = 0
    for epoch in range(1, args.epochs + 1):
        generator.train(); discriminator.train()
        sums = Counter(); start = time.perf_counter()
        if device.type == "cuda": torch.cuda.reset_peak_memory_stats(device)
        for condition, real in loader:
            condition, real = condition.to(device, non_blocking=True), real.to(device, non_blocking=True)
            z = torch.randn(condition.shape[0], generator.noise_dim, device=device)
            opt_d.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp):
                fake = generator(condition, z).detach()
                pred_real = discriminator(condition, real)
                pred_fake = discriminator(condition, fake)
                loss_d = sum(F.relu(1.0 - r[0]).mean() + F.relu(1.0 + f[0]).mean()
                             for r, f in zip(pred_real, pred_fake))
            scaler.scale(loss_d).backward(); scaler.step(opt_d)
            for parameter in discriminator.parameters():
                parameter.requires_grad_(False)
            opt_g.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=amp):
                generated = generator(condition, z)
                pred_fake_g = discriminator(condition, generated)
                with torch.no_grad():
                    pred_real_g = discriminator(condition, real)
                adversarial = sum(-fake_score.mean() for fake_score, _ in pred_fake_g)
                feature_match = sum(
                    F.l1_loss(fake_features[j], real_features[j].detach())
                    for (_, fake_features), (_, real_features) in zip(pred_fake_g, pred_real_g)
                    for j in range(len(fake_features)))
                reconstruction = F.l1_loss(generated, real)
                loss_g = adversarial + 10.0 * feature_match + 50.0 * reconstruction
            scaler.scale(loss_g).backward(); scaler.step(opt_g); scaler.update()
            for parameter in discriminator.parameters():
                parameter.requires_grad_(True)
            sums.update({"g": float(loss_g.detach()), "d": float(loss_d.detach()),
                         "adv": float(adversarial.detach()), "fm": float(feature_match.detach()),
                         "l1": float(reconstruction.detach())})
            global_step += 1
        record = {"epoch": epoch, "global_step": global_step,
                  "loss_g": sums["g"] / max(1, len(loader)),
                  "loss_d": sums["d"] / max(1, len(loader)),
                  "loss_adv": sums["adv"] / max(1, len(loader)),
                  "loss_feature_matching": sums["fm"] / max(1, len(loader)),
                  "loss_l1": sums["l1"] / max(1, len(loader)),
                  "epoch_seconds": time.perf_counter() - start,
                  "images_per_second": len(dataset) / max(time.perf_counter() - start, 1e-6),
                  "peak_vram_mb": (torch.cuda.max_memory_allocated(device) / (1024**2)
                                   if device.type == "cuda" else 0),
                  "seed": args.seed, "resolution": [SIDE, SIDE], "batch_size": args.batch_size,
                  "amp": amp}
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        checkpoint = args.out / f"spade_epoch_{epoch:03d}.pt"
        if epoch % args.save_every == 0 or epoch == args.epochs:
            torch.save({"architecture": LayoutGenerator.architecture,
                        "generator_state_dict": generator.state_dict(),
                        "discriminator_state_dict": discriminator.state_dict(),
                        "epoch": epoch, "steps": global_step, "seed": args.seed,
                        "resolution": [SIDE, SIDE], "class_count": N_CLASSES}, checkpoint)
            provenance = {"method": "project_authored_spade_style_multiscale_pix2pix",
                          "checkpoint": checkpoint.name, "checkpoint_sha256": _sha256(checkpoint),
                          "training_manifest_sha256": manifest_digest,
                          "training_source_splits": ["eligible_wed_train"],
                          "training_views": len(dataset), "training_groups": len(dataset.group_counts),
                          "target_diagnostic_class_ids": sorted(TARGET_CLASSES),
                          "external_weights_downloaded": False,
                          "production_checkpoints_modified": False,
                          "protected_splits_accessed": False,
                          "official_spade_code_copied": False,
                          "code_note": "Independent project implementation of published SPADE normalization and conditional multiscale PatchGAN concepts; research-only until license review."}
            checkpoint.with_suffix(".pt.provenance.json").write_text(
                json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record, sort_keys=True), flush=True)
    return {"epochs": args.epochs, "steps": global_step, "log": str(log_path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--amp", action="store_true")
    parser.add_argument("--save-every", type=int, default=5)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(train(args), indent=2))


if __name__ == "__main__":
    main()
