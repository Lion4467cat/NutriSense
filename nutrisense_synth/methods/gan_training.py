"""Paired semantic pix2pix-style GAN trained from WED TRAIN only."""
from __future__ import annotations

from pathlib import Path
import json
import hashlib
from collections import Counter

import cv2
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from nutrisense_synth.parameters import eligible_wed_train_rows, read_wed_train_manifest

ROOT = Path(__file__).resolve().parents[2]
TRAIN_SIZE = (384, 256)
SEMANTIC_CHANNELS = 42
MASS_CHANNELS = 41
CONDITION_CHANNELS = SEMANTIC_CHANNELS + MASS_CHANNELS
MASS_LOG_MAX_G = 2000.0


def build_condition(mask: np.ndarray,
                    mass_by_class_g: dict[int, float]) -> np.ndarray:
    """Build semantic and class-total mass conditioning channels."""
    labels = np.asarray(mask, dtype=np.int64)
    if labels.ndim != 2 or labels.min(initial=0) < 0 or labels.max(initial=0) > 41:
        raise ValueError("condition mask must contain WED IDs 0..41")
    height, width = labels.shape
    semantic = np.eye(SEMANTIC_CHANNELS, dtype=np.float32)[labels]
    masses = np.zeros((height, width, MASS_CHANNELS), dtype=np.float32)
    for class_id, grams in mass_by_class_g.items():
        if not 1 <= int(class_id) <= MASS_CHANNELS:
            raise ValueError(f"mass condition class id outside WED IDs: {class_id}")
        if grams < 0 or not np.isfinite(grams):
            raise ValueError(f"mass condition must be finite and non-negative: {grams}")
        encoded = np.log1p(min(float(grams), MASS_LOG_MAX_G)) / np.log1p(MASS_LOG_MAX_G)
        masses[:, :, int(class_id) - 1] = encoded
    return np.concatenate([semantic, masses], axis=2)


class WedSemanticPairs(Dataset):
    def __init__(self, manifest: Path, data_root: Path):
        self.data_root = data_root
        manifest_rows = read_wed_train_manifest(manifest)
        self.rows = eligible_wed_train_rows(manifest_rows)
        if not self.rows:
            raise ValueError("No WED TRAIN image/mask pairs found")
        self.rows = [row for row in self.rows if (data_root / row["image"]).is_file()
                     and (data_root / row["mask"]).is_file()]
        if not self.rows:
            raise FileNotFoundError("WED TRAIN image/mask files are unavailable")
        group_counts = Counter(self.group_id(row) for row in self.rows)
        class_groups: dict[str, set[str]] = {}
        for row in self.rows:
            group = self.group_id(row)
            for dish in row.get("dishes", []):
                class_groups.setdefault(str(dish["name"]), set()).add(group)
        class_frequency = {name: max(len(groups), 1) for name, groups in class_groups.items()}
        self.sample_weights = []
        for row in self.rows:
            group = self.group_id(row)
            classes = [str(dish["name"]) for dish in row.get("dishes", [])]
            inverse = [1.0 / class_frequency[name] for name in classes if name in class_frequency]
            self.sample_weights.append((sum(inverse) / max(len(inverse), 1)) / group_counts[group])

    @staticmethod
    def group_id(row: dict) -> str:
        return f"{row.get('date_key', row.get('date'))}:{row.get('set')}"

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows[index]
        rgb = cv2.cvtColor(cv2.imread(str(self.data_root / row["image"])), cv2.COLOR_BGR2RGB)
        mask = cv2.imread(str(self.data_root / row["mask"]), cv2.IMREAD_GRAYSCALE)
        rgb = cv2.resize(rgb, TRAIN_SIZE, interpolation=cv2.INTER_AREA)
        mask = cv2.resize(mask, TRAIN_SIZE, interpolation=cv2.INTER_NEAREST)
        mask = np.clip(mask.astype(np.int64), 0, 41)
        onehot = np.eye(42, dtype=np.float32)[mask]
        mass_by_class = {
            int(dish["class_id"]): float(dish["weight_g"])
            for dish in row.get("dishes", [])
        }
        condition = build_condition(mask, mass_by_class)
        target = rgb.astype(np.float32) / 127.5 - 1.0
        if np.random.random() < 0.5:
            condition, target = condition[:, ::-1], target[:, ::-1]
        return (torch.from_numpy(condition.transpose(2, 0, 1).copy()),
                torch.from_numpy(target.transpose(2, 0, 1).copy()))


class SemanticGenerator(nn.Module):
    def __init__(self, condition_channels: int = CONDITION_CHANNELS):
        super().__init__()
        self.condition_channels = condition_channels
        self.d1 = nn.Sequential(nn.Conv2d(condition_channels, 64, 4, 2, 1), nn.LeakyReLU(.2, True))
        self.d2 = nn.Sequential(nn.Conv2d(64, 128, 4, 2, 1), nn.BatchNorm2d(128), nn.LeakyReLU(.2, True))
        self.d3 = nn.Sequential(nn.Conv2d(128, 256, 4, 2, 1), nn.BatchNorm2d(256), nn.LeakyReLU(.2, True))
        self.d4 = nn.Sequential(nn.Conv2d(256, 512, 4, 2, 1), nn.BatchNorm2d(512), nn.LeakyReLU(.2, True))
        self.u3 = nn.Sequential(nn.ConvTranspose2d(512, 256, 4, 2, 1), nn.BatchNorm2d(256), nn.ReLU(True))
        self.u2 = nn.Sequential(nn.ConvTranspose2d(512, 128, 4, 2, 1), nn.BatchNorm2d(128), nn.ReLU(True))
        self.u1 = nn.Sequential(nn.ConvTranspose2d(256, 64, 4, 2, 1), nn.BatchNorm2d(64), nn.ReLU(True))
        self.out = nn.Sequential(nn.ConvTranspose2d(128, 3, 4, 2, 1), nn.Tanh())

    def forward(self, condition):
        d1, d2, d3, d4 = self.d1(condition), None, None, None
        d2 = self.d2(d1)
        d3 = self.d3(d2)
        d4 = self.d4(d3)
        return self.out(torch.cat([self.u1(torch.cat([self.u2(torch.cat([self.u3(d4), d3], 1)), d2], 1)), d1], 1))


class PatchDiscriminator(nn.Module):
    def __init__(self, condition_channels: int = CONDITION_CHANNELS):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(condition_channels + 3, 64, 4, 2, 1), nn.LeakyReLU(.2, True),
            nn.Conv2d(64, 128, 4, 2, 1), nn.BatchNorm2d(128), nn.LeakyReLU(.2, True),
            nn.Conv2d(128, 256, 4, 2, 1), nn.BatchNorm2d(256), nn.LeakyReLU(.2, True),
            nn.Conv2d(256, 1, 3, 1, 1),
        )

    def forward(self, condition, image):
        return self.net(torch.cat([condition, image], dim=1))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def train_gan(manifest: Path, data_root: Path, output: Path, *, epochs: int = 100,
              batch_size: int = 4, learning_rate: float = 2e-4,
              workers: int = 4, device: str = "cuda", seed: int = 42) -> dict:
    if not torch.cuda.is_available() and device != "cpu":
        raise RuntimeError("No CUDA device is available; use the approved GPU runtime")
    device = torch.device(device)
    torch.manual_seed(seed)
    np.random.seed(seed)
    dataset = WedSemanticPairs(manifest, data_root)
    sampler = WeightedRandomSampler(dataset.sample_weights, len(dataset), replacement=True,
                                    generator=torch.Generator().manual_seed(seed))
    loader = DataLoader(dataset, batch_size=batch_size, sampler=sampler,
                        num_workers=workers, pin_memory=device.type == "cuda")
    generator = SemanticGenerator().to(device)
    discriminator = PatchDiscriminator().to(device)
    opt_g = torch.optim.Adam(generator.parameters(), lr=learning_rate, betas=(.5, .999))
    opt_d = torch.optim.Adam(discriminator.parameters(), lr=learning_rate, betas=(.5, .999))
    bce, l1 = nn.BCEWithLogitsLoss(), nn.L1Loss()
    generator.train(); discriminator.train()
    final_loss_g, final_loss_d = 0.0, 0.0
    for _epoch in range(epochs):
        for condition, real in loader:
            condition, real = condition.to(device), real.to(device)
            fake = generator(condition)
            opt_d.zero_grad(set_to_none=True)
            d_real = discriminator(condition, real)
            d_fake = discriminator(condition, fake.detach())
            loss_d = bce(d_real, torch.ones_like(d_real)) + bce(d_fake, torch.zeros_like(d_fake))
            loss_d.backward(); opt_d.step()
            opt_g.zero_grad(set_to_none=True)
            d_fake = discriminator(condition, fake)
            loss_g = bce(d_fake, torch.ones_like(d_fake)) + 100.0 * l1(fake, real)
            loss_g.backward(); opt_g.step()
            final_loss_g, final_loss_d = float(loss_g.detach()), float(loss_d.detach())
    output.parent.mkdir(parents=True, exist_ok=True)
    generator.eval().cpu()
    torch.save({"architecture": "semantic_unet_83ch_mass_conditioned_v2",
                "generator_state_dict": generator.state_dict(),
                "condition_channels": CONDITION_CHANNELS,
                "image_size": list(TRAIN_SIZE)}, output)
    digest = _sha256(output)
    train_rows = eligible_wed_train_rows(read_wed_train_manifest(manifest))
    provenance = {
        "method": "pix2pix_style_semantic_gan", "revision": "1",
        "sha256": digest,
        "license": "NutriSense project code; WED terms and release restrictions are recorded in docs/licenses.md",
        "training_data_disclosure": "WED paired image/label TRAIN records only",
        "training_source_splits": ["train"],
        "training_manifest_sha256": hashlib.sha256("\n".join(
            json.dumps(row, sort_keys=True) for row in train_rows).encode()).hexdigest(),
        "training_rows": len(dataset), "epochs": epochs, "batch_size": batch_size,
        "learning_rate": learning_rate, "image_size": list(TRAIN_SIZE),
        "seed": seed, "final_generator_loss": final_loss_g,
        "final_discriminator_loss": final_loss_d,
        "external_pretrained_weights": False,
    }
    Path(str(output) + ".provenance.json").write_text(json.dumps(provenance, indent=2) + "\n",
                                                         encoding="utf-8")
    return provenance
