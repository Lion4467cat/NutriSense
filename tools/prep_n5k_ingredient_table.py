"""07b data prep: Nutrition5k per-ingredient gram table for the teacher head.

Reads the Nutrition5k dish metadata CSVs (per-dish per-ingredient grams,
data/nutrition5k/metadata/) and writes data/n5k_ingredient_table.yaml:
  - the ingredient slot table (K most frequent cooked-ingredient names,
    ranked by frequency), frozen into the artifact so the head's slot
    mapping is reproducible;
  - the fixed plate-level split (train/val/test by dish-id hash, seed 42);
  - the leave-ingredient-out (LIO) experiment definition: held-out
    ingredients chosen among frequent slots from different categories, so
    "the head transfers to an ingredient it never saw" is a falsifiable
    per-ingredient MAE rather than vibes.
Only dishes whose overhead imagery exists (or is being pulled) are kept;
grams go through sqrt(grams) later in the trainer to tame the skew.

Run: .venv/bin/python -m tools.prep_n5k_ingredient_table [--top-k 48]
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
from collections import Counter
from pathlib import Path

import yaml

META_DIR = Path("data") / "nutrition5k" / "metadata"
IMAGERY_DIR = Path("data") / "nutrition5k" / "imagery" / "realsense_overhead"
OUT_PATH = Path("data") / "n5k_ingredient_table.yaml"

SEED = 42
LIO_PICKS = (  # one slot per coarse category, among frequent ingredients
    "white rice",      # grain
    "chicken",         # meat
    "broccoli",        # green vegetable
    "olive oil",       # fat (invisible-ish)
    "mixed greens",    # salad
)


def dish_split(dish_id: str) -> str:
    h = int(hashlib.sha1(f"{SEED}:{dish_id}".encode()).hexdigest()[:8], 16)
    r = (h % 100) / 100.0
    if r < 0.80:
        return "train"
    if r < 0.90:
        return "val"
    return "test"


def parse_dish_csv(path: Path) -> dict[str, list[tuple[str, str, float]]]:
    """dish_id -> [(ingr_id, ingredient_name, grams), ...]."""
    out: dict[str, list[tuple[str, str, float]]] = {}
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not row or not row[0].strip():
                continue
            dish = row[0].strip()
            i = 6
            while i + 2 <= len(row) - 1:
                ingr_id, name = row[i].strip(), row[i + 1].strip()
                try:
                    grams = float(row[i + 2])
                except (ValueError, IndexError):
                    break
                if name and grams >= 0:
                    out.setdefault(dish, []).append((ingr_id, name, grams))
                i += 5
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top-k", type=int, default=48)
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()

    dishes: dict[str, list[tuple[str, str, float]]] = {}
    for path in sorted(META_DIR.glob("dish_metadata_*.csv")):
        dishes.update(parse_dish_csv(path))

    with_images = [d for d in dishes if (IMAGERY_DIR / d).is_dir()
                   and any((IMAGERY_DIR / d).iterdir())]
    freq = Counter(name for d in with_images
                   for _id, name, g in dishes[d] if g > 0 and name.lower() not in
                   ("water", "water, distilled"))
    slots = [name for name, _c in freq.most_common(args.top_k)]
    slot_to_idx = {name: k for k, name in enumerate(slots)}

    rows = {}
    for dish in sorted(with_images):
        labeled = [(name, g) for _id, name, g in dishes[dish]
                   if g > 0 and name in slot_to_idx]
        unlabeled = [(name, g) for _id, name, g in dishes[dish]
                     if g > 0 and name not in slot_to_idx]
        if not labeled:
            continue
        rows[dish] = {
            "split": dish_split(dish),
            "labeled": sorted(labeled),
            "other_ingredient_grams": sorted(unlabeled),
        }

    lio = {p: slot_to_idx[p] for p in LIO_PICKS if p in slot_to_idx}

    doc = {
        "meta": {
            "dataset": "Nutrition5k (Google Research, CC BY 4.0)",
            "route": "HF mirror mmathys/food-nutrients (ungated derivative; "
                     "all image ids verified against local dish_metadata ids)",
            "generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%MZ"),
            "extraction_tool": "tools/prep_n5k_ingredient_table.py",
            "split_rule": f"dish-id sha1 hash, seed {SEED}, 0.8/0.1/0.1",
            "water_note": "water rows dropped from slots (no visual mass)",
            "audit_summary": {
                "dishes_in_metadata": len(dishes),
                "dishes_with_imagery": len(with_images),
                "dishes_in_table": len(rows),
                "slots": len(slots),
                "split_counts": {s: sum(1 for r in rows.values() if r["split"] == s)
                                 for s in ("train", "val", "test")},
                "lio_ingredients": list(lio),
            },
        },
        "slots": slots,
        "slot_index": slot_to_idx,
        "lio_held_out": lio,
        "dishes": rows,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True)
    s = doc["meta"]["audit_summary"]
    print(f"wrote {args.out}: {s['dishes_in_table']} dishes, "
          f"{s['slots']} slots, splits {s['split_counts']}, "
          f"LIO {s['lio_ingredients']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
