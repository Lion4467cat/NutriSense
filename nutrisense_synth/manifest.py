"""Small, strict records for source lineage and synthetic annotations."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Literal

Split = Literal["train", "dev", "locked", "aruco_eval"]
Method = Literal["renderer", "gan", "diffusion"]
TASKS = ("classification", "segmentation", "depth", "marker", "mass")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(*parts: Any, prefix: str = "") -> str:
    payload = json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str)
    return prefix + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


@dataclass(frozen=True)
class SourceGroup:
    source: Literal["wed", "aruco"]
    source_group_id: str
    source_record_id: str
    source_split: Split
    source_image_sha256: str
    source_label_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.source_split != "train":
            raise ValueError("Only TRAIN source groups may produce synthetic training samples")
        if self.source != "wed":
            raise ValueError("Synthetic training sources must be WED groups")
        if not self.source_group_id or not self.source_record_id:
            raise ValueError("Source group and record identifiers are required")


@dataclass(frozen=True)
class AnnotationBundle:
    class_id: int
    class_name: str
    labels: dict[str, Any]
    task_valid: dict[str, bool]
    mass_g: float | None = None
    mass_provenance: dict[str, Any] = field(default_factory=dict)
    inferred_mass_g: float | None = None

    def __post_init__(self) -> None:
        if self.class_id < 1 or not self.class_name:
            raise ValueError("A WED food class id and name are required")
        unknown = set(self.task_valid) - set(TASKS)
        if unknown:
            raise ValueError(f"Unknown task validity keys: {sorted(unknown)}")
        if self.mass_g is not None and self.mass_g < 0:
            raise ValueError("Physical mass cannot be negative")
        if self.inferred_mass_g is not None and self.inferred_mass_g < 0:
            raise ValueError("Experimental predicted mass cannot be negative")
        if self.mass_g is not None and self.mass_provenance.get("measurement_kind") != "synthetic_physical":
            raise ValueError("Physical synthetic mass must carry synthetic_physical provenance")


@dataclass(frozen=True)
class SyntheticSample:
    sample_id: str
    scene_id: str
    source: SourceGroup
    method: Method
    method_revision: str
    seed: int
    config_sha256: str
    output_path: str
    output_sha256: str
    width: int
    height: int
    annotations: tuple[AnnotationBundle, ...]
    scene_kind: Literal["isolated_dish", "composed_thali"]
    scene_parameters: dict[str, Any]
    card_present: bool
    card_pair_id: str | None = None
    paired_sample_id: str | None = None
    quality: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    method_checkpoint_sha256: str | None = None
    method_provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.sample_id or not self.scene_id or not self.output_path:
            raise ValueError("Sample, scene, and output identities are required")
        if self.width < 1 or self.height < 1:
            raise ValueError("Image dimensions must be positive")
        if bool(self.card_pair_id) != bool(self.paired_sample_id):
            raise ValueError("Card-paired samples require both pair id and paired sample id")
        if self.source.source_split != "train":
            raise ValueError("Synthetic sample must inherit its TRAIN source split")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def write_jsonl(path: str | Path, samples: Iterable[SyntheticSample]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as stream:
        for sample in samples:
            stream.write(json.dumps(sample.to_dict(), sort_keys=True) + "\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if line.strip():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL at line {line_no}: {exc}") from exc
                rows.append(row)
    return rows
