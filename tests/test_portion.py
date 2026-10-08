"""S3: portion estimation against synthetic ground truth."""
import numpy as np
import pytest
import yaml

from models.portion_estimator import estimate_portion
from models.scale_anchor import estimate_anchor
from tests.synth.scene import default_scene, render_scene

DISH = yaml.safe_load(open("data/menu.yaml"))["dishes"]["rice_sambar"]


def _vol_gt(scene):
    return scene["grams_gt_total"] / scene["cfg"]["food"]["density_g_ml"]


@pytest.fixture(scope="module")
def plate():
    return render_scene()


@pytest.fixture(scope="module")
def bowl():
    food = dict(default_scene()["food"])
    food["radius_mm"] = 70.0
    return render_scene({"vessel": "bowl", "food": food})


def _estimate(scene, dish=DISH, cfg=None, anchor=None):
    anchor = anchor if anchor is not None else estimate_anchor(scene["image_bgr"])
    return estimate_portion(
        scene["image_bgr"], scene["mask_food"], scene["depth_m"], anchor,
        {"K": scene["camera"]["K"]}, dish, cfg=cfg,
    )


def test_plate_volume_within_15pct(plate):
    res = _estimate(plate)
    assert res["base_method"] == "ring"
    assert abs(res["volume_ml"] - _vol_gt(plate)) / _vol_gt(plate) < 0.15


def test_plate_grams_consistent(plate):
    res = _estimate(plate)
    gt = plate["grams_gt_total"]
    assert abs(res["grams"] - gt) / gt < 0.15
    # grams = volume x density, components split by share
    assert res["grams"] == pytest.approx(res["volume_ml"] * res["density_eff"])
    assert sum(res["components_g"].values()) == pytest.approx(res["grams"])
    assert res["components_g"]["rice"] == pytest.approx(0.6 * res["grams"], rel=1e-6)


def test_plate_sigma_matches_plan_budget(plate):
    res = _estimate(plate)
    # plan feasibility: ring path ~+/-26% per-dish grams
    assert 0.18 <= res["sigma_grams_rel"] <= 0.40
    assert set(res["sigma_rel"]) == {"depth", "area", "base", "density"}


def test_bowl_volume_within_15pct(bowl):
    res = _estimate(bowl)
    assert res["base_method"] == "ring"
    assert abs(res["volume_ml"] - _vol_gt(bowl)) / _vol_gt(bowl) < 0.15


def test_prior_tier_volume_and_flags(plate):
    prior = {"method": "prior", "label": "prior", "cm_per_px": None,
             "interval": None, "H": None, "tilt_deg": None,
             "plane_height_interval_mm": (0, 50), "reason": "test", "extras": {}}
    res = _estimate(plate, anchor=prior)
    assert res["scale_tier"] == "prior"
    assert "size_prior_scale" in res["flags"]
    assert abs(res["volume_ml"] - _vol_gt(plate)) / _vol_gt(plate) < 0.30
    # prior tier must carry materially more uncertainty than measured
    assert res["sigma_grams_rel"] > 0.30


def test_table_prior_path_flagged(plate):
    res = _estimate(plate, cfg={"base_method": "table_prior"})
    assert res["base_method"] == "table_prior"
    assert "vessel_shape_uncertain" in res["flags"]
    # prior base height 8mm vs true floor 4mm -> heights slightly low, bounded
    assert abs(res["volume_ml"] - _vol_gt(plate)) / _vol_gt(plate) < 0.35


def test_bad_inputs_raise(plate):
    with pytest.raises(ValueError):
        _estimate(plate, cfg={})["x"] if False else estimate_portion(
            plate["image_bgr"], np.zeros_like(plate["mask_food"]),
            plate["depth_m"], estimate_anchor(plate["image_bgr"]),
            {"K": plate["camera"]["K"]}, DISH)
    with pytest.raises(ValueError):
        estimate_portion(
            plate["image_bgr"], plate["mask_food"], plate["depth_m"][:500],
            estimate_anchor(plate["image_bgr"]),
            {"K": plate["camera"]["K"]}, DISH)
