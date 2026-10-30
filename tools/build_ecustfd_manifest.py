"""Build an identity-grouped ECUSTFD image/box manifest from local files.

The local mirror does not contain its documented ``portions.csv``. Therefore
this adapter exports only food/coin box annotations; it does not invent mass,
volume, or calorie labels and is not eligible for grams training.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets" / "raw" / "portion" / "ecustfd"
DEFAULT_OUT = ROOT / "datasets" / "processed" / "ecustfd_local_manifest.csv"
LICENSE_REF = (
    "Hugging Face mirror card states CC BY 4.0; upstream terms unverified; "
    "research-only pending confirmation (datasets/registry.csv)"
)


def _split_by_identity(groups: dict[str, set[str]]) -> dict[str, str]:
    """Stable per-food 70/15/15 identity split; paired views stay grouped."""
    by_food: dict[str, list[str]] = defaultdict(list)
    for group, foods in groups.items():
        # Mixed samples contain multiple food labels; stratify on the full
        # stable label signature while keeping the physical sample intact.
        signature = "|".join(sorted(food.casefold() for food in foods))
        by_food[signature].append(group)
    result: dict[str, str] = {}
    for food, identities in sorted(by_food.items()):
        ordered = sorted(
            identities,
            key=lambda group: hashlib.sha256(
                f"ecustfd-local-v1:{food}:{group}".encode()
            ).hexdigest(),
        )
        n_test = max(1, round(len(ordered) * 0.15))
        n_val = max(1, round(len(ordered) * 0.15))
        n_train = max(0, len(ordered) - n_val - n_test)
        for index, group in enumerate(ordered):
            result[group] = ("train" if index < n_train else
                             "validation" if index < n_train + n_val else "test")
    return result


def build_manifest(data_dir: Path = DATA) -> list[dict]:
    annotations_path = data_dir / "annotations.csv"
    if not annotations_path.is_file():
        raise FileNotFoundError(f"ECUSTFD annotations missing: {annotations_path}")
    annotations: dict[str, list[dict]] = defaultdict(list)
    group_food: dict[str, set[str]] = defaultdict(set)
    with annotations_path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            image = row["file"].strip()
            group = row["object_id"].strip()
            name = row["name"].strip()
            if not image or not group or not name:
                raise ValueError(f"incomplete ECUSTFD annotation: {row}")
            if name.casefold() not in {"coin"}:
                group_food[group].add(name)
            annotations[image].append({
                "category": name,
                "xmin": int(float(row["xmin"])),
                "ymin": int(float(row["ymin"])),
                "xmax": int(float(row["xmax"])),
                "ymax": int(float(row["ymax"])),
            })
    splits = _split_by_identity(group_food)
    output = []
    for image, boxes in sorted(annotations.items()):
        image_path = data_dir / "images" / image
        if not image_path.is_file():
            raise FileNotFoundError(f"ECUSTFD image missing: {image_path}")
        food_boxes = [box for box in boxes if box["category"].casefold() != "coin"]
        if not food_boxes:
            continue
        group_ids = sorted({
            # IDs are encoded in the annotation's object_id; recover by matching
            # the image prefix against known physical portions.
            group for group in group_food if image.startswith(group)
        })
        if len(group_ids) != 1:
            raise ValueError(f"cannot uniquely map ECUSTFD view to portion: {image}")
        group_id = group_ids[0]
        image_path_value = (image_path.relative_to(ROOT).as_posix()
                            if image_path.is_relative_to(ROOT)
                            else image_path.as_posix())
        output.append({
            "observation_id": f"ecustfd:{image}",
            "image_path": image_path_value,
            "source_release": "ECUSTFD-local-mirror",
            "source_record_id": image,
            "group_id": group_id,
            "split": splits[group_id],
            "license_ref": LICENSE_REF,
            "target_kind": "food_bbox",
            "target_unit": "pixel",
            "measurement_method": "manual bounding-box annotation",
            "targets_json": json.dumps(boxes, sort_keys=True),
            "food_name": "|".join(sorted(group_food[group_id])),
            "measured_mass_g": "",
            "measured_volume_mm3": "",
            "mass_loss_eligible": False,
            "mass_label_status": "portions.csv missing from local mirror",
        })
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    rows = build_manifest(args.data_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["split"]] = counts.get(row["split"], 0) + 1
    print(f"wrote {args.out}: {len(rows)} views, {len({r['group_id'] for r in rows})} portions, splits={counts}; mass labels unavailable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
