from __future__ import annotations

import csv
import json

import pytest

from nutrisense_synth.review import build_review_queue, review_gate


def test_review_queue_is_stratified_and_repeatable() -> None:
    rows = [{"sample_id": f"s{i}", "method": "renderer", "card_present": i % 2 == 0,
             "annotations": [{"class_name": "rice", "labels": {"portion_range": "wed_observed"}}]}
            for i in range(8)]
    first = build_review_queue(rows, per_stratum=1, seed=5)
    second = build_review_queue(rows, per_stratum=1, seed=5)
    assert first == second
    assert {item["stratum"]["card"] for item in first} == {"card", "no_card"}


def test_review_gate_requires_completed_stratified_review(tmp_path) -> None:
    path = tmp_path / "review.csv"
    fields = ["stratum", "reviewer", "identity_correct", "mask_geometry_valid",
              "marker_valid", "appearance_plausible"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerow({"stratum": '{"card":"card"}', "reviewer": "reviewer1",
                         "identity_correct": "yes", "mask_geometry_valid": "yes",
                         "marker_valid": "yes", "appearance_plausible": "yes"})
    assert review_gate(path)["passed"]
    with path.open("a", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writerow({"stratum": '{"card":"card"}', "reviewer": "reviewer1",
                         "identity_correct": "no", "mask_geometry_valid": "yes",
                         "marker_valid": "", "appearance_plausible": "yes"})
    with pytest.raises(ValueError, match="marker review"):
        review_gate(path)


def test_review_rejection_restricts_task_labels_in_manifest(tmp_path) -> None:
    manifest = tmp_path / "manifest.jsonl"
    sample = {"sample_id": "s1", "annotations": [{"task_valid": {
        "classification": True, "segmentation": True, "depth": True,
        "mass": True, "marker": True}}]}
    manifest.write_text(json.dumps(sample) + "\n")
    queue = tmp_path / "queue.csv"
    fields = ["sample_id", "stratum", "reviewer", "identity_correct",
              "mask_geometry_valid", "marker_valid", "appearance_plausible"]
    with queue.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerow({"sample_id": "s1", "stratum": '{"card":"card"}',
                         "reviewer": "reviewer1", "identity_correct": "no",
                         "mask_geometry_valid": "yes", "marker_valid": "yes",
                         "appearance_plausible": "yes"})
    review_gate(queue, min_acceptance=0.0, manifest_path=manifest)
    row = json.loads(manifest.read_text().splitlines()[0])
    validity = row["annotations"][0]["task_valid"]
    assert validity["classification"] is False
    assert validity["segmentation"] is True
    assert validity["depth"] is True
    assert validity["mass"] is True
