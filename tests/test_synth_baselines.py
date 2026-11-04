from __future__ import annotations

import json

import pytest

from nutrisense_synth.evaluation import (
    BASELINE_STAGES,
    ROOT,
    require_frozen_baseline,
    sha256_file,
)


def test_frozen_baseline_requires_all_stage_metrics_hashes_and_groups(tmp_path) -> None:
    stages = {
        stage: {"metrics": {"value": 1.0}, "model_sha256": "a" * 64,
                "data_sha256": "b" * 64, "split_sha256": "c" * 64,
                "group_count": 2, "uncertainty": {"ci95": [0.1, 0.2]}}
        for stage in BASELINE_STAGES
    }
    artifacts = [{"path": "README.md", "sha256": sha256_file(ROOT / "README.md")}]
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps({
        "frozen": True,
        "stages": stages,
        "frozen_artifacts": artifacts,
    }))
    assert require_frozen_baseline(path)["frozen"]
    del stages["segmentation"]
    path.write_text(json.dumps({
        "frozen": True,
        "stages": stages,
        "frozen_artifacts": artifacts,
    }))
    with pytest.raises(ValueError, match="segmentation"):
        require_frozen_baseline(path)
