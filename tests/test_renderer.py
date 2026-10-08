import numpy as np

from tests.synth.scene import render_scene, default_scene
from models.scale_anchor import estimate_anchor

CANVAS_W, CANVAS_H = 1400, 1100


def _default_scene():
    if not hasattr(_default_scene, "_cache"):
        _default_scene._cache = render_scene()
    return _default_scene._cache


def test_image_and_gt_shapes():
    s = _default_scene()
    assert s["image_rgb"].shape == (CANVAS_H, CANVAS_W, 3)
    assert s["image_rgb"].dtype == np.uint8
    assert s["image_bgr"].shape == (CANVAS_H, CANVAS_W, 3)
    assert s["depth_m"].shape == (CANVAS_H, CANVAS_W)
    assert s["depth_m"].dtype == np.float32
    assert float(s["depth_m"].min()) > 0.1          # camera-z depth in metres
    assert set(np.unique(s["obj_ids"])) <= {0, 1, 2, 3, 4}
    assert set(np.unique(s["comp_ids"])) <= {0, 1, 2}
    K, R_wc = s["camera"]["K"], s["camera"]["R_wc"]
    assert K.shape == (3, 3) and R_wc.shape == (3, 3)
    np.testing.assert_allclose(R_wc @ R_wc.T, np.eye(3), atol=1e-9)
    assert abs(float(np.linalg.det(R_wc)) - 1.0) < 1e-9


def test_grams_match_config_within_1pct():
    s = _default_scene()
    food_cfg = s["cfg"]["food"]
    shares = {c["name"]: c["share_g"] for c in food_cfg["components"]}
    total_cfg = food_cfg["grams"]
    assert set(s["grams_gt"]) == set(shares)
    for name, expected in shares.items():
        err = abs(s["grams_gt"][name] - expected) / expected
        assert err < 0.01, f"{name}: {s['grams_gt'][name]:.1f} vs {expected}"
    err = abs(s["grams_gt_total"] - total_cfg) / total_cfg
    assert err < 0.01, f"total {s['grams_gt_total']:.1f} vs {total_cfg}"


def test_anchor_detected_on_rendered_scene():
    s = _default_scene()
    gt = s["anchor_gt"]
    assert gt is not None
    res = estimate_anchor(s["image_bgr"])
    assert res["method"] == "card_aruco"
    assert res["label"] == "measured"
    assert abs(res["cm_per_px"] - gt["cm_per_px"]) / gt["cm_per_px"] < 0.02
    side_err = abs(res["extras"]["marker_side_px"] - gt["marker_side_px"]) \
        / gt["marker_side_px"]
    assert side_err < 0.02
    assert abs(res["tilt_deg"] - gt["tilt_deg"]) < 1.5
    lo, hi = res["interval"]
    assert 0 < lo < res["cm_per_px"] < hi
    assert hi / lo < 1.05
    assert res["H"] is not None and res["H"].shape == (3, 3)


def test_depth_reprojects_to_known_planes():
    s = _default_scene()
    K, R_wc, C = s["camera"]["K"], s["camera"]["R_wc"], s["camera"]["C"]
    fx, cx, cy = K[0, 0], K[0, 2], K[1, 2]
    d = s["depth_m"].astype(np.float64) * 1000.0     # mm camera-z depth
    ys, xs = np.mgrid[0:CANVAS_H, 0:CANVAS_W]
    Pc = np.stack([(xs - cx) / fx * d, (ys - cy) / fx * d, d], axis=-1)
    Pw = Pc @ R_wc + C                               # R^T applied per pixel
    z = Pw[..., 2]

    tab = s["obj_ids"] == 0
    assert tab.sum() > 10000
    np.testing.assert_allclose(z[tab], 0.0, atol=0.5)

    card = s["obj_ids"] == 2
    assert card.sum() > 1000
    np.testing.assert_allclose(z[card], 0.6, atol=1.0)

    food = s["obj_ids"] == 4
    assert food.sum() > 5000
    assert 3.0 < float(z[food].min()) and float(z[food].max()) < 50.0


def test_comp_zones_cover_food_mask():
    s = _default_scene()
    comp, food = s["comp_ids"], s["mask_food"]
    assert set(np.unique(comp[food])) == {1, 2}
    assert not comp[~food].any()
    for zone in (1, 2):
        frac = float((comp == zone).sum()) / float(food.sum())
        assert 0.05 < frac < 0.95, f"zone {frac:.2f}"
    cfg = s["cfg"]["food"]["components"]
    assert cfg[0]["name"] in s["grams_gt"] and cfg[1]["name"] in s["grams_gt"]


def test_bowl_scene_renders():
    food = dict(default_scene()["food"])
    food["radius_mm"] = 70.0
    s = render_scene({"vessel": "bowl", "food": food})
    assert s["image_rgb"].shape == (CANVAS_H, CANVAS_W, 3)
    assert float(s["depth_m"].min()) > 0.1
    ids = set(np.unique(s["obj_ids"]))
    assert 1 in ids and 4 in ids                      # vessel floor/rim + food
    assert s["grams_gt_total"] > 400.0


def test_whole_layout_single_component():
    food = dict(default_scene()["food"])
    food.update(layout="whole", radius_mm=80.0,
                components=[{"name": "curd", "material": "curd",
                             "share_g": 450.0}])
    s = render_scene({"food": food})
    food_mask = s["mask_food"]
    assert food_mask.any()
    assert set(np.unique(s["comp_ids"][food_mask])) == {1}
    assert abs(s["grams_gt_total"] - 450.0) / 450.0 < 0.01
