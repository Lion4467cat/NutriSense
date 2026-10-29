"""Golden guard for the encoder feature cache (spec 002 decision 10).

The frozen encoder's features are a pure function of (image, seed) — the
encoder never trains and stays pinned to eval() — so the training tool
prepares them once (one augmented window per view at feature-prep time)
and reuses them for every epoch. Three paths must therefore produce
BITWISE identical head weights under the same seed:

  build  — cache directory empty: features prepared live and written once,
  reuse  — cache file present: features loaded from disk (no rewrite),
  live   — disk cache disabled ("none"): features prepared in memory.

Each path runs the full tool pipeline (run_training) on a small view slice
(--limit) with the ResNet-50 encoder from the local torch-hub cache — no
downloads — and skips the locked test split entirely (--skip-test). All
artifacts land in tmp_path.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest
import torch

from tools.train_weight_head import run_training

pytestmark = pytest.mark.gpu

_ROOT = Path(__file__).resolve().parents[1]
_RESNET50_CACHE = (Path.home() / ".cache" / "torch" / "hub" / "checkpoints"
                   / "resnet50-11ad3fa6.pth")

_resnet_cached = pytest.mark.skipif(
    not _RESNET50_CACHE.is_file(),
    reason="resnet50 ImageNet weights missing from the local torch hub cache")
_dataset_present = pytest.mark.skipif(
    not (_ROOT / "data" / "wed" / "train").is_dir(),
    reason="WED train images not present (git-ignored dataset)")


def _args(out_dir: Path, features_cache: str | None) -> argparse.Namespace:
    return argparse.Namespace(
        epochs=2, batch=4, encoder="resnet50", lr=1e-3, seed=42,
        val_frac=0.10, workers=0, skip_test=True,
        train_aug="ledger001",  # mirrors the CLI default (tools.train_weight_head)
        out=str(out_dir / "weight_head.pt"),
        sigma_out=str(out_dir / "weight_head_sigma.yaml"),
        report_out=str(out_dir / "weight_head_train.json"),
        features_cache=features_cache,
        limit=24,
    )


@_resnet_cached
@_dataset_present
def test_cached_reused_and_live_training_identical_weights(tmp_path) -> None:
    cache_dir = tmp_path / "features"

    built = run_training(_args(tmp_path / "built", str(cache_dir)))
    assert built["meta"]["feature_cache"]["mode"] == "build"
    cache_file = next(cache_dir.glob("*.pt"))
    cache_mtime = cache_file.stat().st_mtime

    reused = run_training(_args(tmp_path / "reused", str(cache_dir)))
    assert reused["meta"]["feature_cache"]["mode"] == "reuse"
    assert cache_file.stat().st_mtime == cache_mtime, "reuse rewrote the cache"

    live = run_training(_args(tmp_path / "live", "none"))
    assert live["meta"]["feature_cache"]["mode"] == "live"

    heads = []
    for sub in ("built", "reused", "live"):
        ckpt = torch.load(tmp_path / sub / "weight_head.pt",
                          map_location="cpu", weights_only=True)
        heads.append(ckpt["head_mlp"])
    keys = heads[0].keys()
    for k in keys:
        assert torch.equal(heads[0][k], heads[1][k]), (
            f"reuse path diverged from build path on '{k}'")
        assert torch.equal(heads[0][k], heads[2][k]), (
            f"live path diverged from build path on '{k}'")
