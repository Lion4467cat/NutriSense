"""Nutrient table access (S4). Values from data/nutrients.yaml only —
read and cached by config; this module owns the lookup semantics."""
from config import load_nutrients


def nutrient_value(generic_id, nutrients=None):
    """(kcal_per_100g, protein_g_per_100g, status) for a generic food id."""
    foods = nutrients if nutrients is not None else load_nutrients()
    if generic_id not in foods:
        raise KeyError(f"no nutrient row for generic_id {generic_id!r}")
    row = foods[generic_id]
    return float(row["kcal_per_100g"]), float(row["protein_g_per_100g"]), row.get("status", "assumed")


def assumed_nutrient_ids(dish, nutrients=None):
    """Generic ids used by this dish whose nutrient row is not literature."""
    foods = nutrients if nutrients is not None else load_nutrients()
    out = []
    for spec in (dish.get("components") or {}).values():
        gid = spec.get("generic_id")
        if gid and gid in foods and foods[gid].get("status") != "literature":
            out.append(gid)
    return sorted(set(out))
