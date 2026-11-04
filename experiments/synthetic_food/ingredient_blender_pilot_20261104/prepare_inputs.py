"""Prepare TRAIN-only portion/co-occurrence inputs and the ID7/60mm texture."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from nutrisense_synth.parameters import (  # noqa: E402
    eligible_wed_train_rows,
    load_class_registry,
    read_wed_train_manifest,
    wed_group_id,
)

OUT = ROOT / "datasets/processed/synthetic_food_ingredient_blender_pilot_20261104"
PROFILE_PATH = ROOT / "datasets/processed/synthetic_food_appearance_pilot_20261103/appearance_profiles.json"
CLASSES = {"chicken-dum-biryani": 12, "Bottle-gourd-curry": 1, "salad": 32}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = eligible_wed_train_rows(read_wed_train_manifest())
    grams: dict[str, list[float]] = {name: [] for name in CLASSES}
    cooccurrence: dict[str, set[str]] = {}
    for row in rows:
        group = wed_group_id(row)
        for dish in row.get("dishes", []):
            name = str(dish.get("name", ""))
            if name in grams and float(dish.get("weight_g", 0)) > 0:
                grams[name].append(float(dish["weight_g"]))
                cooccurrence.setdefault(group, set()).add(name)

    registry = load_class_registry()
    profiles = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profile_records = {}
    for name, class_id in CLASSES.items():
        profile = profiles[str(class_id)]
        params = registry[class_id]
        values = sorted(grams[name])
        if not values:
            raise RuntimeError(f"No eligible TRAIN portion measurements for {name}")
        profile_records[name] = {
            "class_id": class_id,
            "eligible_train_portion_count": len(values),
            "portion_quantiles_g": {
                "q20": float(np.quantile(values, 0.20)),
                "q50": float(np.quantile(values, 0.50)),
                "q80": float(np.quantile(values, 0.80)),
                "min": values[0],
                "max": values[-1],
            },
            "density_prior_g_ml": params.density_g_ml,
            "density_uncertainty_g_ml": params.density_uncertainty_g_ml,
            "density_source": params.density_source,
            "density_assumption_status": params.assumption_status,
            "density_evidence": list(params.density_evidence),
            "appearance_profile_sha256": profile["profile_sha256"],
            "appearance_profile_train_group_count": profile["source_group_count"],
            "appearance_profile_source_groups": sorted({
                str(s["group_id"]) for s in profile.get("statistics", [])
            }),
            "appearance_profile_rgb_median": profile["base_rgb"],
            "appearance_profile_rgb_q10": profile["between_group_rgb_q10"],
            "appearance_profile_rgb_q90": profile["between_group_rgb_q90"],
            "ingredient_composition_status": "inferred_from_class_name_and_human_reading_of_saved_eligible_WED_TRAIN_crop; WED_has_no_ingredient_instance_labels",
        }

    pairs = []
    for names in (("chicken-dum-biryani", "salad"), ("Bottle-gourd-curry", "salad")):
        candidates = sorted(group for group, group_names in cooccurrence.items()
                            if set(names).issubset(group_names))
        if not candidates:
            raise RuntimeError(f"No eligible TRAIN group co-occurrence for {names}")
        pairs.append({"class_names": list(names), "eligible_train_group_count": len(candidates),
                      "example_group_id": candidates[0],
                      "note": "composition support only; rendered portions use independent class TRAIN quantiles"})

    metadata = {
        "seed": 20261104,
        "source_split": "eligible WED TRAIN only",
        "wed_dev_image_accessed": False,
        "locked_data_accessed": False,
        "aruco_evaluation_accessed": False,
        "wed_test_accessed": False,
        "full_corpus_generated": False,
        "production_models_trained": False,
        "recipe_assumptions": {
            "chicken-dum-biryani": ["cooked rice grains", "brown chicken-like pieces"],
            "Bottle-gourd-curry": ["bottle-gourd chunks", "olive gravy", "small herb/onion garnish"],
            "salad": ["large cucumber slices", "tomato slices", "small onion/herb garnish"],
        },
        "class_evidence": profile_records,
        "observed_train_group_cooccurrences": pairs,
    }
    (OUT / "inputs.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")

    # 60 mm active marker, on an 85 mm card. The surrounding margin is white.
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, 7, 360, borderBits=1)
    modules=[]
    for row in range(6):
        modules.append([int(marker[row*60+30,col*60+30] < 128) for col in range(6)])
    card = np.full((512, 512), 255, np.uint8)
    card[76:436, 76:436] = marker
    cv2.imwrite(str(OUT / "marker_id7_60mm_on_85mm_card.png"), card)
    metadata["aruco_marker"]= {
        "dictionary":"DICT_4X4_50","marker_id":7,"marker_side_mm":60.0,
        "card_side_mm":85.0,"module_count":6,"module_side_mm":10.0,
        "black_modules":modules,
        "source":"OpenCV predefined dictionary generated with seed-independent exact marker ID 7",
    }
    (OUT / "inputs.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(f"Wrote TRAIN-only pilot inputs for {len(profile_records)} classes to {OUT}")


if __name__ == "__main__":
    main()
