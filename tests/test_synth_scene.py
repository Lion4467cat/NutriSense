from __future__ import annotations

import numpy as np

from nutrisense_synth.quality import check_card_pair
from nutrisense_synth.quality import check_scene
from nutrisense_synth.scene import build_class_scene, build_thali_scene, render_card_pair


def test_rendered_card_pair_keeps_scene_fixed() -> None:
    cfg = build_class_scene(34, "steamed-rice", 80.0, 0.85, seed=17,
                            size=(320, 240))
    present, absent = render_card_pair(cfg)
    assert all(item.passed for item in check_card_pair(present, absent))
    assert present["grams_gt"] == absent["grams_gt"]


def test_class_scene_uses_explicit_mass_inputs() -> None:
    cfg = build_class_scene(34, "steamed-rice", 80.0, 0.85, seed=1,
                            card_present=False, size=(320, 240))
    assert cfg["food"]["grams"] == 80.0
    assert cfg["food"]["density_g_ml"] == 0.85
    assert cfg["anchor"]["card"] is False


def test_renderer_scene_exports_physical_geometry_and_class_shape_prior() -> None:
    cfg = build_class_scene(34, "steamed-rice", 80.0, 0.85, seed=9,
                            size=(320, 240), appearance_profile={
                                "base_rgb": [180, 160, 130], "texture_amplitude": .2})
    scene, _ = render_card_pair(cfg)
    assert cfg["shape_assumption"] == "loose_pile"
    assert scene["volume_ml_gt"]["steamed-rice"] > 0
    assert np.isclose(scene["grams_gt"]["steamed-rice"],
                      scene["volume_ml_gt"]["steamed-rice"]
                      * scene["density_g_ml_by_component"]["steamed-rice"])
    assert scene["surface_xyz_world_mm"].shape == (240, 320, 3)
    assert all(item.passed for item in check_scene(scene))


def test_thali_scene_uses_separate_component_labels_without_spike_mounds() -> None:
    scene_cfg = build_thali_scene([
        {"class_id": 34, "grams": 120, "density_g_ml": .75},
        {"class_id": 33, "grams": 80, "density_g_ml": 1.0},
        {"class_id": 32, "grams": 30, "density_g_ml": .5},
    ], seed=18, size=(320, 240))
    scene, _ = render_card_pair(scene_cfg)
    assert scene_cfg["food"]["layout"] == "sectors"
    assert set(np.unique(scene["comp_ids"])) == {0, 1, 2, 3}
    assert all(item.passed for item in check_scene(scene))
