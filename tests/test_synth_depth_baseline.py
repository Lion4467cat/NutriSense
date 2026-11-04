from __future__ import annotations

import numpy as np
import pytest

from nutrisense_synth.evaluation import metric_depth_metrics
from tools.run_renderer_depth_baseline import _horizontal_fov_x


def test_metric_depth_exact_match_has_zero_error() -> None:
    target = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    report = metric_depth_metrics(target, target)
    assert report["mae_m"] == 0.0
    assert report["rmse_m"] == 0.0
    assert report["abs_rel"] == 0.0
    assert report["silog_pct"] == 0.0
    assert report["delta_1_25"] == 1.0
    assert report["valid_prediction_fraction"] == 1.0


def test_metric_depth_detects_two_x_scale_error() -> None:
    target = np.full((2, 2), 1.0, dtype=np.float32)
    report = metric_depth_metrics(target * 2, target)
    assert report["mae_m"] == 1.0
    assert report["abs_rel"] == 1.0
    assert report["delta_1_25"] == 0.0
    assert report["silog_pct"] == pytest.approx(0.0)
    assert report["median_prediction_to_target_scale"] == 2.0


def test_metric_depth_counts_invalid_predictions_and_does_not_mutate_mask() -> None:
    target = np.ones((2, 2), dtype=np.float32)
    target_mask = np.array([[True, True], [False, False]])
    prediction = np.array([[1.0, np.nan], [0.0, 1.0]])
    original = target_mask.copy()
    report = metric_depth_metrics(prediction, target, target_mask)
    assert report["target_pixels"] == 2
    assert report["valid_prediction_pixels"] == 1
    assert report["valid_prediction_fraction"] == 0.5
    assert np.array_equal(target_mask, original)


def test_metric_depth_rejects_shape_mismatch_and_empty_target() -> None:
    with pytest.raises(ValueError, match="shape mismatch"):
        metric_depth_metrics(np.ones((2, 2)), np.ones((3, 3)))
    with pytest.raises(ValueError, match="at least one valid target"):
        metric_depth_metrics(np.ones((2, 2)), np.zeros((2, 2)))


def test_renderer_depth_uses_camera_intrinsics_for_horizontal_fov() -> None:
    K = np.array([[500.0, 0.0, 320.0],
                  [0.0, 500.0, 240.0],
                  [0.0, 0.0, 1.0]])
    assert _horizontal_fov_x(K, 640) == pytest.approx(65.2384861)
