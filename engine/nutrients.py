"""Nutrient table access (S4). Values from data/nutrients.yaml only —
read and cached by config; this module owns the lookup semantics."""
import json
from pathlib import Path
from typing import Any
from config import load_nutrients

_INDB_CACHE: dict[str, Any] | None = None

def get_indb_master() -> dict[str, Any]:
    global _INDB_CACHE
    if _INDB_CACHE is None:
        p = Path(__file__).resolve().parents[1] / "data" / "indb_ifct_nutrition_master.json"
        if p.is_file():
            try:
                with open(p) as f:
                    _INDB_CACHE = json.load(f).get("dishes", {})
            except Exception:
                _INDB_CACHE = {}
        else:
            _INDB_CACHE = {}
    return _INDB_CACHE or {}


def nutrient_value(generic_id, nutrients=None):
    """(kcal_per_100g, protein_g_per_100g, status) for a generic food id."""
    foods = nutrients if nutrients is not None else load_nutrients()
    if generic_id not in foods:
        if generic_id.startswith("indb_"):
            dish_key = generic_id[5:]
            entry = get_indb_master().get(dish_key)
            if entry and "per_100g" in entry:
                p100 = entry["per_100g"]
                kcal = float(p100.get("energy_kcal", 180.0))
                prot = float(p100.get("protein_g", 5.0))
                return kcal, prot, "indb_ifct"
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
