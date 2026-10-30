import json
import pytest

from tools.compare_cv_runs import compare


def _report(tag: str, abs_per_plate: float):
    folds = []
    for fold_index, plate in enumerate(("plate_a", "plate_b")):
        folds.append({
            "fold_index": fold_index,
            "held_out_plates": [plate],
            "train_plates": ["train_group"],
            "epoch_selection_plates": ["val_group"],
            "excluded_dev_plates": ["dev_group"],
            "per_plate_errors": {
                plate: {"n_rois": 10,
                        "sum_abs_err_g": 10 * abs_per_plate,
                        "sum_signed_err_g": 0.0},
            },
            "per_class_errors": {
                "rice": {"n_rois": 10,
                         "sum_abs_err_g": 10 * abs_per_plate},
            },
        })
    return {"protocol": "outer plate CV", "seed": 42, "folds": 2,
            "encoder": "dinov2", "manifest_sha256": "abc", "tag": tag,
            "fold_results": folds}


def test_paired_plate_bootstrap_accepts_clear_paired_improvement():
    result = compare(_report("base", 10), _report("candidate", 9),
                     replicates=200)
    json.dumps(result)
    assert result["paired_delta_mae_g"] == -1
    assert result["paired_delta_plate_bootstrap_95ci_g"] == [-1, -1]
    assert result["decision"] == "pass"


def test_cv_comparison_rejects_different_plate_sets():
    baseline = _report("base", 10)
    candidate = _report("candidate", 9)
    candidate["fold_results"][1]["held_out_plates"] = ["other"]
    candidate["fold_results"][1]["per_plate_errors"] = {
        "other": {"n_rois": 10, "sum_abs_err_g": 90,
                  "sum_signed_err_g": 0}}
    with pytest.raises(ValueError, match="held_out_plates"):
        compare(baseline, candidate, replicates=20)
