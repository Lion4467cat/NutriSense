"""Evaluate the held-out Nutrition5k ingredient teacher on meal nutrients.

The candidate is source-specific and is not the deployed school-mode head.
Only Nutrition5k's fixed local test dishes are read; no model/threshold choice
may be made from this report. Ingredient gram predictions are converted to
kcal, fat, carbohydrate and protein with Nutrition5k ingredient metadata.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "data" / "n5k_ingredient_table.yaml"
INGREDIENT_METADATA = ROOT / "data" / "nutrition5k" / "metadata" / "ingredients_metadata.csv"
IMAGERY = ROOT / "data" / "nutrition5k" / "imagery" / "realsense_overhead"
DEFAULT_CHECKPOINT = ROOT / "data" / "ingredient_head_candidate.pt"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_densities(path: Path = INGREDIENT_METADATA) -> dict[str, dict[str, float]]:
    out = {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row in csv.DictReader(stream):
            name = row["ingr"].strip().casefold()
            out[name] = {
                "kcal": float(row["cal/g"]),
                "fat_g": float(row["fat(g)"],),
                "carbohydrate_g": float(row["carb(g)"],),
                "protein_g": float(row["protein(g)"],),
            }
    return out


def predict_macros(predicted_grams: dict[str, float],
                   densities: dict[str, dict[str, float]]) -> dict[str, float] | None:
    """Convert ingredient grams to macro totals; missing mappings abstain."""
    totals = {key: 0.0 for key in ("kcal", "fat_g", "carbohydrate_g", "protein_g")}
    for ingredient, grams in predicted_grams.items():
        row = densities.get(ingredient.strip().casefold())
        if row is None:
            return None
        for key in totals:
            totals[key] += max(0.0, float(grams)) * row[key]
    return totals


def select_present_ingredients(predicted_grams: dict[str, float],
                               present_names: list[str]) -> dict[str, float] | None:
    """Return a label-oracle subset, or abstain if any slot is unavailable.

    This is diagnostic only: callers must not supply held-out labels in a
    serving path.
    """
    if any(name not in predicted_grams for name in present_names):
        return None
    return {name: predicted_grams[name] for name in present_names}


def metric_rows(rows: list[dict]) -> dict:
    targets = ("kcal", "fat_g", "carbohydrate_g", "protein_g")
    out = {}
    for key in targets:
        errors = [float(r["pred"][key]) - float(r["truth"][key]) for r in rows]
        out[key] = {
            "mae": round(float(np.mean(np.abs(errors))), 3),
            "bias": round(float(np.mean(errors)), 3),
            "rmse": round(float(np.sqrt(np.mean(np.square(errors)))), 3),
        }
    return out


def evaluate(checkpoint: Path = DEFAULT_CHECKPOINT) -> dict:
    from models.ingredient_head import IngredientHead
    from models.weight_head import WeightHead
    from tools.train_ingredient_head import load_table, resolve_png

    table, dishes, _slot_to_idx, _k, _held, _impurity = load_table()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    slots = list(model_state["slots"])
    encoder = str(model_state["encoder"])
    model = WeightHead(num_classes=len(slots), encoder_id=encoder,
                       pretrained=True)
    model.head_mlp.load_state_dict(model_state["head"])
    model.to(device).eval()
    head = IngredientHead(model, slots, encoder, int(model_state.get("seed", 0)))
    densities = load_densities()
    gt_macros: dict[str, dict[str, float]] = {}
    for café in ("dish_metadata_cafe1.csv", "dish_metadata_cafe2.csv"):
        path = ROOT / "data" / "nutrition5k" / "metadata" / café
        with path.open(newline="", encoding="utf-8-sig") as stream:
            for row in csv.reader(stream):
                if not row or row[0] == "dish_id":
                    continue
                gt_macros[row[0]] = {
                    "kcal": float(row[1]),
                    "fat_g": float(row[3]),
                    "carbohydrate_g": float(row[4]),
                    "protein_g": float(row[5]),
                    "mass_g": float(row[2]),
                }

    records, skipped_missing_density, skipped_missing_labels = [], [], []
    for dish_id, dish in sorted(dishes.items()):
        if dish["split"] != "test":
            continue
        if dish_id not in gt_macros:
            skipped_missing_labels.append(dish_id)
            continue
        image_path = resolve_png(IMAGERY / dish_id, dish_id)
        if image_path is None:
            skipped_missing_labels.append(dish_id)
            continue
        rgb = np.asarray(Image.open(image_path).convert("RGB"))
        predicted_grams = head.predict(rgb[:, :, ::-1])
        predicted = predict_macros(predicted_grams, densities)
        if predicted is None:
            skipped_missing_density.append(dish_id)
            continue
        # The ingredient teacher is trained only on labels present for each
        # dish. Unlabeled slots were masked, not trained as zero, so summing
        # all output slots is its honest unfiltered full-head behavior but is
        # not a calibrated multi-label meal prediction. Also report an oracle
        # composition diagnostic that restricts grams to ingredients known
        # from the held-out labels; this isolates mass/density error and must
        # never be interpreted as deployable end-to-end performance.
        present_names = [name for name, _grams in dish["labeled"]]
        oracle_grams = select_present_ingredients(predicted_grams, present_names)
        if oracle_grams is None:
            skipped_missing_labels.append(dish_id)
            continue
        oracle_predicted = predict_macros(oracle_grams, densities)
        if oracle_predicted is None:
            skipped_missing_density.append(dish_id)
            continue
        truth = gt_macros[dish_id]
        records.append({
            "dish_id": dish_id,
            "pred": predicted,
            "oracle_present_ingredient_pred": oracle_predicted,
            "truth": {key: truth[key] for key in predicted},
            "mass_pred_g": sum(predicted_grams.values()),
            "oracle_present_mass_pred_g": sum(oracle_grams.values()),
            "mass_truth_g": truth["mass_g"],
        })

    if not records:
        raise RuntimeError("no held-out Nutrition5k dishes had compatible macro targets")
    mass_errors = [r["mass_pred_g"] - r["mass_truth_g"] for r in records]
    oracle_mass_errors = [r["oracle_present_mass_pred_g"] - r["mass_truth_g"]
                          for r in records]
    return {
        "source": "Nutrition5k-local-subset",
        "split": "dish-id hash test; 47 dishes planned",
        "checkpoint_sha256": _sha(checkpoint),
        "ingredient_table_sha256": _sha(TABLE),
        "ingredient_nutrition_metadata_sha256": _sha(INGREDIENT_METADATA),
        "dish_metadata_sha256": hashlib.sha256(b"".join(
            (ROOT / "data" / "nutrition5k" / "metadata" / name).read_bytes()
            for name in ("dish_metadata_cafe1.csv", "dish_metadata_cafe2.csv")
        )).hexdigest(),
        "device": device,
        "n_test_dishes_scored": len(records),
        "n_test_dishes_skipped_missing_macro_label_or_image": len(skipped_missing_labels),
        "n_test_dishes_skipped_missing_ingredient_nutrient_mapping": len(skipped_missing_density),
        "nutrient_metrics": metric_rows(records),
        "mass_total_mae_g": round(float(np.mean(np.abs(mass_errors))), 3),
        "oracle_present_ingredient_nutrient_metrics": metric_rows([
            {"pred": r["oracle_present_ingredient_pred"], "truth": r["truth"]}
            for r in records
        ]),
        "oracle_present_mass_total_mae_g": round(
            float(np.mean(np.abs(oracle_mass_errors))), 3),
        "warning": (
            "Exploratory Nutrition5k teacher metrics only; candidate failed "
            "leave-ingredient-out transfer gates and is not deployed. The "
            "full-head metric sums every ingredient slot, including slots "
            "whose absence was not supervised, so it exposes the current "
            "unusable end-to-end output. Oracle-present metrics use held-out "
            "ingredient labels to isolate portion/density error and are not "
            "deployable estimates. Do not compare these values with WED "
            "school-mode outputs."
        ),
        "per_dish": [{"dish_id": r["dish_id"], "predicted": r["pred"],
                      "oracle_present_ingredient_predicted":
                          r["oracle_present_ingredient_pred"],
                      "ground_truth": r["truth"]} for r in records],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "data" / "reports" / "nutrition5k_test_nutrients.json")
    args = parser.parse_args()
    report = evaluate(args.checkpoint)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "per_dish"}, indent=2))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
