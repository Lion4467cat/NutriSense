from __future__ import annotations

import numpy as np
import pytest

from nutrisense_synth.methods.base import GenerationContext, restore_scene_owned_pixels
from nutrisense_synth.quality import check_card_pair


def test_card_pair_rejects_changed_food_geometry() -> None:
    base = {
        "image_rgb": np.zeros((8, 8, 3), dtype=np.uint8),
        "obj_ids": np.zeros((8, 8), dtype=np.uint8),
        "mask_food": np.zeros((8, 8), dtype=bool),
        "comp_ids": np.zeros((8, 8), dtype=np.uint8),
        "grams_gt": {"rice": 10.0},
        "camera": {"K": np.eye(3), "R_wc": np.eye(3), "C": np.zeros(3), "size": (8, 8)},
        "cfg": {"anchor": {"card": True, "card_center": (1, 1)}},
    }
    absent = {**base, "cfg": {"anchor": {"card": False, "card_center": (1, 1)}}}
    absent["mask_food"] = np.ones((8, 8), dtype=bool)
    assert any(not result.passed for result in check_card_pair(base, absent))


def test_no_card_context_cannot_receive_marker_scale() -> None:
    with pytest.raises(ValueError, match="marker-derived"):
        GenerationContext("s1", 1, np.zeros((4, 4, 3), np.uint8),
                          np.zeros((4, 4), np.uint8), np.ones((4, 4), np.float32),
                          np.zeros((4, 4), bool), np.ones((4, 4), bool),
                          {"marker_scale": 1.0})


def test_appearance_can_change_only_food_pixels() -> None:
    condition = np.zeros((4, 4, 3), np.uint8)
    food = np.zeros((4, 4), bool); food[1:3, 1:3] = True
    context = GenerationContext("s1", 1, condition, np.ones((4, 4), np.uint8),
                                np.ones((4, 4), np.float32), np.zeros((4, 4), bool),
                                food, {})
    output = restore_scene_owned_pixels(np.full_like(condition, 255), context)
    assert np.all(output[~food] == 0)
    assert np.all(output[food] == 255)
