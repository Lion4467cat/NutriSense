from __future__ import annotations

import pytest

from nutrisense_synth.evaluation import build_depth_report
from nutrisense_synth.promotion import evaluate_candidate


def test_candidate_requires_target_gain_and_no_critical_regression() -> None:
    baseline = {"classification": .80, "segmentation": .60,
                "depth_geometry": .70, "weight": 20.0}
    candidate = {"classification": .83, "segmentation": .58,
                 "depth_geometry": .70, "weight": 19.0}
    good = evaluate_candidate("classification", baseline, candidate,
                              {"classification": .02}, direction="higher")
    assert good.promoted
    blocked = evaluate_candidate("classification", baseline, candidate,
                                  {"classification": .02},
                                  critical_regressions=["segmentation"], direction="higher")
    assert not blocked.promoted


def test_depth_report_separates_synthetic_accuracy_from_real_diagnostics() -> None:
    report = build_depth_report(
        synthetic_metrics={"rmse_m": .03},
        marker_scale_diagnostics={"detection_rate": .9},
        model_sha256="a" * 64, data_sha256="b" * 64,
        split_sha256="c" * 64, configuration={"seed": 42}, group_count=6,
    )
    assert report["synthetic_metric_depth"]["ground_truth_source"] == "renderer"
    assert report["real_depth_accuracy_claim"] is False
    assert report["real_marker_scale_diagnostics"]["depth_accuracy_claim"] is False
    with pytest.raises(ValueError, match="hashes"):
        build_depth_report(synthetic_metrics={}, marker_scale_diagnostics={},
                           model_sha256="", data_sha256="x", split_sha256="y",
                           configuration={}, group_count=1)
