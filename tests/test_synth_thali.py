from __future__ import annotations

from nutrisense_synth.quality import check_scene
from nutrisense_synth.scene import build_thali_scene, render_card_pair


def test_thali_has_individual_component_mass_and_paired_scene() -> None:
    cfg = build_thali_scene([
        {"class_id": 34, "grams": 100.0},
        {"class_id": 33, "grams": 80.0},
    ], seed=41, size=(320, 240))
    present, absent = render_card_pair(cfg)
    assert all(item.passed for item in check_scene(present))
    assert set(present["grams_gt"]) == {"steamed-rice", "sambar"}
    assert abs(sum(present["grams_gt"].values()) - present["grams_gt_total"]) < 1e-6
    assert present["grams_gt"] == absent["grams_gt"]
    component_ids = set(present["comp_ids"].ravel()) - {0}
    assert component_ids == {1, 2}
    assert all((present["comp_ids"] == component_id).any() for component_id in component_ids)
