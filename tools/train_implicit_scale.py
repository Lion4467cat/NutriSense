"""Train the card-free implicit scale and mass estimator.

Supervised by ArUco metric ground-truth with marker-dropout domain randomization.
Produces: data/implicit_scale_head.pt
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.implicit_scale import (
    DEFAULT_CHECKPOINT,
    ImplicitScaleHead,
    RESIZE,
)
from nutrisense_synth.measured import (
    load_aruco_supervised_examples,
    mask_out_marker,
)


def prepare_dataset(device: str | torch.device) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Prepare ArUco supervised images with card erasure and normalized targets."""
    examples = load_aruco_supervised_examples()
    if not examples:
        raise RuntimeError("No ArUco supervised examples found in dataset directory!")

    tf = transforms.Compose([
        transforms.Resize(RESIZE),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    images_list = []
    scale_targets_list = []
    mass_targets_list = []

    print(f"Preparing {len(examples)} ArUco captures with marker-dropout randomization...")
    for ex in examples:
        img = cv2.imread(str(ex.image_path))
        if img is None:
            continue
        h, w = img.shape[:2]
        max_dim = max(h, w)

        # 1. Image with card digitally erased
        masked_img = mask_out_marker(img, ex.marker_corners_px, expansion=2.5)

        # Normalized scale at 224px reference
        s_224 = ex.cm_per_px * (max_dim / 224.0)
        d_scale = 0.1152  # Calibrated MoGe-2 depth scale factor
        mass_g = ex.ground_truth_total_g

        # Add both original (for invariance) and marker-erased versions
        for variant in (masked_img, img):
            rgb = Image.fromarray(variant[:, :, ::-1])
            images_list.append(tf(rgb))
            scale_targets_list.append([math.log(s_224), math.log(d_scale)])
            mass_targets_list.append([math.log(mass_g)])

    images_t = torch.stack(images_list).to(device)
    scale_targets_t = torch.tensor(scale_targets_list, dtype=torch.float32, device=device)
    mass_targets_t = torch.tensor(mass_targets_list, dtype=torch.float32, device=device)
    return images_t, scale_targets_t, mass_targets_t


def train(epochs: int = 50, lr: float = 1e-3, out_path: Path = DEFAULT_CHECKPOINT) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training ImplicitScaleHead on {device} for {epochs} epochs...")

    images_t, scale_targets_t, mass_targets_t = prepare_dataset(device)
    n_samples = images_t.shape[0]
    print(f"Prepared {n_samples} training windows (paired original and marker-erased).")

    model = ImplicitScaleHead(pretrained=True).to(device)
    model.train()

    optimizer = torch.optim.AdamW(
        list(model.scale_mlp.parameters()) + list(model.mass_mlp.parameters()),
        lr=lr,
        weight_decay=1e-4,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.SmoothL1Loss()

    for epoch in range(1, epochs + 1):
        optimizer.zero_grad()
        scale_pred, mass_pred = model(images_t)
        loss_scale = criterion(scale_pred, scale_targets_t)
        loss_mass = criterion(mass_pred, mass_targets_t)
        loss = loss_scale + 0.5 * loss_mass
        loss.backward()
        optimizer.step()
        scheduler.step()

        if epoch % 10 == 0 or epoch == epochs:
            with torch.no_grad():
                scale_mae = (torch.exp(scale_pred[:, 0]) - torch.exp(scale_targets_t[:, 0])).abs().mean().item()
                mass_mape = ((torch.exp(mass_pred[:, 0]) - torch.exp(mass_targets_t[:, 0])).abs() / torch.exp(mass_targets_t[:, 0])).mean().item() * 100.0
            print(f"Epoch {epoch:2d}/{epochs} | Loss: {loss.item():.4f} | Scale MAE (224px): {scale_mae:.4f} cm/px | Mass MAPE: {mass_mape:.1f}%")

    model.eval()
    meta = {
        "epochs": epochs,
        "n_samples": n_samples,
        "final_loss": float(loss.item()),
        "scale_mae_224": float(scale_mae),
        "mass_mape": float(mass_mape),
    }
    model.save(out_path, meta=meta)
    print(f"Successfully saved implicit scale checkpoint to: {out_path}")


if __name__ == "__main__":
    train()
