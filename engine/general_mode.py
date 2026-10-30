"""General-mode ingredient-compositional serving + uncertainty routing (07e).

For an OFF-MENU recognized dish only (School-mode dishes never reach this
module — spec 002 decision 1), try the ingredient-compositional route of
`docs/research/general-indian-dish-method.md` §4/§5:

  1. `models.ingredient_head.IngredientHead` predicts a per-ingredient grams
     profile from the frame.
  2. Match that profile against the INDB recipe table (ledger 011) — cosine
     over the recipe's gram-resolved ingredient rows, normalised names.
  3. Match ≥ threshold -> the recipe supplies composition: predicted visible
     carrier grams feed `distribute_invisible` (oil/spices/water ride their
     carriers), MC rides the recipe's per-100 g nutrients via a synthetic
     dish + nutrients override (`status: recipe` -> the ID shows up in
     `assumed_nutrients`, never silently trusted).
  4. Uncertainty routing: a matched plate still carries inferred composition
     (`composition_inferred` flag); <50% of the resolved recipe mass covered
     by predicted slots, or predicted mass the recipe cannot resolve, marks
     the estimate NOT confident -> widened sigma_rel + `unknown_state_widening`.

NO viable match, or no head checkpoint -> callers get None and keep the
existing off-menu path (dish-slot head + generic table) byte-for-byte, so the
ledger 013 fallback criterion holds while 07b is pending.

Pre-registered constants (ledger 013): match threshold 0.5, sigma_rel 0.35,
widened 0.45 — defaults pending a measured calibration entry.
"""
from __future__ import annotations

import re

from models import recipe_table

# Ledger 013 pre-registered constants.
MATCH_THRESHOLD = 0.5          # minimum cosine over shared resolved slots
CONFIDENT_COVERAGE = 0.5       # matched grams / resolved recipe mass
SIGMA_REL_MATCHED = 0.35
SIGMA_REL_UNKNOWN = 0.45
_NAME_CLEAN_RE = re.compile(r"[^a-z0-9 ]+")


def _norm(name: str) -> str:
    return _NAME_CLEAN_RE.sub("", str(name).lower().strip())


def recipe_profile(entry: dict) -> dict[str, float]:
    """Normalised ingredient name -> gram-resolved mass for one recipe."""
    out: dict[str, float] = {}
    for row in entry.get("ingredients", []):
        g = row.get("amount_g")
        if g is None:
            continue
        key = _norm(row.get("name", ""))
        if key:
            out[key] = out.get(key, 0.0) + float(g)
    return out


def match_recipe(profile: dict[str, float]) -> tuple[str | None, float]:
    """Best INDB recipe (code, cosine) for a predicted ingredient profile."""
    best_code, best_cos = None, 0.0
    for code, entry in recipe_table.load_recipes()["recipes"].items():
        ref = recipe_profile(entry)
        if not ref:
            continue
        shared = set(ref) & set(profile)
        if not shared:
            continue
        num = sum(profile[k] * ref[k] for k in shared)
        den_a = sum(v * v for v in profile.values()) ** 0.5
        den_b = sum(v * v for v in ref.values()) ** 0.5
        if den_a <= 0 or den_b <= 0:
            continue
        cos = num / (den_a * den_b)
        if cos > best_cos:
            best_code, best_cos = code, cos
    return best_code, best_cos


def serve_with_head(image_bgr, head, dish: dict, dish_info: dict,
                    predict=None) -> dict | None:
    """Ingredient-compositional serving for ONE off-menu dish.

    head: IngredientHead or a duck-typed stand-in (tests); predict(image_bgr)
    defaults to head.predict. Returns {"portion", "nutrition", "confident"}
    for the wire assembly, or None when the predicted profile does not match
    any recipe (caller falls back unchanged). Failures raise; the pipeline
    converts them exactly like a stage failure into the wire contract.
    """
    from engine.mc import sample_nutrients
    from models.recipe_table import distribute_invisible

    predict_fn = predict or head.predict
    grams_by_name = predict_fn(image_bgr)
    profile = {_norm(k): float(v) for k, v in grams_by_name.items() if v > 0}
    if not profile:
        return None
    code, cos = match_recipe(profile)
    if code is None or cos < MATCH_THRESHOLD:
        return None
    entry = recipe_table.recipe_entry(code)
    if entry is None:
        return None
    ref = recipe_profile(entry)

    # Visible carriers = predicted grams on slots the recipe resolves; mass
    # the recipe cannot explain stays OUT of the point estimate (it is not
    # part of the resolved recipe) but widens the band and is reported.
    visible, unexplained = {}, 0.0
    for key, g in profile.items():
        if key in ref:
            visible[key] = g
        else:
            unexplained += g
    visible = {k: v for k, v in visible.items() if v > 0}
    if not visible:
        return None
    inflated = distribute_invisible(visible, entry)
    total_visible = float(sum(inflated.values()))
    total = total_visible + unexplained

    coverage = total_visible / max(float(ref.get("__total__", 0.0))
                                   or sum(ref.values()), 1e-9)
    confident = bool(cos >= MATCH_THRESHOLD
                     and coverage >= CONFIDENT_COVERAGE
                     and unexplained / total <= 1.0 - CONFIDENT_COVERAGE)
    sigma = SIGMA_REL_MATCHED if confident else SIGMA_REL_UNKNOWN

    names = list(inflated)
    shares = {n: inflated[n] / total_visible for n in names}
    gid = f"indb_{code}"
    per100 = entry["per_100g"]
    if per100.get("energy_kcal") is None or per100.get("protein_g") is None:
        return None
    synthetic_nutrients = {
        gid: {
            "kcal_per_100g": float(per100["energy_kcal"]),
            "protein_g_per_100g": float(per100["protein_g"]),
            "status": "recipe",
        }
    }
    mc_dish = {
        "components": {n: {"share": shares[n], "generic_id": gid}
                       for n in names},
        "ranges_wider": not confident,
        "nutrition_source": f"indb:{code}",
    }
    portion = {
        "grams": total,
        "volume_ml": total / 1.0,      # recipe-weighted; no depth involved
        "density_eff": 1.0,
        "components_g": {n: round(inflated[n], 1) for n in names},
        "base_method": "ingredient_compositional",
        "scale_tier": "prior",
        "mean_h_mm": None,
        "area_cm2": None,
        "sigma_grams_rel": float(sigma),
        "sigma_rel": {
            "ingredient_head": float(sigma),
            "recipe_match": float(round(cos, 3)),
        },
        "depth_invalid_frac": 0.0,
        "flags": ["ingredient_head_applied", "composition_inferred"]
                 + ([] if confident else ["unknown_state_widening"]),
        "grams_source": "ingredient_head",
        "head_slots": {k: round(v, 2) for k, v in grams_by_name.items()},
        "recipe_match": {"code": code, "name": entry.get("name", code),
                         "cosine": round(cos, 3), "confident": confident,
                         "coverage": round(coverage, 3)},
    }
    mc = sample_nutrients(portion, mc_dish, None,
                          nutrients=synthetic_nutrients)
    nutrition_block = {
        "kcal": mc["kcal"], "protein_g": mc["protein_g"], "grams": mc["grams"],
        "n": mc["n"], "seed": mc["seed"],
        "diagnostics": mc["diagnostics"],
        "assumed_nutrients": mc["assumed_nutrients"],
        "wider_ranges": mc["wider_ranges"],
    }
    return {"portion": portion, "nutrition": nutrition_block,
            "confident": confident}


def ingredient_route(image_bgr, head, dish: dict, dish_info: dict,
                     predict=None) -> dict | None:
    """serve_with_head -> {"portion", "nutrition"} wire-ready dicts, or None
    when there is no viable recipe match (caller keeps the existing path)."""
    out = serve_with_head(image_bgr, head, dish, dish_info, predict=predict)
    if out is None:
        return None
    return {k: out[k] for k in ("portion", "nutrition")}
