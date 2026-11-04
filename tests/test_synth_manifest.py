from __future__ import annotations

import json

import pytest

from nutrisense_synth.manifest import AnnotationBundle, SourceGroup, SyntheticSample, stable_id
from nutrisense_synth.measured import MeasuredExample, load_measured_examples


def test_source_group_allows_only_wed_train() -> None:
    source = SourceGroup("wed", "plate-1", "image.jpg", "train", "a" * 64)
    assert source.source_group_id == "plate-1"
    with pytest.raises(ValueError):
        SourceGroup("wed", "plate-1", "image.jpg", "dev", "a" * 64)
    with pytest.raises(ValueError):
        SourceGroup("aruco", "dish-1", "frame.jpg", "aruco_eval", "a" * 64)


def test_synthetic_mass_requires_physical_provenance() -> None:
    with pytest.raises(ValueError):
        AnnotationBundle(1, "food", {}, {"mass": True}, mass_g=20.0,
                         mass_provenance={"measurement_kind": "model_prediction"})
    ann = AnnotationBundle(1, "food", {}, {"mass": True}, mass_g=20.0,
                           mass_provenance={"measurement_kind": "synthetic_physical"})
    assert ann.mass_g == 20


def test_sample_pair_fields_are_all_or_none() -> None:
    source = SourceGroup("wed", "plate-1", "image.jpg", "train", "a" * 64)
    with pytest.raises(ValueError):
        SyntheticSample("s1", "scene-1", source, "renderer", "v1", 1,
                        "b" * 64, "x.png", "c" * 64, 10, 10, (),
                        "isolated_dish", {}, True, card_pair_id="pair-1")
    assert stable_id("x") == stable_id("x")


def test_measured_example_aggregates_class_totals() -> None:
    example = MeasuredExample.from_row({
        "split": "train",
        "date_key": "20250512",
        "set": "set1",
        "image": "train/example.jpg",
        "mask": "train/example.png",
        "dishes": [
            {"class_id": 34, "name": "steamed-rice", "weight_g": 90},
            {"class_id": 34, "name": "steamed-rice", "weight_g": 10},
            {"class_id": 13, "name": "chutney", "weight_g": 5},
        ],
    })
    assert example.source_group_id == "20250512_set1"
    assert example.mass_by_class == {34: 100.0, 13: 5.0}
    assert example.total_mass_g == 105.0


def test_measured_example_rejects_non_positive_or_unknown_targets() -> None:
    base = {
        "split": "train", "date_key": "20250512", "set": "set1",
        "image": "train/example.jpg", "dishes": [],
    }
    with pytest.raises(ValueError, match="at least one dish"):
        MeasuredExample.from_row(base)
    base["dishes"] = [{"class_id": 42, "name": "unknown", "weight_g": 10}]
    with pytest.raises(ValueError, match="invalid WED class"):
        MeasuredExample.from_row(base)
    base["dishes"] = [{"class_id": 1, "name": "food", "weight_g": 0}]
    with pytest.raises(ValueError, match="must be positive"):
        MeasuredExample.from_row(base)


def test_measured_loader_can_exclude_physical_groups(tmp_path) -> None:
    manifest = tmp_path / "manifest.jsonl"
    rows = [
        {"split": "train", "date_key": "a", "set": "one",
         "image": "a.jpg", "dishes": [{"class_id": 1, "name": "a", "weight_g": 1}]},
        {"split": "train", "date_key": "b", "set": "two",
         "image": "b.jpg", "dishes": [{"class_id": 2, "name": "b", "weight_g": 2}]},
        {"split": "dev", "date_key": "c", "set": "three",
         "image": "c.jpg", "dishes": [{"class_id": 3, "name": "c", "weight_g": 3}]},
    ]
    manifest.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    examples = load_measured_examples(manifest=manifest, split="train",
                                      exclude_groups={"a_one"})
    assert [item.source_record_id for item in examples] == ["b.jpg"]
