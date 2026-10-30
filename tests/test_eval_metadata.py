import hashlib
import json
from pathlib import Path

from tools.log_run import build_run_metadata


def test_run_metadata_fingerprints_artifacts_config_and_plate_groups(tmp_path: Path) -> None:
    files = {
        "data/weight_head.pt": b"checkpoint",
        "data/weight_head_sigma.yaml": b"sigma",
        "models/weight_head.py": b"model code",
        "tools/train_weight_head.py": b"training code",
        "tools/run_eval.py": b"evaluation code",
        "data/wed_manifest.jsonl": b"manifest",
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    report = {
        "tier": "dev", "checkpoint": "data/weight_head.pt",
        "seed": 42, "split_seed": 42, "val_frac": 0.1,
        "bootstrap_reps": 2000, "device": "cpu", "limit": None,
        "per_plate": {"plate-b": {}, "plate-a": {}},
        "stress": {"blur": {}},
    }
    metadata = build_run_metadata(report, tmp_path)
    assert metadata["artifacts"]["checkpoint_sha256"] == hashlib.sha256(b"checkpoint").hexdigest()
    assert metadata["artifacts"]["manifest_sha256"] == hashlib.sha256(b"manifest").hexdigest()
    assert metadata["split_groups_sha256"] == hashlib.sha256(b'["plate-a","plate-b"]').hexdigest()
    assert metadata["config"]["stress_axes"] == ["blur"]
    assert metadata["run_id"].startswith("dev-")


def test_run_id_changes_when_checkpoint_changes(tmp_path: Path) -> None:
    for relative in ("data/weight_head.pt", "data/weight_head_sigma.yaml",
                     "models/weight_head.py", "tools/train_weight_head.py",
                     "tools/run_eval.py", "data/wed_manifest.jsonl"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative)
    report = {"tier": "dev", "checkpoint": "data/weight_head.pt", "per_plate": {}}
    first = build_run_metadata(report, tmp_path)["run_id"]
    (tmp_path / "data/weight_head.pt").write_text("changed")
    second = build_run_metadata(report, tmp_path)["run_id"]
    assert first != second
