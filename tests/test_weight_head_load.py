"""Regression: WeightHead.load must restore the pretrained IMAGENET1K_V2
encoder. The head was trained on frozen *pretrained* features; the old
load path (pretrained=False) fed untrained features to the head and produced
kilogram-scale garbage (~870 g MAE on the WED test split instead of ~25 g).

STAGE 1C adds two guards on top of the checksum/plausible-range pair:
  * encoder BN buffers must equal stock ImageNet values (option A — the
    frozen encoder is pinned to eval() during training; train-mode BN
    drift is what used to cost ~4 g between in-process and deployed MAE),
  * a golden MAE on a fixed 30-view VAL subset via the deployable path.

Every test in this module loads a model and carries the `gpu` marker; the
model and the ImageNet reference are built once per session by fixtures.
All tests skip when the head checkpoint or the cached torchvision
resnet50 IMAGENET1K_V2 weights are missing — no downloads in CI.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import torch

from models.weight_head import WeightHead

pytestmark = pytest.mark.gpu

_ROOT = Path(__file__).resolve().parents[1]
CKPT = _ROOT / "data" / "weight_head.pt"
_RESNET50_CACHE = (Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
                   / "resnet50-11ad3fa6.pth")

_needs_artifacts = pytest.mark.skipif(
    not CKPT.is_file() or not _RESNET50_CACHE.is_file(),
    reason="weight_head.pt or cached resnet50 IMAGENET1K_V2 weights missing")


def _sha(t: torch.Tensor) -> str:
    return hashlib.sha256(t.detach().cpu().numpy().tobytes()).hexdigest()


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@pytest.fixture(scope="session")
def head() -> WeightHead:
    return WeightHead.load(CKPT, device=_device())


@pytest.fixture(scope="session")
def imagenet_ref():
    from torchvision import models
    return models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)


@_needs_artifacts
def test_load_restores_pretrained_encoder(head, imagenet_ref) -> None:
    assert _sha(head.encoder[0].weight) == _sha(imagenet_ref.conv1.weight), (
        "loaded encoder conv1 does not match IMAGENET1K_V2 weights — "
        "WeightHead.load rebuilt the backbone without pretrained=True")


@_needs_artifacts
def test_loaded_head_predicts_grams_not_kilograms(head) -> None:
    torch.manual_seed(0)
    x = torch.randn(1, 3, 224, 224, device=_device())
    feats = head.encode(x)
    rois = torch.tensor([[0.0, 2.0, 2.0, 26.0, 26.0]], device=_device())
    with torch.no_grad():
        pred = float(head(feats, rois)[0, 0])
    assert 0.0 < pred < 5000.0, f"implausible prediction {pred:.1f} g (kg-scale garbage?)"


@_needs_artifacts
def test_encoder_bn_matches_stock_imagenet(head, imagenet_ref) -> None:
    ref_enc = torch.nn.Sequential(*list(imagenet_ref.children())[:-2])
    ref_sd = ref_enc.state_dict()
    enc_sd = {k: v.detach().cpu() for k, v in head.encoder.state_dict().items()}
    assert ref_sd.keys() == enc_sd.keys()
    bn_keys = [k for k in ref_sd
               if k.endswith(("running_mean", "running_var",
                              "num_batches_tracked"))]
    assert len(bn_keys) == 159  # 53 BatchNorm2d modules x 3 buffers
    drifted = [k for k in bn_keys if not torch.equal(ref_sd[k], enc_sd[k])]
    assert not drifted, (
        f"{len(drifted)} encoder BN buffers differ from stock ImageNet "
        f"({drifted[:3]}) — train-mode BN drift crept back into training?")


# Golden 16.21 g: first 30 rows of the seed-42 VAL carve (manifest order,
# 6 plates), measured 2026-10-11 through the deployable path (WeightHead.load)
# from the frozen-encoder-BN checkpoint deployed 2026-10-11 (full 108-view
# val MAE 20.30 g). Re-derive with tools.train_weight_head helpers; the WED
# test split is never read here.
_GOLDEN_VAL30_MAE_G = 16.21


@_needs_artifacts
def test_golden_val_subset_mae(head) -> None:
    import random

    import yaml
    from torch.utils.data import DataLoader

    from tools.train_weight_head import (WedPlates, collate, evaluate_mae,
                                         load_manifest, plate_key)

    rows = load_manifest("train")
    plates = sorted({plate_key(r) for r in rows})
    random.Random(42).shuffle(plates)
    val_plates = set(plates[: max(1, int(len(plates) * 0.10))])
    subset = [r for r in rows if plate_key(r) in val_plates][:30]
    assert len(subset) == 30

    cfg = yaml.safe_load((_ROOT / "data" / "wed_dishes.yaml").read_text())
    wed_root = Path(cfg["dataset"]["root"])
    if not wed_root.is_absolute():
        wed_root = _ROOT / wed_root
    loader = DataLoader(WedPlates(subset, wed_root, train=False),
                        batch_size=8, shuffle=False, collate_fn=collate,
                        num_workers=0)
    mae, _, _ = evaluate_mae(head, loader, device=_device())
    assert abs(mae - _GOLDEN_VAL30_MAE_G) <= 1.0, (
        f"golden val-subset MAE drifted: {mae:.2f} g "
        f"(golden {_GOLDEN_VAL30_MAE_G} g ± 1.0)")
