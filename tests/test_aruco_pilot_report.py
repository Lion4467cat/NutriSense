from __future__ import annotations

import pytest

from tools.report_aruco_pilot import GROUND_TRUTH, build_report


def test_pilot_report_keeps_tare_separate_and_uses_only_six_groups() -> None:
    groups = {}
    remaining = 23
    names = list(GROUND_TRUTH)
    for index, name in enumerate(names):
        truth = GROUND_TRUTH[name]
        frames = remaining if index == len(names) - 1 else 1
        remaining -= frames
        groups[name] = {
            "frame_count": frames,
            "tare_g": truth["tare_g"],
            "net_food_g": truth["net_food_g"],
        }
    report = build_report({"frozen": True, "candidate_id": "candidate-1"},
                          {"candidate_id": "candidate-1", "groups": groups})
    assert report["physical_group_count"] == 6
    assert report["source_frame_count"] == 23
    assert report["tare_and_net_food_reported_separately"] is True
    assert report["net_component_mae_g"] == 0
    assert report["tare_mae_g"] == 0


def test_pilot_report_rejects_unfrozen_candidate() -> None:
    with pytest.raises(ValueError, match="frozen=true"):
        build_report({"frozen": False, "candidate_id": "candidate-1"},
                     {"candidate_id": "candidate-1", "groups": {}})
