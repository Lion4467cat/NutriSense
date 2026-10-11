"""Join WED images + labelIds masks + per-dish gram weights into one manifest.

Reads the dataset layout published with Arora et al. ICVGIP 2025 (MIT):

  <root>/{train,test}/<dd>-<mon>/imgsFine/leftImg8bit/default/setN/*.jpg
  <root>/{train,test}/<dd>-<mon>/gtFine/default/setN/*_gtFine_labelIds.png

and the repo's all_food_data.json (per-capture-date -> SetN -> food weights)
+ index_map.json (mask label id -> dish slug). Emits one JSONL row per image
view with its plate-level per-dish entries:

  {"split","date","date_key","set","image","mask",
   "dishes":[{"class_id","name","weight_g"}, ...]}

Paths are relative to the dataset root so the manifest stays portable.
Run:  .venv/bin/python -m tools.build_wed_manifest
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import yaml  # noqa: E402

DATE_RE = re.compile(r"^(\d{2})-([a-z]{3})$", re.I)
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def _date_key(date_dir: str, sample_year: int) -> str | None:
    m = DATE_RE.match(date_dir)
    if not m:
        return None
    day, mon = m.group(1), m.group(2).lower()
    if mon not in MONTHS:
        return None
    return f"{sample_year:04d}{MONTHS[mon]:02d}{int(day):02d}"


def build(dataset_root: Path, weights_json: Path, index_map: Path) -> list[dict]:
    weight_data = json.loads(weights_json.read_text())
    id2name = {int(k): v for k, v in json.loads(index_map.read_text()).items()
               if v.lower() != "background"}
    sample_year = int(next(iter(weight_data))[:4])

    rows: list[dict] = []
    for split in ("train", "test"):
        split_root = dataset_root / split
        if not split_root.is_dir():
            continue
        for date_dir in sorted(p.name for p in split_root.iterdir() if p.is_dir()):
            date_key = _date_key(date_dir, sample_year)
            if date_key is None or date_key not in weight_data:
                continue
            set_root = split_root / date_dir / "gtFine" / "default"
            if not set_root.is_dir():
                continue
            for set_name in sorted(p.name for p in set_root.iterdir() if p.is_dir()):
                json_key = set_name.capitalize()  # set17 -> Set17
                entries = weight_data[date_key].get(json_key, [])
                weight_map = {e["food_item"]: float(e["weight"]) for e in entries}
                for mask_path in sorted(set_root.glob(f"{set_name}/*_gtFine_labelIds.png")):
                    stem = mask_path.name.replace("_gtFine_labelIds.png", "")
                    image_path = (split_root / date_dir / "imgsFine" / "leftImg8bit"
                                  / "default" / set_name / f"{stem}_leftImg8bit.jpg")
                    if not image_path.is_file():
                        continue
                    dishes = [
                        {"class_id": cid, "name": name, "weight_g": weight_map[name]}
                        for cid, name in sorted(id2name.items())
                        if name in weight_map
                    ]
                    if not dishes:
                        continue
                    rows.append({
                        "split": split,
                        "date": date_dir,
                        "date_key": date_key,
                        "set": set_name,
                        "image": str(image_path.relative_to(dataset_root)),
                        "mask": str(mask_path.relative_to(dataset_root)),
                        "dishes": dishes,
                    })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(_ROOT / "data" / "wed_dishes.yaml"))
    ap.add_argument("--out", default=str(_ROOT / "data" / "wed_manifest.jsonl"))
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())["dataset"]
    root = Path(cfg["root"])
    rows = build(root if root.is_absolute() else _ROOT / root,
                 _ROOT / cfg["weights_json"], _ROOT / cfg["index_map"])

    out = Path(args.out)
    with out.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    n_train = sum(1 for r in rows if r["split"] == "train")
    n_test = len(rows) - n_train
    plates = {(r["date_key"], r["set"]) for r in rows}
    rois = sum(len(r["dishes"]) for r in rows)
    print(f"wrote {out}: {len(rows)} views "
          f"(train {n_train} / test {n_test}), {len(plates)} plates, {rois} dish-ROIs")


if __name__ == "__main__":
    main()
