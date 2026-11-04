"""WED-native 41-class semantic food segmentation model.

The label map is background=0 and WED food classes=1..41. This module emits
pixel-class logits; it does not claim instance-level supervision.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from torch import nn

N_CLASSES = 42
INPUT_HEIGHT = 1024
INPUT_WIDTH = 768
IMAGE_MEAN = (0.485, 0.456, 0.406)
IMAGE_STD = (0.229, 0.224, 0.225)
ARCHITECTURE = "deeplabv3_resnet50_imagenet_wed42"


def build_model(*, pretrained_backbone: bool = True) -> nn.Module:
    """Build DeepLabV3 with an ImageNet ResNet-50 and 42 WED output classes."""
    from torchvision.models import ResNet50_Weights
    from torchvision.models.segmentation import deeplabv3_resnet50

    model = deeplabv3_resnet50(
        weights=None,
        weights_backbone=(ResNet50_Weights.IMAGENET1K_V2
                          if pretrained_backbone else None),
        num_classes=N_CLASSES,
        aux_loss=None,
    )
    if model.classifier[-1].out_channels != N_CLASSES:
        raise RuntimeError("WED classifier head must have 42 output channels")
    return model


def prepare_image(image_bgr: np.ndarray,
                  size: tuple[int, int] = (INPUT_WIDTH, INPUT_HEIGHT)
                  ) -> torch.Tensor:
    """Resize BGR input to model size and return normalized RGB CHW tensor."""
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError("expected an HxWx3 BGR image")
    image = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)
    tensor = torch.from_numpy(np.ascontiguousarray(image)).permute(2, 0, 1)
    tensor = tensor.float().div_(255.0)
    mean = torch.tensor(IMAGE_MEAN, dtype=tensor.dtype)[:, None, None]
    std = torch.tensor(IMAGE_STD, dtype=tensor.dtype)[:, None, None]
    return (tensor - mean) / std


def predict_labels(model: nn.Module, image_bgr: np.ndarray,
                   device: str | torch.device,
                   size: tuple[int, int] = (INPUT_WIDTH, INPUT_HEIGHT)
                   ) -> np.ndarray:
    """Return an HxW uint8 WED semantic prediction in original image size."""
    model.eval()
    h, w = image_bgr.shape[:2]
    image = prepare_image(image_bgr, size).unsqueeze(0).to(device)
    with torch.inference_mode():
        logits = model(image)["out"]
        logits = torch.nn.functional.interpolate(
            logits, size=(h, w), mode="bilinear", align_corners=False)
        labels = logits.argmax(dim=1)[0]
    return labels.byte().cpu().numpy()


def load_checkpoint(path: str | Path, *, device: str | torch.device
                    ) -> tuple[nn.Module, dict[str, Any]]:
    """Load a saved WED segmentation model and its reproducibility metadata."""
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    if checkpoint.get("architecture") != ARCHITECTURE:
        raise ValueError("checkpoint architecture does not match WED segmenter")
    if int(checkpoint.get("n_classes", -1)) != N_CLASSES:
        raise ValueError("checkpoint does not contain the 42 WED labels")
    model = build_model(pretrained_backbone=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.to(device).eval()
    return model, checkpoint
