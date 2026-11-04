import numpy as np
import pytest

import models.wed_inference as wed_inference


def _runtime_for(labels):
    runtime = wed_inference.WEDInference.__new__(wed_inference.WEDInference)
    runtime.checkpoint_path = wed_inference.DEFAULT_CHECKPOINT
    runtime.predict = lambda _image: labels
    return runtime


def test_semantic_adapter_keeps_components_and_class_level_mass_rois():
    labels = np.zeros((20, 30), dtype=np.uint8)
    labels[2:5, 3:7] = 1
    labels[12:15, 20:25] = 1
    labels[7:11, 10:14] = 2
    runtime = _runtime_for(labels)

    result = runtime.segment(np.zeros((20, 30, 3), dtype=np.uint8))

    assert result["mask"].sum() == 12 + 15 + 16
    assert result["candidate_count"] == 3
    assert result["class_item_count"] == 2
    rice_like = next(item for item in result["items"] if item["class_id"] == 1)
    assert rice_like["component_count"] == 2
    assert rice_like["mask"].sum() == 12 + 15
    assert rice_like["bbox"] == [3, 2, 24, 14]
    assert len(result["regions"]) == 3
    assert all(region["mask"].dtype == bool for region in result["regions"])


def test_pipeline_deps_reuses_one_semantic_forward(monkeypatch):
    labels = np.zeros((12, 12), dtype=np.uint8)
    labels[2:10, 3:9] = 1
    runtime = _runtime_for(labels)
    calls = []

    def get_runtime():
        calls.append("load")
        return runtime

    monkeypatch.setattr(wed_inference, "get_runtime", get_runtime)
    frame = np.zeros((12, 12, 3), dtype=np.uint8)
    deps = wed_inference.pipeline_deps(frame)
    segmented = deps["segment"](frame)
    items = deps["segment_items"](frame)

    assert calls == ["load"]
    assert segmented["strategy"] == "wed_deeplabv3_semantic"
    assert items["strategy"] == "wed_semantic_class_union_components"
    assert items["candidate_count"] == 1
    assert items["items"][0]["semantic_class_name"]
    with pytest.raises(ValueError, match="different frame"):
        deps["segment"](frame.copy())
