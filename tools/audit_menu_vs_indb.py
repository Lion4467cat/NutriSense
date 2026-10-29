"""07d menu-vs-INDB nutrient audit (audit table, never a gate; method doc 6.4).

Matches the menu's generic_id nutrient assumptions (data/nutrients.yaml,
many `status: assumed`) against actual INDB recipes by name, and writes
data/reports/menu_indb_audit.yaml. Calibrates nothing: assumed values get
flagged with observed deltas so a later ledger pass decides whether to adopt
the INDB numbers.

Run: .venv/bin/python -m tools.audit_menu_vs_indb
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import yaml

from models.recipe_table import load_recipes, recipe_entry

NUTRIENTS_PATH = Path("data") / "nutrients.yaml"
REPORT_PATH = Path("data") / "reports" / "menu_indb_audit.yaml"

# generic_id -> INDB name substrings that plausibly denote it. Audit aid
# only: matches print with their deltas so a human confirms the adoption.
MATCHES = {
    "rice_boiled": ["sambar", "rasam", "rice"],
    "sambar": ["sambar"],
    "vegetable_rice": ["vegetable rice", "vegetable pulao", "veg pulao"],
    "bisibelebath": ["bisibele", "bisi bele", "sambarsaadam"],
    "curd": ["curd", "thaggu mosaru", "mosaru"],
    "rice_dal": ["mudda pappu", "dal rice"],
}

NUTRIENT_KEYS = ("kcal_per_100g", "protein_g_per_100g")
INDB_KEYS = ("energy_kcal", "protein_g")


def best_match(name_hints: list[str], title: str | None = None) -> tuple[str | None, float]:
    """Best INDB recipe for the hints; score = longest hint hit."""
    recipes = load_recipes()["recipes"]
    best_code, best_score = None, 0.0
    for code, entry in recipes.items():
        n = entry["name"].lower()
        if title and title.lower() not in n:
            continue
        for hint in name_hints:
            if hint in n and len(hint) > best_score:
                best_score = len(hint)
                best_code = code
    return best_code, best_score


def main() -> int:
    nut = yaml.safe_load(NUTRIENTS_PATH.read_text())
    rows = []
    for gid, hints in MATCHES.items():
        food = nut["foods"].get(gid)
        if food is None:
            continue
        code, _score = best_match(hints)
        entry = recipe_entry(code) if code is not None else None
        row = {"generic_id": gid, "nutrient_status": food.get("status"),
               "indb_recipe_code": code,
               "indb_recipe_name": entry["name"] if entry else None,
               "assumed": {k: food.get(k) for k in NUTRIENT_KEYS}}
        if code is not None and entry is not None:
            per100 = entry["per_100g"]
            row["indb_per_100g"] = {k: per100.get(k) for k in INDB_KEYS}
            deltas = {}
            for ours, theirs in (("kcal_per_100g", "energy_kcal"),
                                 ("protein_g_per_100g", "protein_g")):
                a, b = food.get(ours), per100.get(theirs)
                deltas[ours] = (round((a - b) / b * 100.0, 1)
                                if a is not None and b else None)
            row["delta_pct"] = deltas
            row["note"] = ("status: assumed values — audit-only; adopting "
                           "INDB numbers needs its own honesty pass")
        rows.append(row)

    report = {
        "generated": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%MZ"),
        "kind": "audit-only; never verdict/policy input",
        "source": "data/indb_recipes.yaml (INDB; use-with-citation)",
        "rows": rows,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        yaml.safe_dump(report, f, sort_keys=False, allow_unicode=True)
    print(f"wrote {REPORT_PATH}")
    for r in rows:
        print(f"  {r['generic_id']:>15} status={r['nutrient_status']} "
              f"-> {r['indb_recipe_code']}: {r['indb_recipe_name']} "
              f"delta={r.get('delta_pct')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
