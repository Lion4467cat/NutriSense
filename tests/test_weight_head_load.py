"""Regression: WeightHead.load must restore the SAME pretrained encoder the
head was trained against. The head is trained on frozen *pretrained*
features; a load path that rebuilds the backbone without pretrained weights
feeds untrained features to the head and produces kilogram-scale garbage
(~870 g MAE on the WED test split instead of ~25 g).

Guards (STAGE 1C + ledger 002):
  * the deployed encoder's pretrained weights match their canonical source —
    checksummed per encoder (ResNet-50 IMAGENET1K_V2 conv1, DINOv2-S first
    layer), so a `pretrained=False` rebuild fails loudly,
  * ResNet: encoder BN buffers equal stock ImageNet values (option A — the
    frozen encoder is pinned to eval() during training; train-mode BN drift
    is what used to cost ~4 g between in-process and deployed MAE),
    DINOv2: NO BatchNorm buffers exist (ViT — drift enters through dropout,
    frozen by the same eval() pin),
  * a golden MAE on a fixed 30-view VAL subset via the deployable path.

Every test in this module loads a model and carries the `gpu` marker; the
model and the reference are built once per session by fixtures. All tests
skip when the deployable encoder's pretrained weights are not already
cached — no downloads in CI (HF_HUB_OFFLINE stays honest here).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import torch

from models.weight_head import DINOV2_ID, WeightHead

pytestmark = pytest.mark.gpu

_ROOT = Path(__file__).resolve().parents[1]
CKPT = _ROOT / "data" / "weight_head.pt"
_RESNET50_CACHE = (Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
                   / "resnet50-11ad3fa6.pth")
_DINOV2_CACHE = (Path.home() / ".cache" / "huggingface" / "hub"
                 / "models--facebook--dinov2-small")


def _encoder_cache_present(encoder_id: str) -> bool:
    if encoder_id == "dinov2":
        return _DINOV2_CACHE.is_dir() and any(_DINOV2_CACHE.rglob("*.safetensors"))
    return _RESNET50_CACHE.is_file()


def _checkpoints_encoder_id() -> str:
    import json as _json
    try:
        ckpt = torch.load(CKPT, map_location="cpu", weights_only=True)
        eid = ckpt.get("encoder_id", "resnet50")
        _json.dumps(eid)  # sanity: str-able
        return eid
    except Exception:
        return "resnet50"


_needs_artifacts = pytest.mark.skipif(
    not CKPT.is_file() or not _encoder_cache_present(_checkpoints_encoder_id()),
    reason="weight_head.pt or the deployed encoder's pretrained weights missing from cache")


def _sha(t) -> str:
    return hashlib.sha256(t.detach().cpu().numpy().tobytes()).hexdigest()


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


@pytest.fixture(scope="session")
def head() -> WeightHead:
    return WeightHead.load(CKPT, device=_device())


@pytest.fixture(scope="session")
def pretrained_ref(head):
    """The canonical pretrained encoder for whatever the checkpoint deploys."""
    if head.encoder_id == "dinov2":
        from transformers import AutoModel
        return AutoModel.from_pretrained("facebook/dinov2-small")
    from torchvision import models
    return models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)


@_needs_artifacts
def test_load_restores_pretrained_encoder(head, pretrained_ref) -> None:
    if head.encoder_id == "dinov2":
        deployed = head.encoder.embeddings.cls_token
        reference = pretrained_ref.embeddings.cls_token
    else:
        deployed = head.encoder[0].weight
        reference = pretrained_ref.conv1.weight
    assert _sha(deployed) == _sha(reference), (
        "loaded encoder weights do not match their pretrained source — "
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
def test_encoder_buffers_match_stock_pretrained(head, pretrained_ref) -> None:
    if head.encoder_id == "dinov2":
        # ViT: no BatchNorm buffers exist; the eval() pin governs dropout.
        drifted = [k for k, _ in head.encoder.state_dict().items()
                   if k.endswith("running_mean")]
        assert not drifted, f"unexpected BN buffers in {head.encoder_id}: {drifted[:3]}"
        # frozen ViT weights identical to the pretrained source (spot-check
        # two spatially-meaningful tensors beyond the cls embedding guard)
        for dep, ref in (
            (head.encoder.encoder.layer[0].attention.attention.query.weight,
             pretrained_ref.encoder.layer[0].attention.attention.query.weight),
            (head.encoder.layernorm.weight,
             pretrained_ref.layernorm.weight),
        ):
            assert _sha(dep) == _sha(ref), "frozen ViT drifted from pretrained"
        return
    ref_enc = torch.nn.Sequential(*list(pretrained_ref.children())[:-2])
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


# Golden 10.70 g: first 30 rows of the seed-42 VAL carve (manifest order,
# 6 plates), measured 2026-10-15 through the deployable path (WeightHead.load)
# from the ledger-002 DINOv2-S checkpoint deployed 2026-10-15 (full 108-view
# val MAE 15.03 g; DEV deployable 15.034 g, paired-vs-ledger-001 CI
# [-6.23, -4.23] in docs/ledger/002-dinov2-encoder.md). Re-pinning documented
# there: the encoder CHANGED ON PURPOSE (lever b keep). The test exists to
# catch corruption of THIS deployable checkpoint, not to forbid retraining.
# Re-derive with tools.train_weight_head helpers; the WED test split is never
# read here.
_GOLDEN_VAL30_MAE_G = 10.70


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
