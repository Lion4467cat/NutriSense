from __future__ import annotations

import numpy as np
import pytest

from nutrisense_synth.wed_segmentation import (
    class_set_metrics, confusion_matrix, connected_regions, region_counts,
)
from tools.analyze_wed_semantic_errors import _class_errors


def test_confusion_matrix_and_semantic_class_set() -> None:
    truth = np.array([[0, 1, 1], [2, 2, 0]], dtype=np.uint8)
    pred = np.array([[0, 1, 3], [2, 0, 0]], dtype=np.uint8)
    matrix = confusion_matrix(truth, pred)
    assert matrix[0, 0] == 2
    assert matrix[1, 1] == 1
    assert matrix[1, 3] == 1
    assert matrix[2, 2] == 1
    exact = class_set_metrics(truth, pred)
    assert not exact["class_set_exact"]
    assert exact["missed_class_ids"] == []
    assert exact["extra_class_ids"] == [3]


def test_connected_regions_keep_same_class_disconnected_regions_separate() -> None:
    labels = np.zeros((6, 8), dtype=np.uint8)
    labels[1:3, 1:3] = 7
    labels[3:5, 5:7] = 7
    regions = connected_regions(labels, class_aware=True)
    assert len(regions) == 2
    assert {region["class_id"] for region in regions} == {7}


def test_region_metrics_count_duplicate_predictions_and_missed_component() -> None:
    truth = np.zeros((8, 12), dtype=np.uint8)
    truth[1:4, 1:4] = 7
    truth[4:7, 8:11] = 7
    first_component = np.zeros_like(truth, dtype=bool)
    first_component[1:4, 1:4] = True
    predictions = [
        {"class_id": 7, "mask": first_component, "area": int(first_component.sum())},
        {"class_id": 7, "mask": first_component, "area": int(first_component.sum())},
    ]
    result = region_counts(truth, predictions, class_aware=True)
    assert result["true_positive_regions"] == 1
    assert result["false_positive_regions"] == 1
    assert result["duplicate_overlapping_predictions"] == 1
    assert result["missed_semantic_regions"] == 1
    assert not result["complete_region_recovery"]


def test_region_metrics_reject_wrong_class_match() -> None:
    truth = np.zeros((5, 5), dtype=np.uint8)
    truth[1:4, 1:4] = 7
    result = region_counts(
        truth, [{"class_id": 8, "mask": truth == 7, "area": 9}],
        class_aware=True)
    assert result["true_positive_regions"] == 0
    assert result["missed_semantic_regions"] == 1


def test_region_metrics_reject_bad_shape() -> None:
    truth = np.zeros((2, 2), dtype=np.uint8)
    with pytest.raises(ValueError):
        confusion_matrix(truth, np.zeros((3, 3), dtype=np.uint8))


def test_error_audit_counts_a_wrong_class_prediction_as_miss_and_spurious() -> None:
    truth = np.zeros((8, 8), dtype=np.uint8)
    truth[2:5, 2:5] = 7
    prediction = np.zeros_like(truth)
    prediction[2:5, 2:5] = 8
    result, _ = _class_errors(truth, prediction, 8, 8)
    assert result["missed_regions_with_zero_same_class_overlap"] == 1
    assert result["unmatched_prediction_with_no_gt_overlap"] == 1


def test_wed_deeplab_head_has_42_logits() -> None:
    torch = pytest.importorskip("torch")
    from models.wed_semantic_segmenter import build_model

    model = build_model(pretrained_backbone=False).eval()
    with torch.inference_mode():
        result = model(torch.zeros((1, 3, 64, 64)))
    assert result["out"].shape == (1, 42, 64, 64)
