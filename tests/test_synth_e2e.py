from __future__ import annotations

import pytest

from nutrisense_synth.e2e import (compare_regions_to_semantic_mask,
                                  extract_food_mass_g, summarize_end_to_end,
                                  summarize_segmentation)
import numpy as np


def test_extracts_food_mass_without_tare() -> None:
    wire = {"nutrition": {"grams": 315.5},
            "plate": {"tare_g": 127.0}, "portion": {"grams": 315.5}}
    assert extract_food_mass_g(wire) == 315.5


def test_extract_mass_falls_back_to_portion_and_rejects_invalid_values() -> None:
    assert extract_food_mass_g({"nutrition": {"grams": None},
                                "portion": {"grams": 22}}) == 22.0
    assert extract_food_mass_g({"nutrition": {"grams": float("nan")},
                                "portion": {"grams": -2}}) is None


def test_summary_reports_mass_error_return_rate_and_critical_failures() -> None:
    rows = [
        {"group": "p1", "ground_truth_mass_g": 100,
         "predicted_mass_g": 90, "complete_items": True,
         "critical_failure": False},
        {"group": "p1", "ground_truth_mass_g": 200,
         "predicted_mass_g": 180, "complete_items": False,
         "critical_failure": True},
        {"group": "p2", "ground_truth_mass_g": 50,
         "predicted_mass_g": None, "complete_items": False,
         "critical_failure": True},
    ]
    summary = summarize_end_to_end(rows)
    assert summary["n_views"] == 3
    assert summary["n_groups"] == 2
    assert summary["mass_return_rate"] == pytest.approx(2 / 3)
    assert summary["meal_mass_mae_g_returned"] == 15.0
    assert summary["critical_failure_rate"] == pytest.approx(2 / 3)
    assert summary["n_complete_item_outputs"] == 1


def test_summary_requires_rows() -> None:
    with pytest.raises(ValueError, match="at least one DEV view"):
        summarize_end_to_end([])


def test_semantic_mask_comparison_separates_union_iou_and_region_recall() -> None:
    labels = np.zeros((4, 4), dtype=np.uint8)
    labels[:2, :2] = 1
    labels[2:, 2:] = 2
    masks = [labels == 1, labels == 2]
    result = compare_regions_to_semantic_mask(labels, [1, 2], masks)
    assert result["foreground_union_iou"] == 1.0
    assert result["semantic_region_iou_at_0_5"] == 1.0
    assert result["semantic_region_gt_recall_at_0_5"] == 1.0


def test_segmentation_summary_bootstraps_by_source_group() -> None:
    rows = [
        {"group": "g1", "foreground_union_iou": 0.2,
         "foreground_union_dice": 0.3,
         "semantic_region_iou_at_0_5": 0.1,
         "semantic_region_gt_recall_at_0_5": 0.4,
         "predicted_region_count": 3,
         "ground_truth_semantic_region_count": 4},
        {"group": "g2", "foreground_union_iou": 0.4,
         "foreground_union_dice": 0.5,
         "semantic_region_iou_at_0_5": 0.3,
         "semantic_region_gt_recall_at_0_5": 0.6,
         "predicted_region_count": 5,
         "ground_truth_semantic_region_count": 4},
    ]
    result = summarize_segmentation(rows)
    assert result["n_groups"] == 2
    assert result["mean_predicted_regions"] == 4.0
    assert result["foreground_union_iou"] == pytest.approx(0.3)
