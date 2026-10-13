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


def _draw_gold_disc(canvas, center, r):
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


def test_gold_disc_is_not_an_anchor():
    canvas = np.full((CANVAS_H, CANVAS_W, 3), 190, np.uint8)
    _draw_gold_disc(canvas, (CANVAS_W // 2, CANVAS_H // 2), 90)
    res = estimate_anchor(canvas)
    assert res["label"] == "prior"
    assert res["method"] == "prior"
    assert res["cm_per_px"] is None
    assert "no reference card" in res["reason"]


def test_prior_fallback_on_empty_scene():
    canvas = np.full((CANVAS_H, CANVAS_W, 3), 180, np.uint8)
    rng = np.random.default_rng(3)
    canvas = np.clip(canvas.astype(int) + rng.integers(-5, 5, canvas.shape), 0, 255).astype(np.uint8)
    res = estimate_anchor(canvas)
    assert res["label"] == "prior"
    assert res["cm_per_px"] is None
    assert res["interval"] is None
    assert res["reason"] == "no reference card in frame — scale from size priors"


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


def test_exif_tags_read_from_exif_ifd(tmp_path):
    from PIL import Image
    p = tmp_path / "phone.jpg"
    im = Image.new("RGB", (64, 64), 128)
    ex = im.getexif()
    ifd = ex.get_ifd(0x8769)
    ifd[37386] = 3.98     # FocalLength
    ifd[37382] = "45/1"   # SubjectDistance
    ifd[41988] = 1.0      # DigitalZoomRatio
    ifd[41989] = 26       # FocalLengthIn35mmFilm
    ex[0x8769] = ifd
    im.save(p, exif=ex)

    out = read_exif(p)
    assert out["focal_mm"] == 3.98
    assert out["subject_distance_cm"] == 45.0
    # 1.0 is a reported, protocol-compliant value — not swallowed as absent
    assert out["digital_zoom"] == 1.0
    assert out["focal_length_35mm"] == 26.0


def test_real_photos_exif_focal_length():
    """Assert focal length equals exif_dump.csv values for vivo, moto, and Galaxy."""
    import os
    from pathlib import Path
    import pytest

    env_dir = os.environ.get("CARD_PHOTOS_DIR")
    if env_dir:
        candidates = [Path(env_dir)]
    else:
        candidates = [
            Path("/home/tinkerer/Desktop/Nutrisense/CARD_PHOTOS"),
            Path("/home/tinkerer/Desktop/AruCo 7ID _plain _60mm/CARD_PHOTOS"),
            Path(__file__).resolve().parent.parent.parent / "CARD_PHOTOS",
        ]
    root = next((p for p in candidates if p.is_dir()), None)
    if root is None:
        pytest.skip("CARD_PHOTOS directory not found")

    expected = [
        ("existing_29/IMG_20261013_110219.jpg", 4.84),     # vivo vivo T4 5G
        ("existing_29/IMG_20261013_110823870.jpg", 4.266), # motorola moto g82 5G
        ("ruler/20261013_201052.jpg", 6.5),                 # samsung Galaxy S26 Ultra
    ]
    for rel_path, exp_focal in expected:
        p = root / rel_path
        if not p.exists():
            pytest.skip(f"Photo not found: {p}")
        ex = read_exif(p)
        assert ex["focal_mm"] is not None
        assert abs(ex["focal_mm"] - exp_focal) < 1e-3


def test_config_loads_tiers():
    cfg = load_config()
    assert cfg["tiers"] == ["card", "prior"]
    assert "coin" not in cfg
    assert cfg["card"]["marker_mm"] == 60.0
    assert cfg["card"]["ruler_checked"] is False
