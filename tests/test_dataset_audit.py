from tools.audit_dataset_manifest import audit_rows


def _row(obs: str, group: str, split: str, image: str) -> dict:
    return {
        "observation_id": obs,
        "group_id": group,
        "split": split,
        "image_path": image,
        "source_release": "fixture-v1",
        "license_ref": "fixture-license",
    }


def test_grouped_views_stay_in_one_split() -> None:
    rows = [_row("a1", "plate-a", "train", "a.jpg"),
            _row("a2", "plate-a", "train", "b.jpg"),
            _row("b1", "plate-b", "test", "c.jpg")]
    report = audit_rows(rows)
    assert report["passed"]
    assert report["rows_by_split"] == {"test": 1, "train": 2}
    assert report["groups_by_split"] == {"test": 1, "train": 1}


def test_rejects_group_crossing_splits() -> None:
    rows = [_row("a1", "same-plate", "train", "a.jpg"),
            _row("a2", "same-plate", "validation", "b.jpg")]
    report = audit_rows(rows)
    assert not report["passed"]
    assert report["cross_split_group_count"] == 1


def test_rejects_duplicate_observation_and_missing_provenance() -> None:
    rows = [_row("same", "a", "train", "a.jpg"),
            {**_row("same", "b", "test", "b.jpg"), "license_ref": ""}]
    report = audit_rows(rows)
    assert not report["passed"]
    assert report["cross_split_group_count"] == 0
    assert any("duplicate observation_id" in error for error in report["errors"])
    assert any("license_ref" in error for error in report["errors"])
