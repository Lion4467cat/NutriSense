from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import cv2
import pytest

from nutrisense_synth.appearance import (
    compute_plate_relative_geometry,
    randomize_isp_lighting,
)
from nutrisense_synth.corpus import auditable_cutmix


def test_randomize_isp_lighting_basic() -> None:
    img = np.full((64, 64, 3), 128, dtype=np.uint8)
    out, meta = randomize_isp_lighting(img, seed=42)
    assert out.shape == img.shape
    assert out.dtype == np.uint8
    assert 2800.0 <= meta["temperature_k"] <= 6500.0
    assert 1.0 <= meta["clahe_clip_limit"] <= 3.0
    assert 0.0 <= meta["specular_strength"] <= 0.35
    assert len(meta["wb_gains_rgb"]) == 3


def test_randomize_isp_lighting_deterministic() -> None:
    img = np.full((32, 32, 3), 100, dtype=np.uint8)
    out1, meta1 = randomize_isp_lighting(img, temperature_k=3200.0, clahe_clip_limit=2.0, specular_strength=0.2, seed=123)
    out2, meta2 = randomize_isp_lighting(img, temperature_k=3200.0, clahe_clip_limit=2.0, specular_strength=0.2, seed=123)
    np.testing.assert_array_equal(out1, out2)
    assert meta1 == meta2


def test_randomize_isp_lighting_rejects_invalid_shape() -> None:
    invalid = np.full((32, 32), 100, dtype=np.uint8)
    with pytest.raises(ValueError, match="Expected BGR image"):
        randomize_isp_lighting(invalid)


def test_compute_plate_relative_geometry_circular_and_elongated() -> None:
    plate_mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(plate_mask, (50, 50), 40, 1, -1)  # Area ~ 5026 px

    # Circular item at center
    item_mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.circle(item_mask, (50, 50), 20, 1, -1)  # Area ~ 1256 px

    geom = compute_plate_relative_geometry(item_mask, plate_mask)
    assert 0.20 <= geom["area_share_of_plate"] <= 0.30
    assert 0.90 <= geom["hull_fill_ratio"] <= 1.05
    assert 1.0 <= geom["aspect_ratio"] <= 1.25

    # Elongated item
    elong_mask = np.zeros((100, 100), dtype=np.uint8)
    cv2.rectangle(elong_mask, (20, 45), (80, 55), 1, -1)
    geom_elong = compute_plate_relative_geometry(elong_mask, plate_mask)
    assert geom_elong["aspect_ratio"] >= 4.0


def test_compute_plate_relative_geometry_empty() -> None:
    empty = np.zeros((50, 50), dtype=np.uint8)
    geom = compute_plate_relative_geometry(empty)
    assert geom["area_share_of_plate"] == 0.0
    assert geom["item_area_px"] == 0.0
    assert geom["hull_fill_ratio"] == 1.0
    assert geom["aspect_ratio"] == 1.0


def test_auditable_cutmix_rejects_non_train(tmp_path: Path) -> None:
    row_a = {"split": "train", "date_key": "20260101", "set": "set1", "image": "a.jpg"}
    row_b = {"split": "dev", "date_key": "20260102", "set": "set1", "image": "b.jpg"}
    with pytest.raises(ValueError, match="auditable_cutmix accepts WED TRAIN rows only"):
        auditable_cutmix(row_a, row_b, tmp_path)


def test_auditable_cutmix_roundtrip(tmp_path: Path) -> None:
    dataset_root = tmp_path / "wed"
    dataset_root.mkdir()

    img_a = np.full((40, 40, 3), 100, dtype=np.uint8)
    mask_a = np.ones((40, 40), dtype=np.uint8) * 34  # steamed-rice
    cv2.imwrite(str(dataset_root / "a.png"), img_a)
    cv2.imwrite(str(dataset_root / "a_mask.png"), mask_a)

    img_b = np.full((40, 40, 3), 160, dtype=np.uint8)
    mask_b = np.ones((40, 40), dtype=np.uint8) * 12  # sambar
    cv2.imwrite(str(dataset_root / "b.png"), img_b)
    cv2.imwrite(str(dataset_root / "b_mask.png"), mask_b)

    row_a = {
        "split": "train", "date_key": "20260101", "set": "set1",
        "image": "a.png", "mask": "a_mask.png",
        "dishes": [{"class_id": 34, "name": "steamed-rice", "weight_g": 200.0}],
    }
    row_b = {
        "split": "train", "date_key": "20260102", "set": "set1",
        "image": "b.png", "mask": "b_mask.png",
        "dishes": [{"class_id": 12, "name": "sambar", "weight_g": 150.0}],
    }

    out_dir = tmp_path / "cutmix_out"
    res = auditable_cutmix(row_a, row_b, dataset_root, output_dir=out_dir, seed=42)

    assert "source_a" in res and "source_b" in res
    assert res["source_a"]["source_split"] == "train"
    assert res["source_b"]["source_split"] == "train"
    assert res["pasted_class_id"] == 12
    assert len(res["composite_dishes"]) == 2
    assert Path(res["output_image_path"]).is_file()
    assert Path(res["output_mask_path"]).is_file()
