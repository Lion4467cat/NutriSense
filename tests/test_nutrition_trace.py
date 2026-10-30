"""Nutrition provenance is computed from the same mappings as estimates."""
from __future__ import annotations

from config import load_menu, load_nutrients
from engine.mc import aggregate_meal, sample_nutrients


def test_nutrition_provenance_reconciles_component_calculation():
    dish = load_menu()["dishes"]["rice_sambar"]
    portion = {
        "grams": 200.0,
        "components_g": {name: 100.0 * float(spec.get("share", 1.0))
                         for name, spec in dish["components"].items()},
        "sigma_grams_rel": 0.2,
    }
    out = sample_nutrients(portion, dish, n=20, seed=17)
    trace = out["nutrition_provenance"]
    assert len(trace["table_sha256"]) == 64
    assert set(trace["components"]) == set(dish["components"])
    foods = load_nutrients()
    expected_kcal = 0.0
    expected_protein = 0.0
    for name, spec in dish["components"].items():
        row = trace["components"][name]
        table = foods[spec["generic_id"]]
        assert row["generic_id"] == spec["generic_id"]
        assert row["kcal_per_100g"] == table["kcal_per_100g"]
        assert row["protein_g_per_100g"] == table["protein_g_per_100g"]
        assert row["status"] == table["status"]
        assert row["source"] == table["source"]
        expected_kcal += row["grams"] * row["kcal_per_100g"] / 100
        expected_protein += row["grams"] * row["protein_g_per_100g"] / 100
    assert abs(sum(r["kcal_contribution"]
                   for r in trace["components"].values()) - expected_kcal) < 1e-3
    assert abs(sum(r["protein_g_contribution"]
                   for r in trace["components"].values()) - expected_protein) < 1e-3


def test_multi_item_trace_keeps_same_components_from_both_dishes():
    dish = load_menu()["dishes"]["rice_sambar"]
    portion = {
        "grams": 200.0,
        "components_g": {name: 100.0 * float(spec.get("share", 1.0))
                         for name, spec in dish["components"].items()},
        "sigma_grams_rel": 0.2,
    }
    first = sample_nutrients(portion, dish, n=20, seed=17,
                             component_prefix="dish_a")
    second = sample_nutrients(portion, dish, n=20, seed=18,
                              component_prefix="dish_b")
    merged = aggregate_meal([first, second])
    keys = set(merged["nutrition_provenance"]["components"])
    assert keys == {
        f"dish_{dish_name}:{component}"
        for dish_name in ("a", "b")
        for component in dish["components"]
    }
