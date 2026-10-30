import csv
from pathlib import Path

import yaml

from tools.build_ecustfd_manifest import build_manifest as build_ecustfd
from tools.build_nutrition5k_manifest import build_manifest as build_nutrition5k


def test_nutrition5k_manifest_keeps_dish_group_and_target_semantics(tmp_path: Path) -> None:
    image_root = tmp_path / "images"
    (image_root / "dish_a").mkdir(parents=True)
    (image_root / "dish_a" / "dish_a_rgb.png").write_bytes(b"img")
    table = tmp_path / "table.yaml"
    table.write_text(yaml.safe_dump({
        "meta": {"split_rule": "dish-id hash"},
        "dishes": {"dish_a": {"split": "train", "labeled": [["rice", 12.5]]}},
    }))
    rows = build_nutrition5k(table, image_root)
    assert len(rows) == 1
    assert rows[0]["group_id"] == "dish_a"
    assert rows[0]["target_kind"] == "ingredient_mass_vector"
    assert rows[0]["target_unit"] == "g"
    assert rows[0]["split_is_official"] is False
    assert '"grams": 12.5' in rows[0]["targets_json"]


def test_ecustfd_manifest_keeps_views_together_and_masks_missing_mass(tmp_path: Path) -> None:
    image_root = tmp_path / "images"
    image_root.mkdir()
    rows = []
    for index in range(10):
        object_id = f"apple{index:03d}"
        for view in ("S", "T"):
            name = f"{object_id}{view}(1).JPG"
            (image_root / name).write_bytes(b"image")
            rows.extend([
                {"file": name, "object_id": object_id, "name": "apple",
                 "xmin": 1, "ymin": 2, "xmax": 3, "ymax": 4},
                {"file": name, "object_id": object_id, "name": "coin",
                 "xmin": 5, "ymin": 6, "xmax": 7, "ymax": 8},
            ])
    annotation_path = tmp_path / "annotations.csv"
    with annotation_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    manifest = build_ecustfd(tmp_path)
    assert len(manifest) == 20
    by_group: dict[str, set[str]] = {}
    for row in manifest:
        by_group.setdefault(row["group_id"], set()).add(row["split"])
        assert row["measured_mass_g"] == ""
        assert row["mass_loss_eligible"] is False
        assert row["target_kind"] == "food_bbox"
    assert all(len(splits) == 1 for splits in by_group.values())
