from tools.eval_nutrition import (
    metric_rows,
    predict_macros,
    select_present_ingredients,
)


def test_predict_macros_uses_gram_scaled_nutrient_density():
    density = {
        "rice": {"kcal": 1.0, "fat_g": 0.02,
                 "carbohydrate_g": 0.2, "protein_g": 0.03},
    }
    out = predict_macros({"rice": 100.0}, density)
    assert out == {"kcal": 100.0, "fat_g": 2.0,
                   "carbohydrate_g": 20.0, "protein_g": 3.0}


def test_missing_nutrient_mapping_abstains_instead_of_assuming_zero():
    assert predict_macros({"unknown": 100.0}, {}) is None


def test_macro_metrics_are_reported_separately():
    rows = [{
        "pred": {"kcal": 110, "fat_g": 12, "carbohydrate_g": 18, "protein_g": 6},
        "truth": {"kcal": 100, "fat_g": 10, "carbohydrate_g": 20, "protein_g": 5},
    }]
    result = metric_rows(rows)
    assert result["kcal"]["mae"] == 10
    assert result["fat_g"]["mae"] == 2
    assert result["carbohydrate_g"]["mae"] == 2
    assert result["protein_g"]["mae"] == 1


def test_oracle_diagnostic_selects_only_ground_truth_present_slots():
    assert select_present_ingredients(
        {"rice": 120.0, "beans": 40.0, "unlabeled": 500.0},
        ["rice", "beans"],
    ) == {"rice": 120.0, "beans": 40.0}


def test_oracle_diagnostic_abstains_if_slot_missing():
    assert select_present_ingredients({"rice": 120.0}, ["rice", "beans"]) is None
