"""Renderer-grounded checks for the depth/anchor/geometry integration seams."""
import numpy as np
import pytest

from engine.depth import (MonocularDepth, calibrate_depth_scale,
                          normalized_intrinsics_to_pixel_K)
from models.scale_anchor import estimate_anchor
from models.scale_anchor import refine_anchor_pose
from models.portion_estimator import estimate_portion
from nutrisense_synth.parameters import load_class_registry
from nutrisense_synth.scene import (build_class_scene, render_scene)


@pytest.fixture(scope="module")
def renderer_scene():
    return render_scene()


def test_renderer_exact_marker_corners_preserve_metric_depth(renderer_scene):
    scene = renderer_scene
    marker_anchor = {
        "method": "card_aruco",
        "marker_mm": 60.0,
        "extras": {"marker_corners_px":
                   scene["anchor_gt"]["marker_corners_px"].tolist()},
    }

    calibrated, factor, source = calibrate_depth_scale(
        scene["depth_m"], marker_anchor, scene["camera"]["K"])

    assert source == "card"
    assert factor == pytest.approx(1.0, abs=0.005)
    assert np.allclose(calibrated, scene["depth_m"] * factor)


def test_detected_marker_calibration_stays_within_two_percent_on_renderer(
        renderer_scene):
    scene = renderer_scene
    anchor = estimate_anchor(scene["image_bgr"])
    assert anchor["label"] == "measured"

    _calibrated, factor, source = calibrate_depth_scale(
        scene["depth_m"], anchor, scene["camera"]["K"])

    assert source == "card"
    assert factor == pytest.approx(1.0, abs=0.02)


def test_cpu_depth_provider_disables_half_precision(monkeypatch):
    import torch

    class FakeModel:
        def __init__(self):
            self.weight = torch.nn.Parameter(torch.ones(1))
            self.use_fp16 = None

        def parameters(self):
            return iter((self.weight,))

        def infer(self, image, **kwargs):
            self.use_fp16 = kwargs["use_fp16"]
            depth = torch.ones(image.shape[-2:])
            depth[0, 0] = torch.nan
            return {"depth": depth,
                    "intrinsics": torch.eye(3)}

    model = FakeModel()
    provider = MonocularDepth(device="cpu")
    monkeypatch.setattr(provider, "_load", lambda: model)

    result = provider(np.zeros((4, 4, 3), dtype=np.uint8))

    assert model.use_fp16 is False
    assert result["depth_m"].shape == (4, 4)
    assert np.isnan(result["depth_m"][0, 0])
    assert result["valid_fraction"] == pytest.approx(15 / 16)


def test_moge_normalized_intrinsics_convert_to_pixel_camera_matrix():
    normalized = np.array([[0.8, 0.0, 0.5],
                           [0.0, 0.9, 0.5],
                           [0.0, 0.0, 1.0]])
    actual = normalized_intrinsics_to_pixel_K(normalized, 640, 480)
    expected = np.array([[512.0, 0.0, 320.0],
                         [0.0, 432.0, 240.0],
                         [0.0, 0.0, 1.0]])
    assert np.array_equal(actual, expected)
    assert normalized_intrinsics_to_pixel_K(np.zeros((2, 2)), 640, 480) is None


@pytest.mark.parametrize("seed", [7001, 7003, 7005])
def test_detected_id7_calibrates_renderer_depth_across_camera_poses(seed):
    cls = load_class_registry()[7]
    cfg = build_class_scene(cls.class_id, cls.class_name, 180.0,
                            cls.density_g_ml, seed=seed, card_present=True,
                            size=(1400, 1100))
    scene = render_scene(cfg)
    anchor = estimate_anchor(scene["image_bgr"])
    assert anchor["label"] == "measured"

    _depth, factor, source = calibrate_depth_scale(
        scene["depth_m"], anchor, scene["camera"]["K"])

    assert source == "card"
    assert factor == pytest.approx(1.0, abs=0.02)


def test_marker_pose_is_refined_in_depth_intrinsics_frame():
    cls = load_class_registry()[7]
    scene = render_scene(build_class_scene(
        cls.class_id, cls.class_name, 180.0, cls.density_g_ml,
        seed=7001, card_present=True, size=(1400, 1100)))
    detected = estimate_anchor(scene["image_bgr"])
    K = scene["camera"]["K"]

    refined = refine_anchor_pose(detected, K, max_reproj_err_px=3.0)

    assert refined["extras"]["depth_pose_method"] == "moge_intrinsics"
    assert refined["tilt_deg"] == pytest.approx(scene["anchor_gt"]["tilt_deg"],
                                                abs=2.0)


def test_renderer_nine_gram_chutney_geometry_is_physical():
    cls = next(value for value in load_class_registry().values()
               if value.class_name.casefold() == "chutney")
    scene = render_scene(build_class_scene(
        cls.class_id, cls.class_name, 9.0, cls.density_g_ml,
        seed=8880, card_present=True, size=(640, 480)))
    anchor_gt = scene["anchor_gt"]
    anchor = {
        "method": "card_aruco", "label": "measured",
        "cm_per_px": anchor_gt["cm_per_px"],
        "interval": (anchor_gt["cm_per_px"] * 0.999,
                     anchor_gt["cm_per_px"] * 1.001),
        "tilt_deg": anchor_gt["tilt_deg"], "marker_mm": 60.0,
        "extras": {"marker_corners_px":
                   anchor_gt["marker_corners_px"].tolist()},
    }
    dish = {"components": {cls.class_name: {
        "share": 1.0, "density_g_ml": cls.density_g_ml}}}

    portion = estimate_portion(
        scene["image_bgr"], scene["mask_food"], scene["depth_m"], anchor,
        {"K": scene["camera"]["K"]}, dish)

    assert portion["grams"] == pytest.approx(9.0, rel=0.10)
    assert portion["volume_ml"] == pytest.approx(9.0 / cls.density_g_ml,
                                                  rel=0.10)
    assert portion["sigma_grams_rel"] > 0


def test_pipeline_renderer_card_to_mass_uses_calibrated_depth():
    from engine.pipeline import analyze
    from tests.conftest import OK_EXIF

    cls = next(value for value in load_class_registry().values()
               if value.class_name.casefold() == "chutney")
    scene = render_scene(build_class_scene(
        cls.class_id, cls.class_name, 9.0, cls.density_g_ml,
        seed=8880, card_present=True, size=(1400, 1100)))
    height, width = scene["depth_m"].shape
    K = scene["camera"]["K"]
    normalized_K = np.array([[K[0, 0] / width, 0.0, K[0, 2] / width],
                             [0.0, K[1, 1] / height, K[1, 2] / height],
                             [0.0, 0.0, 1.0]])

    def segment(_image):
        return {"mask": scene["mask_food"], "strategy": "renderer_gt",
                "sam_score": 1.0,
                "area_frac": float(scene["mask_food"].mean())}

    def depth(_image, **_kwargs):
        return {"depth_m": scene["depth_m"], "intrinsics": normalized_K,
                "model": "renderer_gt"}

    def classify(_image):
        return {"dish": "chutney", "confidence": 1.0, "method": "test",
                "match_score": 0.99, "reason": "renderer test"}

    result = analyze(
        scene["image_bgr"], "mon", "1-5", exif=OK_EXIF,
        deps={"segment": segment, "classify": classify, "depth": depth,
              "segment_items": lambda _image: {"items": [],
                                                "strategy": "renderer_test"}},
        n_mc=100)

    assert result["anchor"]["depth_scale_source"] == "card"
    assert result["portion"]["grams_source"] == "geometry"
    assert result["portion"]["grams"] == pytest.approx(9.0, rel=0.15)
    assert any("configured class/component density" in text
               for text in result["assumptions"])
