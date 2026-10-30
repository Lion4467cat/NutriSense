"""Audit a CSV/JSONL observation manifest for provenance and split leakage.

The auditor is intentionally model-agnostic. It never opens a sample's label
or image unless ``--hash-images`` is explicitly supplied; that option is meant
for auxiliary manifests such as FinnFoodPics, never for WED LOCKED data.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ALIASES = {
    "observation_id": ("observation_id", "id"),
    "group_id": ("group_id", "sample_group_id", "food_identity"),
    "split": ("split",),
    "image_path": ("image_path", "image", "path"),
    "source_release": ("source_release", "dataset_id", "source"),
    "license_ref": ("license_ref", "license", "license_or_terms"),
}


def _get(row: dict[str, Any], logical: str) -> Any:
    for name in ALIASES.get(logical, (logical,)):
        value = row.get(name)
        if value is not None and str(value).strip():
            return value
    return None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_rows(
    rows: list[dict[str, Any]],
    *,
    image_root: Path | None = None,
    hash_images: bool = False,
    require_provenance: bool = True,
) -> dict[str, Any]:
    """Return a JSON-safe audit; ``passed`` is false for structural leaks/errors."""
    errors: list[str] = []
    missing: Counter[str] = Counter()
    ids: set[str] = set()
    group_splits: dict[str, set[str]] = defaultdict(set)
    image_splits: dict[str, set[str]] = defaultdict(set)
    split_rows: Counter[str] = Counter()
    split_groups: dict[str, set[str]] = defaultdict(set)
    hashes: dict[str, set[str]] = defaultdict(set)

    for index, row in enumerate(rows, start=1):
        observation = _get(row, "observation_id")
        group = _get(row, "group_id")
        split = _get(row, "split")
        image = _get(row, "image_path")
        if not observation:
            missing["observation_id"] += 1
        elif str(observation) in ids:
            errors.append(f"row {index}: duplicate observation_id {observation!r}")
        else:
            ids.add(str(observation))
        if not group:
            missing["group_id"] += 1
        if not split:
            missing["split"] += 1
        if not image:
            missing["image_path"] += 1
        if require_provenance:
            for field in ("source_release", "license_ref"):
                if not _get(row, field):
                    missing[field] += 1
        if group and split:
            group_splits[str(group)].add(str(split))
            split_groups[str(split)].add(str(group))
        if split:
            split_rows[str(split)] += 1
        if image and split:
            resolved = Path(str(image))
            if image_root is not None and not resolved.is_absolute():
                resolved = image_root / resolved
            key = resolved.as_posix().casefold()
            image_splits[key].add(str(split))
            if hash_images:
                if not resolved.is_file():
                    errors.append(f"row {index}: image file not found: {resolved}")
                else:
                    hashes[sha256_file(resolved)].add(str(split))

    if not rows:
        errors.append("manifest has no observations")
    for field, count in sorted(missing.items()):
        errors.append(f"{count} rows missing required field {field}")
    group_leaks = sorted(group for group, splits in group_splits.items()
                         if len(splits) > 1)
    if group_leaks:
        errors.append(f"{len(group_leaks)} groups occur in multiple splits")
    image_leaks = sorted(image for image, splits in image_splits.items()
                         if len(splits) > 1)
    if image_leaks:
        errors.append(f"{len(image_leaks)} image paths occur in multiple splits")
    hash_leaks = sorted(digest for digest, splits in hashes.items()
                        if len(splits) > 1)
    if hash_leaks:
        errors.append(f"{len(hash_leaks)} exact image duplicates cross splits")

    return {
        "passed": not errors,
        "n_observations": len(rows),
        "n_groups": len(group_splits),
        "rows_by_split": dict(sorted(split_rows.items())),
        "groups_by_split": {key: len(value)
                            for key, value in sorted(split_groups.items())},
        "cross_split_group_count": len(group_leaks),
        "cross_split_image_path_count": len(image_leaks),
        "cross_split_exact_image_hash_count": len(hash_leaks),
        "errors": errors,
    }


def read_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.casefold() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as stream:
            return list(csv.DictReader(stream))
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {line_number}: {exc}") from exc
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--hash-images", action="store_true",
                        help="hash local image bytes for exact cross-split duplicates")
    parser.add_argument("--no-provenance-required", action="store_true",
                        help="skip source-release/license presence checks")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    report = audit_rows(
        read_rows(args.manifest), image_root=args.image_root,
        hash_images=args.hash_images,
        require_provenance=not args.no_provenance_required,
    )
    report["manifest"] = str(args.manifest)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
