"""Segmentation architectures used by the controlled WED study."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from torch import nn

from models.wed_semantic_segmenter import N_CLASSES, build_model as build_deeplabv3

SEGFORMER_ID = "nvidia/segformer-b0-finetuned-ade-512-512"
DEEP_LAB_PLUS_ID = "deeplabv3plus_resnet50_imagenet_v2"


class _ConvBNReLU(nn.Sequential):
    def __init__(self, in_channels: int, out_channels: int,
                 kernel_size: int, *, dilation: int = 1):
        padding = dilation * (kernel_size // 2)
        super().__init__(
            nn.Conv2d(in_channels, out_channels, kernel_size,
                      padding=padding, dilation=dilation, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )


class _ASPP(nn.Module):
    def __init__(self, channels: int, out_channels: int = 256):
        super().__init__()
        self.branches = nn.ModuleList([
            _ConvBNReLU(channels, out_channels, 1),
            _ConvBNReLU(channels, out_channels, 3, dilation=6),
            _ConvBNReLU(channels, out_channels, 3, dilation=12),
            _ConvBNReLU(channels, out_channels, 3, dilation=18),
        ])
        self.pool = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(channels, out_channels, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )
        self.project = _ConvBNReLU(out_channels * 5, out_channels, 1)
        self.dropout = nn.Dropout2d(0.1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        pooled = self.pool(x)
        pooled = F.interpolate(pooled, size=x.shape[-2:], mode="bilinear",
                               align_corners=False)
        return self.dropout(self.project(torch.cat(
            [branch(x) for branch in self.branches] + [pooled], dim=1)))


class _DeepLabV3Plus(nn.Module):
    def __init__(self, *, pretrained: bool):
        super().__init__()
        from torchvision.models import ResNet50_Weights, resnet50

        weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
        network = resnet50(weights=weights)
        self.stem = nn.Sequential(network.conv1, network.bn1, network.relu,
                                  network.maxpool)
        self.layer1 = network.layer1
        self.layer2 = network.layer2
        self.layer3 = network.layer3
        self.layer4 = network.layer4
        self.aspp = _ASPP(2048, 256)
        self.low_level = _ConvBNReLU(512, 48, 1)
        self.decoder = nn.Sequential(
            _ConvBNReLU(304, 256, 3),
            nn.Dropout2d(0.1),
            _ConvBNReLU(256, 256, 3),
        )
        self.classifier = nn.Conv2d(256, N_CLASSES, kernel_size=1)
        self.pretrained_backbone = pretrained

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        output_size = x.shape[-2:]
        x = self.stem(x)
        x = self.layer1(x)
        low = self.layer2(x)
        high = self.layer4(self.layer3(low))
        high = self.aspp(high)
        high = F.interpolate(high, size=low.shape[-2:], mode="bilinear",
                             align_corners=False)
        decoded = self.decoder(torch.cat([high, self.low_level(low)], dim=1))
        logits = self.classifier(decoded)
        logits = F.interpolate(logits, size=output_size, mode="bilinear",
                               align_corners=False)
        return {"out": logits}


class _SegFormer(nn.Module):
    def __init__(self, *, pretrained: bool, model_id: str = SEGFORMER_ID):
        super().__init__()
        from transformers import SegformerConfig, SegformerForSemanticSegmentation

        if pretrained:
            self.model = SegformerForSemanticSegmentation.from_pretrained(
                model_id, num_labels=N_CLASSES, ignore_mismatched_sizes=True)
        else:
            config = SegformerConfig(num_labels=N_CLASSES)
            self.model = SegformerForSemanticSegmentation(config)
        self.pretrained = pretrained
        self.model_id = model_id

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        logits = self.model(pixel_values=x).logits
        logits = F.interpolate(logits, size=x.shape[-2:], mode="bilinear",
                               align_corners=False)
        return {"out": logits}


def build_variant(architecture: str, *, pretrained: bool = True) -> nn.Module:
    if architecture == "deeplabv3":
        return build_deeplabv3(pretrained_backbone=pretrained)
    if architecture == "deeplabv3plus":
        return _DeepLabV3Plus(pretrained=pretrained)
    if architecture == "segformer_b0":
        return _SegFormer(pretrained=pretrained)
    raise ValueError(f"unknown segmentation architecture: {architecture}")


def pretrained_weight_path(architecture: str) -> Path | None:
    """Return a cached public encoder/model weight path when known."""
    if architecture in {"deeplabv3", "deeplabv3plus"}:
        from torchvision.models import ResNet50_Weights
        from torch.hub import get_dir
        return Path(get_dir()) / "checkpoints" / Path(
            ResNet50_Weights.IMAGENET1K_V2.url).name
    if architecture == "segformer_b0":
        from huggingface_hub import try_to_load_from_cache
        cached = try_to_load_from_cache(SEGFORMER_ID, "model.safetensors")
        if isinstance(cached, str):
            return Path(cached)
    return None


def predict_variant(model: nn.Module, image_bgr, *, device: torch.device,
                    width: int, height: int) -> torch.Tensor:
    """Normalize/resize one BGR image and return input-resolution class logits."""
    import cv2
    import numpy as np

    from models.wed_semantic_segmenter import IMAGE_MEAN, IMAGE_STD

    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    rgb = cv2.resize(rgb, (width, height), interpolation=cv2.INTER_LINEAR)
    array = rgb.astype(np.float32) / 255.0
    mean = np.asarray(IMAGE_MEAN, dtype=np.float32)[None, None, :]
    std = np.asarray(IMAGE_STD, dtype=np.float32)[None, None, :]
    tensor = torch.from_numpy(np.ascontiguousarray(
        ((array - mean) / std).transpose(2, 0, 1))).unsqueeze(0).to(device)
    model.eval()
    with torch.inference_mode():
        output = model(tensor)["out"]
    return output[0]
