from __future__ import annotations

import pytest

from nutrisense_synth.ablation import build_conditions
from nutrisense_synth.promotion import evaluate_candidate


def test_matched_synthetic_ratio_sweep_preserves_budget_and_class_quotas() -> None:
    conditions = build_conditions(100, {1: 30, 2: 70}, methods=("renderer", "gan"))
    assert len(conditions) == 10
    for condition in conditions:
        assert condition.real_examples + condition.synthetic_examples == 100
        assert sum(condition.class_quotas.values()) == 100
        assert sum(condition.real_class_quotas.values()) == condition.real_examples
        assert sum(condition.synthetic_class_quotas.values()) == condition.synthetic_examples
    assert {item.synthetic_fraction for item in conditions} == {0, .25, .5, .75, 1}


def test_promotion_respects_lower_is_better_and_registered_thresholds() -> None:
    result = evaluate_candidate("weight", {"classification": .8, "segmentation": .5,
                                           "depth_geometry": .7, "weight": 20.0},
                                {"weight": 18.0}, {"weight": 1.0}, direction="lower")
    assert result.promoted
    with pytest.raises(ValueError, match="earlier-stage baselines"):
        evaluate_candidate("weight", {"weight": 20.0}, {"weight": 18.0},
                           {"weight": 1.0}, direction="lower")
