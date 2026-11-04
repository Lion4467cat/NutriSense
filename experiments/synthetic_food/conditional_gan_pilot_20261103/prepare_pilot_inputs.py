"""Select eligible WED TRAIN references and existing five-class Blender scenes.

Only the already-established eligible TRAIN groups are opened. Generated
products and copied TRAIN references go under ignored datasets/processed.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT := Path(__file__).resolve().parents[3]) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nutrisense_synth.parameters import (  # noqa: E402
    DEFAULT_MANIFEST, eligible_wed_train_rows, read_wed_train_manifest, wed_group_id,
)

OUT = ROOT / "datasets/processed/conditional_gan_pilot_20261103"
BLENDER_ROOT = ROOT / "datasets/processed/synthetic_food_pilot_20261103"
CLASSES = {
    34: "steamed-rice",
    12: "chicken-dum-biryani",
    1: "Bottle-gourd-curry",
    28: "phulka",
    32: "salad",
}
def _load_wed_train_refs():
    rows = eligible_wed_train_rows(read_wed_train_manifest(DEFAULT_MANIFEST))
    names = {int(k): v for k, v in json.loads(
        (ROOT / "data/wed/index_map.json").read_text(encoding="utf-8")).items()}
    support = {cid: {"views": 0, "groups": set(), "pixels": 0}
               for cid in names}
    selected = {}
    candidates = {cid: [] for cid in CLASSES}
    for row in rows:
        mask_path = ROOT / "data/wed" / row["mask"]
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None or int(mask.max()) > 41:
            raise ValueError(f"Invalid eligible TRAIN label map: {row['mask']}")
        ids, counts = np.unique(mask, return_counts=True)
        present = {int(cid): int(n) for cid, n in zip(ids, counts) if cid > 0}
        group = wed_group_id(row)
        for cid, n in present.items():
            support[cid]["views"] += 1
            support[cid]["groups"].add(group)
            support[cid]["pixels"] += n
        for cid, class_candidates in candidates.items():
            area = present.get(cid, 0)
            if area:
                class_candidates.append((row, group, area, area / mask.size))
    if len(rows) != 1038:
        raise RuntimeError(f"Expected the frozen eligible TRAIN view count 1038, found {len(rows)}")
    if len({wed_group_id(row) for row in rows}) != 198:
        raise RuntimeError("Eligible TRAIN groups differ from the established 198-group set")

    for cid, options in candidates.items():
        # One image per physical meal group. Choose a representative median mask
        # fraction, preventing a long burst from dominating reference selection.
        per_group = {}
        for option in options:
            per_group.setdefault(option[1], []).append(option)
        group_representatives = []
        for group, items in per_group.items():
            items.sort(key=lambda x: x[3])
            group_representatives.append(items[len(items) // 2])
        median_fraction = float(np.median([x[3] for x in group_representatives]))
        selected[cid] = min(group_representatives, key=lambda x: abs(x[3] - median_fraction))
    return rows, names, support, selected


def _select_blender_samples():
    manifest = [json.loads(line) for line in
                (BLENDER_ROOT / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    result = {}
    for cid, name in CLASSES.items():
        candidates = [row for row in manifest
                      if row["scene_kind"] == "isolated_dish" and row["card_present"]
                      and any(int(a["class_id"]) == cid for a in row["annotations"])]
        if not candidates:
            raise FileNotFoundError(f"No existing Blender card-present scene for {name}")
        row = min(candidates, key=lambda x: x["sample_id"])
        rgb_path = BLENDER_ROOT / row["rgb_path"]
        mask_path = rgb_path.parent / "food_class_mask.png"
        if not rgb_path.is_file() or not mask_path.is_file():
            raise FileNotFoundError(f"Existing Blender scene missing RGB or semantic mask for {name}")
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None or cid not in {int(v) for v in np.unique(mask)}:
            raise ValueError(f"Blender mask does not contain WED class {cid}: {mask_path}")
        result[cid] = {"sample_id": row["sample_id"],
                       "rgb_path": str(rgb_path.relative_to(ROOT)),
                       "mask_path": str(mask_path.relative_to(ROOT)),
                       "metadata": row}
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "wed_train_references").mkdir(exist_ok=True)
    rows, names, support, refs = _load_wed_train_refs()
    blender = _select_blender_samples()
    support_json = {
        "split": "eligible WED TRAIN only; fixed DEV carve removed",
        "views": len(rows), "groups": len({wed_group_id(r) for r in rows}),
        "classes": {str(cid): {"name": names[cid], "mask_positive_views": item["views"],
                               "source_groups": len(item["groups"]),
                               "foreground_pixels": item["pixels"]}
                    for cid, item in sorted(support.items())},
    }
    (OUT / "train_class_support.json").write_text(
        json.dumps(support_json, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest = {"schema": "wed_semantic_gan_pilot_inputs_v1", "classes": {}}
    for cid, name in CLASSES.items():
        row, group, area, fraction = refs[cid]
        reference_name = f"class_{cid:02d}_{name}.jpg"
        source = ROOT / "data/wed" / row["image"]
        destination = OUT / "wed_train_references" / reference_name
        shutil.copyfile(source, destination)
        manifest["classes"][str(cid)] = {
            "name": name,
            "wed_train_reference": str(destination.relative_to(ROOT)),
            "wed_train_mask": str((ROOT / "data/wed" / row["mask"]).relative_to(ROOT)),
            "wed_group": group,
            "reference_class_fraction": fraction,
            "blender": blender[cid],
        }
    manifest["guardrails"] = {
        "wed_source_rows": len(rows), "wed_source_groups": len({wed_group_id(r) for r in rows}),
        "protected_splits_opened": False, "production_checkpoints_modified": False,
        "blender_artifacts_modified": False,
    }
    (OUT / "pilot_inputs.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    make_sheet(manifest)


def make_sheet(manifest):
    columns = ["WED TRAIN reference", "Existing Blender RGB", "Blender semantic mask"]
    tw, th, gap, header = 360, 270, 16, 70
    rows = list(manifest["classes"].items())
    sheet = Image.new("RGB", (gap + 3 * (tw + gap), header + len(rows) * (th + 54)), "#f4f1e8")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 19)
        small = ImageFont.truetype("DejaVuSans.ttf", 14)
    except OSError:
        font = small = ImageFont.load_default()
    for i, title in enumerate(columns):
        draw.text((gap + i * (tw + gap), 16), title, fill="#24352c", font=font)
    for idx, (raw_id, item) in enumerate(rows):
        cid = int(raw_id); y = header + idx * (th + 54)
        draw.text((gap, y - 25), f"{item['name']} · WED class {cid}", fill="#24352c", font=small)
        paths = [ROOT / item["wed_train_reference"],
                 ROOT / item["blender"]["rgb_path"],
                 ROOT / item["blender"]["mask_path"]]
        for col, path in enumerate(paths):
            image = Image.open(path)
            if col == 2:
                labels = np.asarray(image.convert("L"))
                color = np.zeros((*labels.shape, 3), dtype=np.uint8)
                color[labels > 0] = (224, 132, 54)
                color[labels == cid] = (41, 134, 88)
                image = Image.fromarray(color)
            else:
                image = image.convert("RGB")
            image.thumbnail((tw, th), Image.Resampling.LANCZOS)
            tile = Image.new("RGB", (tw, th), "white")
            tile.paste(image, ((tw - image.width) // 2, (th - image.height) // 2))
            sheet.paste(tile, (gap + col * (tw + gap), y))
    sheet.save(OUT / "baseline_comparison.png")


if __name__ == "__main__":
    main()
