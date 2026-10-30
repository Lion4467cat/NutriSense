"""Export the existing Nutrition5k ingredient table as an auditable manifest.

This local subset uses the project's deterministic dish-id hash split because
the original official split lists are not present beside the downloaded rows.
The manifest records that fact and keeps ingredient grams separate from WED
single-food plate grams.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data" / "n5k_ingredient_table.yaml"
IMAGES = ROOT / "data" / "nutrition5k" / "imagery" / "realsense_overhead"
LICENSE_REF = "Google Research Nutrition5k CC BY 4.0; see datasets/registry.csv"
DEFAULT_OUT = ROOT / "datasets" / "processed" / "nutrition5k_local_manifest.csv"


def build_manifest(table_path: Path = TABLE, image_root: Path = IMAGES) -> list[dict]:
    table = yaml.safe_load(table_path.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for dish_id, record in sorted(table["dishes"].items()):
        dish_dir = image_root / dish_id
        images = sorted(path for path in dish_dir.glob("*.png") if path.is_file())
        if not images:
            continue
        grams = [
            {"ingredient": str(name), "grams": float(value)}
            for name, value in record.get("labeled", [])
        ]
        rows.append({
            "observation_id": f"nutrition5k:{dish_id}",
            "image_path": (images[0].relative_to(ROOT).as_posix()
                           if images[0].is_relative_to(ROOT)
                           else images[0].as_posix()),
            "source_release": "Nutrition5k-local-subset",
            "source_record_id": dish_id,
            "group_id": dish_id,
            "split": str(record["split"]),
            "license_ref": LICENSE_REF,
            "target_kind": "ingredient_mass_vector",
            "target_unit": "g",
            "measurement_method": "source ingredient mass labels",
            "targets_json": json.dumps(grams, sort_keys=True),
            "n_labeled_ingredients": len(grams),
            "split_rule": table.get("meta", {}).get("split_rule", "unspecified"),
            "split_is_official": False,
        })
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, default=TABLE)
    parser.add_argument("--image-root", type=Path, default=IMAGES)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    rows = build_manifest(args.table, args.image_root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    split_counts: dict[str, int] = {}
    for row in rows:
        split_counts[row["split"]] = split_counts.get(row["split"], 0) + 1
    fingerprint = hashlib.sha256(args.out.read_bytes()).hexdigest()
    print(f"wrote {args.out}: {len(rows)} dishes, splits={split_counts}, sha256={fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
