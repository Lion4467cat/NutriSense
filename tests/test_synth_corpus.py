from __future__ import annotations

import json

import numpy as np
import cv2
from PIL import Image

from nutrisense_synth.corpus import audit_manifest, generate_renderer_corpus
from nutrisense_synth.manifest import sha256_file


def test_audit_accepts_train_artifact_and_rejects_non_train(tmp_path) -> None:
    image = tmp_path / "sample.png"
    Image.new("RGB", (2, 2)).save(image)
    row = {
        "sample_id": "s1", "source": {"source": "wed", "source_split": "train"},
        "output_path": "sample.png", "output_sha256": sha256_file(image),
        "quality": {"automated_pass": True, "findings": [{"passed": True}]}, "card_pair_id": None,
        "width": 2, "height": 2, "card_present": False,
        "scene_parameters": {"anchor": {"card": False}}, "annotations": [],
    }
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps(row) + "\n")
    summary = tmp_path / "review_summary.json"
    summary.write_text(json.dumps({"passed": True}))
    assert audit_manifest(manifest, tmp_path) == []
    row["source"]["source_split"] = "dev"
    manifest.write_text(json.dumps(row) + "\n")
    assert any("WED TRAIN" in error for error in audit_manifest(manifest, tmp_path))


def test_train_source_renderer_corpus_round_trip(tmp_path) -> None:
    dataset_root = tmp_path / "wed"
    dataset_root.mkdir()
    image = np.full((12, 12, 3), 120, dtype=np.uint8)
    mask = np.ones((12, 12), dtype=np.uint8) * 34
    cv2.imwrite(str(dataset_root / "sample.jpg"), image)
    cv2.imwrite(str(dataset_root / "sample.png"), mask)
    rows = [{"split": "train", "date_key": f"202601{i:02d}", "set": "set1",
             "image": "sample.jpg", "mask": "sample.png",
             "dishes": [{"class_id": 34, "name": "steamed-rice", "weight_g": 80.0}]}
            for i in range(1, 11)]
    output = tmp_path / "generated"
    samples = generate_renderer_corpus(rows, dataset_root, output,
                                       samples_per_class=1, seed=3)
    assert len(samples) == 2
    assert {sample.card_present for sample in samples} == {True, False}
    summary = output / "review_summary.json"
    summary.write_text(json.dumps({"passed": True}))
    assert audit_manifest(output / "manifest.jsonl", output) == []
