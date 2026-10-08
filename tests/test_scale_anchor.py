import numpy as np
import cv2

from tools.make_reference_card import build_card, card_layout
from models.scale_anchor import estimate_anchor, load_config, read_exif
from tests.synth.render import trapezoid_quad, render_on_background

CANVAS_W, CANVAS_H = 1400, 1100


def _true_cm_per_px(H_card_to_scene, dpi=300):
    mk = card_layout(dpi)["marker"]
    corners = np.array([[mk[0], mk[1]], [mk[2], mk[1]],
                        [mk[2], mk[3]], [mk[0], mk[3]]], dtype=float)
    homog = np.column_stack([corners, np.ones(4)])
    proj = (H_card_to_scene @ homog.T).T
    proj = proj[:, :2] / proj[:, 2:]
    side = np.linalg.norm(np.roll(proj, -1, axis=0) - proj, axis=1).mean()
    return 60.0 / 10.0 / side


def _card_scene(seed=0):
    card = build_card(300)
    quad = trapezoid_quad(CANVAS_W, CANVAS_H, scale=0.34, y_frac=0.16, taper=0.10)
    scene, H = render_on_background(card, quad, (CANVAS_W, CANVAS_H), noise=4.0, seed=seed)
    return scene, H


def _draw_coin(canvas, center, r):
    cv2.circle(canvas, center, r, (110, 168, 212), -1)   # gold outer
    cv2.circle(canvas, center, int(r * 0.55), (150, 150, 155), -1)  # steel core


def test_card_tier_recovers_scale():
    scene, H = _card_scene()
    res = estimate_anchor(scene)
    assert res["label"] == "measured"
    assert res["method"] == "card_aruco"
    true = _true_cm_per_px(H)
    assert abs(res["cm_per_px"] - true) / true < 0.02
    lo, hi = res["interval"]
    assert 0 < lo < hi
    assert hi / lo < 1.05
    assert res["tilt_deg"] is not None and 0 <= res["tilt_deg"] < 60
    assert res["plane_height_interval_mm"] == (0, 50)
    assert res["H"] is not None and res["H"].shape == (3, 3)


def test_coin_tier_recovers_scale():
    canvas = np.full((CANVAS_H, CANVAS_W, 3), 190, np.uint8)
    _draw_coin(canvas, (CANVAS_W // 2, CANVAS_H // 2), 90)  # 180 px diameter
    res = estimate_anchor(canvas)
    assert res["label"] == "measured"
    assert res["method"] == "coin_bimetallic"
    true = 2.7 / 180.0
    assert abs(res["cm_per_px"] - true) / true < 0.05
    assert res["tilt_deg"] is None and res["H"] is None


def test_card_wins_over_coin():
    scene, _ = _card_scene()
    _draw_coin(scene, (CANVAS_W - 160, CANVAS_H - 160), 80)
    res = estimate_anchor(scene)
    assert res["method"] == "card_aruco"


def test_prior_fallback_on_empty_scene():
    canvas = np.full((CANVAS_H, CANVAS_W, 3), 180, np.uint8)
    rng = np.random.default_rng(3)
    canvas = np.clip(canvas.astype(int) + rng.integers(-5, 5, canvas.shape), 0, 255).astype(np.uint8)
    res = estimate_anchor(canvas)
    assert res["label"] == "prior"
    assert res["cm_per_px"] is None
    assert res["interval"] is None
    assert "no card or coin" in res["reason"]


def test_marker_too_small_rejected_with_reason():
    card = build_card(300)
    quad = trapezoid_quad(CANVAS_W, CANVAS_H, scale=0.08, y_frac=0.3, taper=0.05)  # marker < 80 px
    scene, _ = render_on_background(card, quad, (CANVAS_W, CANVAS_H), noise=0.0, seed=1)
    res = estimate_anchor(scene)
    assert res["label"] == "prior"
    assert "too small" in res["reason"]


def test_exif_read_on_plain_png(tmp_path):
    p = tmp_path / "plain.png"
    cv2.imwrite(str(p), np.full((64, 64, 3), 128, np.uint8))
    ex = read_exif(p)
    assert ex["focal_mm"] is None and ex["subject_distance_cm"] is None
    # end-to-end via path (EXIF branch + imread)
    res = estimate_anchor(str(p))
    assert res["label"] == "prior"


def test_config_loads_tiers():
    cfg = load_config()
    assert cfg["tiers"] == ["card", "coin", "prior"]
    assert cfg["card"]["marker_mm"] == 60.0
    assert cfg["coin"]["diameter_mm"] == 27.0
    assert cfg["card"]["ruler_checked"] is False
