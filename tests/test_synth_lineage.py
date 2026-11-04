from __future__ import annotations

import pytest

from nutrisense_synth.manifest import SourceGroup
from nutrisense_synth.parameters import (eligible_wed_train_rows, read_wed_train_manifest,
                                         wed_dev_group_ids, wed_group_id)


def test_aruco_eval_and_wed_dev_cannot_be_training_sources() -> None:
    for source, split in (("wed", "dev"), ("wed", "locked"), ("aruco", "aruco_eval")):
        with pytest.raises(ValueError):
            SourceGroup(source, "g1", "r1", split, "a" * 64)


def test_seed_42_dev_carve_is_removed_from_manifest_train_rows() -> None:
    rows = [{"split": "train", "date_key": f"202605{i:02d}", "set": "set1"}
            for i in range(1, 11)]
    rows += [{"split": "test", "date_key": "20260520", "set": "set1"}]
    dev_groups = wed_dev_group_ids(rows)
    eligible = eligible_wed_train_rows(rows)
    assert len(dev_groups) == 1
    assert not ({wed_group_id(row) for row in eligible} & dev_groups)
    assert len(eligible) == 9


def test_manifest_reader_does_not_deserialize_locked_records(tmp_path) -> None:
    path = tmp_path / "manifest.jsonl"
    path.write_text('{"split":"train","date_key":"20260101","set":"set1"}\n'
                    '{"split":"test", this is protected and intentionally malformed}\n')
    rows = read_wed_train_manifest(path)
    assert len(rows) == 1
    assert rows[0]["split"] == "train"
