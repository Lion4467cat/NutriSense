"""Regression: WeightHead.load must restore the pretrained IMAGENET1K_V2
encoder. The head was trained on frozen *pretrained* features; the old
load path (pretrained=False) fed untrained features to the head and produced
kilogram-scale garbage (~870 g MAE on the WED test split instead of ~25 g).

Both tests skip when the head checkpoint or the cached torchvision
resnet50 IMAGENET1K_V2 weights are missing — no downloads in CI, and the
gpu pytest marker does not exist yet, so a plain skipif guard is used.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import torch

from models.weight_head import WeightHead

_ROOT = Path(__file__).resolve().parents[1]
CKPT = _ROOT / "data" / "weight_head.pt"
_RESNET50_CACHE = (Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
                   / "resnet50-11ad3fa6.pth")

_needs_artifacts = pytest.mark.skipif(
    not CKPT.is_file() or not _RESNET50_CACHE.is_file(),
    reason="weight_head.pt or cached resnet50 IMAGENET1K_V2 weights missing")


def _sha(t: torch.Tensor) -> str:
    return hashlib.sha256(t.detach().cpu().numpy().tobytes()).hexdigest()


@_needs_artifacts
def test_load_restores_pretrained_encoder() -> None:
    from torchvision import models
    ref = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
    model = WeightHead.load(CKPT, device="cpu")
    assert _sha(model.encoder[0].weight) == _sha(ref.conv1.weight), (
        "loaded encoder conv1 does not match IMAGENET1K_V2 weights — "
        "WeightHead.load rebuilt the backbone without pretrained=True")


@_needs_artifacts
def test_loaded_head_predicts_grams_not_kilograms() -> None:
    torch.manual_seed(0)
    model = WeightHead.load(CKPT, device="cpu")
    x = torch.randn(1, 3, 224, 224)
    feats = model.encode(x)
    rois = torch.tensor([[0.0, 2.0, 2.0, 26.0, 26.0]])
    with torch.no_grad():
        pred = float(model(feats, rois)[0, 0])
    assert 0.0 < pred < 5000.0, f"implausible prediction {pred:.1f} g (kg-scale garbage?)"
