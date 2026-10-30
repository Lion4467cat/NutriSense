"""07d: derive data/indb_recipes.yaml from the INDB recipe capstone files.

Sources (downloaded manually, nothing bundled):
  https://github.com/lindsayjaacks/Indian-Nutrient-Databank-INDB-
    recipes.xlsx         - raw ingredient rows per recipe (amount + unit)
    INDB.xlsx            - master nutrient table, per-100 g + per-serving
    recipes_names.xlsx   - validated recipe names

Honesty rules honored here (ticket 07d "composition-share / per-100 g
nutrient audit; invisible-component distribution rule"):
  - composition shares are resolved ONLY from rows whose unit converts to
    grams without a hidden assumption: g and kg directly; ml at the recorded
    water approximation (1 g/ml, flagged in the meta block); tsp/tbsp/cup/
    pinch/nos/... stay UNRESOLVED (they carry per-substance conversions in
    Units.xlsx that we do not replicate or bundle).
  - every recipe carries a raw-gram resolution audit (resolved mass and
    fraction) so callers know how much of the composition is actually
    gram-backed.
  - invisibility: the rule from docs/research/general-indian-dish-method.md
    section 7 (oil/spices/salt/water are not segmentable on the plate) is
    materialized as a `visible` flag per ingredient row plus per-recipe
    visible/invisible resolved mass, so the serving code can distribute
    invisible components proportional to the visible carrier mass.
  - energy sanity per recipe: Atwater-style 4/4/9 check vs the reported
    energy_kcal (expected to diverge somewhat because INDB applies nutrient
    retention factors) — audit-only, never a gate.
  - nothing is redistributed: the artifact is regenerated from the source
    xlsx files; use-with-citation posture like WED (docs/licenses.md).

Run: .venv/bin/python -m tools.import_indb_recipes \
       --recipes /tmp/indb/recipes.xlsx --indb /tmp/indb/INDB.xlsx \
       [--names /tmp/indb/recipes_names.xlsx] [--out data/indb_recipes.yaml]
"""
from __future__ import annotations

import argparse
import datetime as dt
from collections import OrderedDict
from pathlib import Path

import openpyxl
import yaml

OUT_DEFAULT = Path("data/indb_recipes.yaml")
NAMES_URL = ("https://github.com/lindsayjaacks/"
             "Indian-Nutrient-Databank-INDB-/raw/main/recipes_names.xlsx")
RECIPES_URL = ("https://github.com/lindsayjaacks/"
               "Indian-Nutrient-Databank-INDB-/raw/main/recipes.xlsx")
INDB_URL = ("https://github.com/lindsayjaacks/"
            "Indian-Nutrient-Databank-INDB-/raw/main/INDB.xlsx")

WATER_APPROX = 1.0  # g/ml assumed for ml-resolved rows (recorded in meta)

yaml.SafeDumper.add_representer(
    OrderedDict, lambda dumper, data: dumper.represent_dict(data.items()))

MACROS = ("energy_kcal", "energy_kj", "carb_g", "protein_g", "fat_g",
          "freesugar_g", "fibre_g")

# Invisible-on-the-plate ingredient classes (method doc section 7:
# "oil, spices, salt dissolved in gravy"); matched on the normalized
# ingredient name, not the food code.
INVISIBLE_PATTERNS = (
    "salt", "water", "oil", "ghee", "butter", "fat", "masala", "chilli powder",
    "turmeric", "cumin", "coriander powder", "asafoetida", "pepper", "essence",
    "colour", "color", "spice", "soda", "garam", "cardamom", "cloves",
    "cinnamon", "curry leaves", "mustard seeds", "fenugreek", "ginger",
    "garlic",
)
VISIBLE_OVERRIDES = ("ginger ale", "garlic bread", "pepper water")


def norm(name: str) -> str:
    return " ".join(str(name).lower().split())


def is_invisible(ingredient_name: str) -> bool:
    n = norm(ingredient_name)
    if any(ov in n for ov in VISIBLE_OVERRIDES):
        return False
    return any(p in n for p in INVISIBLE_PATTERNS)


def amount_to_g(amount: object, unit: object) -> tuple[float | None, str]:
    """Resolve a raw amount + unit to grams, or (None, reason)."""
    try:
        a = float(str(amount))
    except (TypeError, ValueError):
        return None, "no_amount"
    unit = "" if unit is None else str(unit).strip().lower().rstrip(".")
    if unit == "g":
        return a, "g"
    if unit == "kg":
        return a * 1000.0, "kg"
    if unit == "ml":
        return round(a * WATER_APPROX, 2), "ml_as_1g_per_ml"
    if unit == "l":
        return round(a * 1000.0 * WATER_APPROX, 2), "l_as_1g_per_ml"
    return None, f"unit_unsupported:{unit or '(blank)'}"


def _round(v: object, nd: int = 4) -> float | None:
    if v is None or isinstance(v, str):
        return None
    try:
        return round(float(str(v)), nd)
    except (TypeError, ValueError):
        return None


def read_indb(path: str) -> "OrderedDict[str, dict]":
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["Nutrient Data"]
    rows = ws.iter_rows(values_only=True)
    hdr = list(next(rows))
    idx = {h: i for i, h in enumerate(hdr) if h}
    out: "OrderedDict[str, dict]" = OrderedDict()
    for r in rows:
        code = str(r[idx["food_code"]]).strip() if r[idx["food_code"]] else None
        if not code:
            continue
        out[code] = {
            "name": str(r[idx["food_name"]]).strip(),
            "source": str(r[idx["primarysource"]]).strip() if r[idx["primarysource"]] else None,
            "per_100g": {m: _round(r[idx[m]]) for m in MACROS if m in idx},
            "per_serving": {m: _round(r[idx["unit_serving_" + m]]) for m in MACROS if "unit_serving_" + m in idx},
            "servings_unit": str(r[idx["servings_unit"]]).strip() if r[idx["servings_unit"]] else None,
        }
    return out


def read_names(path: str | None) -> "OrderedDict[str, dict]":
    if path is None:
        return OrderedDict()
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = ws.iter_rows(values_only=True)
    hdr = [h for h in next(rows)]
    idx = {h: i for i, h in enumerate(hdr) if h}
    out: "OrderedDict[str, dict]" = OrderedDict()
    for r in rows:
        code = str(r[idx["recipe_code"]]).strip() if r[idx["recipe_code"]] else None
        if code:
            out[code] = {
                "recipe_name": str(r[idx["recipe_name"]]).strip(),
                "primarysource": str(r[idx["primarysource"]]).strip() if r[idx["primarysource"]] else None,
            }
    return out


def atwater_kcal_macros(per100: dict) -> float | None:
    carb, prot, fat = per100.get("carb_g"), per100.get("protein_g"), per100.get("fat_g")
    if carb is None or prot is None or fat is None:
        return None
    return round(4.0 * carb + 4.0 * prot + 9.0 * fat, 2)


def read_recipe_rows(path: str) -> tuple["OrderedDict[str, list[dict]]", "OrderedDict[str, str]"]:
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["Sheet1"]
    rows = ws.iter_rows(values_only=True)
    hdr = list(next(rows))
    idx = {h: i for i, h in enumerate(hdr) if h}
    per_recipe: "OrderedDict[str, list[dict]]" = OrderedDict()
    names: "OrderedDict[str, str]" = OrderedDict()
    for r in rows:
        code = str(r[idx["recipe_code"]]).strip() if r[idx["recipe_code"]] else None
        if not code:
            continue
        names.setdefault(code, str(r[idx["recipe_name"]]).strip())
        ing_name_org = str(r[idx["ingredient_name_org"]]).strip()
        per_recipe.setdefault(code, []).append({
            "name": ing_name_org,
            "food_name": str(r[idx["food_name"]]).strip(),
            "food_code": str(r[idx["food_code"]]).strip(),
            "amount": _round(r[idx["amount"]], 2),
            "unit": str(r[idx["unit"]]).strip() if r[idx["unit"]] is not None else "",
            "amount_g": None,
            "g_resolution": None,
            "visible": not is_invisible(ing_name_org),
        })
    return per_recipe, names


def audit_energy(per100: dict) -> dict:
    rep = per100.get("energy_kcal")
    calc = atwater_kcal_macros(per100)
    if rep is None or calc is None or rep <= 0:
        return {"atwater_kcal": calc, "atwater_delta_pct": None}
    return {"atwater_kcal": calc,
            "atwater_delta_pct": round((calc - rep) / rep * 100.0, 1)}


def build(args: argparse.Namespace) -> dict:
    indb = read_indb(args.indb)
    names: dict = read_names(args.names)
    per_recipe, recipe_names = read_recipe_rows(args.recipes)

    recipes_meta: "OrderedDict[str, dict]" = OrderedDict()
    mass_resolved_total = 0.0
    mass_total_rows = 0
    mass_resolved_rows = 0
    energy_audits: list[float] = []
    invisible_rows_total = 0

    for code, ings in per_recipe.items():
        row = indb.get(code)
        if row is None:
            continue  # name/ingredient sheet row with no nutrient row
        resolved_g = 0.0
        invisible_g = 0.0
        n_resolved = 0
        rows_out = []
        for ing in ings:
            g, how = amount_to_g(ing["amount"], ing["unit"])
            mass_total_rows += 1
            if g is not None:
                resolved_g += g
                n_resolved += 1
                mass_resolved_rows += 1
                mass_resolved_total += g
                if not ing["visible"]:
                    invisible_g += g
                    invisible_rows_total += 1
            rows_out.append({
                "name": ing["name"], "food_name": ing["food_name"],
                "food_code": ing["food_code"],
                "amount": ing["amount"], "unit": ing["unit"],
                "amount_g": g, "g_resolution": how if g is not None else None,
                "visible": ing["visible"],
            })
        eng_audit = audit_energy(row["per_100g"])
        if eng_audit["atwater_delta_pct"] is not None:
            energy_audits.append(abs(eng_audit["atwater_delta_pct"]))
        recipes_meta[code] = {
            "name": names.get(code, {}).get("recipe_name", row["name"]),
            "source": row["source"],
            "servings_unit": row["servings_unit"],
            "per_100g": row["per_100g"],
            "per_serving": row["per_serving"],
            "ingredients": rows_out,
            "mass_audit_g": {
                "resolved_total": round(resolved_g, 1),
                "invisible_resolved": round(invisible_g, 1),
                "visible_resolved": round(resolved_g - invisible_g, 1),
                "resolved_rows": n_resolved,
                "total_rows": len(rows_out),
            },
            "energy_audit": eng_audit,
        }

    return {
        "meta": {
            "dataset": "Indian Nutrient Databank (INDB)",
            "publisher": "Jaacks et al. (anuvaad.org.in), built on ICMR-NIN IFCT 2017",
            "source_urls": {"recipes_xlsx": RECIPES_URL,
                             "indb_xlsx": INDB_URL,
                             "recipes_names_xlsx": NAMES_URL},
            "use_with_citation": True,
            "redistribution":
                "not permitted/rethink before bundling; regenerate from source "
                "instead (docs/licenses.md posture)",
            "extraction_tool": "tools/import_indb_recipes.py",
            "extracted": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%MZ"),
            "water_ml_approx_g_per_ml": WATER_APPROX,
            "unit_policy":
                "amount_g resolved only from g/kg (and ml/L at the recorded "
                "water approximation); tsp/tbsp/cup/pinch/nos/... left "
                "unresolved with g_resolution=None",
            "audit_summary": {
                "recipes": len(recipes_meta),
                "ingredient_rows": mass_total_rows,
                "resolved_rows": mass_resolved_rows,
                "resolved_frac_rows": round(mass_resolved_rows / max(mass_total_rows, 1), 3),
                "resolved_mass_g": round(mass_resolved_total, 1),
                "invisible_rows": invisible_rows_total,
                "atwater_median_abs_delta_pct":
                    sorted(energy_audits)[len(energy_audits) // 2] if energy_audits else None,
            },
        },
        "invisible_rule": {
            "statement":
                "Components that are not segmentable on the plate (oil, ghee, "
                "spices, salt, cooking water) are distributed over the visible "
                "carrier components proportional to their resolved raw-gram "
                "mass; their nutrients reach the serving estimate through the "
                "recipe-level per-100 g table, never as separate visible "
                "masks.",
            "classes": list(INVISIBLE_PATTERNS),
            "applies_when": "per_recipe_<code>.mass_audit_g.invisible_resolved > 0",
        },
        "recipes": recipes_meta,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recipes", required=True, help="path to recipes.xlsx")
    ap.add_argument("--indb", required=True, help="path to INDB.xlsx")
    ap.add_argument("--names", default=None, help="path to recipes_names.xlsx")
    ap.add_argument("--out", default=str(OUT_DEFAULT))
    args = ap.parse_args()

    doc = build(args)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        yaml.safe_dump(doc, f, sort_keys=False, allow_unicode=True,
                       default_flow_style=False)
    s = doc["meta"]["audit_summary"]
    print(f"wrote {out_path}: {s['recipes']} recipes, "
          f"{s['ingredient_rows']} ingredient rows "
          f"({s['resolved_frac_rows']:.0%} gram-resolved), "
          f"{s['invisible_rows']} invisible rows; "
          f"Atwater median |delta| = {s['atwater_median_abs_delta_pct']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
