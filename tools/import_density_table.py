"""07c: derive data/ingredient_densities.yaml from the FAO/INFOODS Density
Database v2 (XLSX, downloaded 2026-10-29 from
https://www.fao.org/fileadmin/templates/food_composition/documents/density_DB_v2_0_final-1__1_.xlsx).

House posture (docs/licenses.md): use-with-citation. ONLY the exact cited
rows a state references land in the artifact (row text + density + BiblioID
+ source sheet row number); the source file itself is never committed.

Usage:
  uv run --python /usr/bin/python3 --with openpyxl python -m \
      tools.import_density_table --src /tmp/density_DB_v2.xlsx

Deterministic: the same XLSX always regenerates the same artifact. The
`audit:` block cross-checks the currently-served assumed densities
(data/menu.yaml + data/wed_dishes.yaml components) against the FAO values —
an audit, never a gate (ticket 07c); serving values stay untouched until a
pre-registered ledger experiment changes them.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
from pathlib import Path

import openpyxl
import yaml

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Ingredient-state curation: every generic_id the serving stack reads
# (data/menu.yaml + data/wed_dishes.yaml) mapped to its FAO evidence rows.
# `primary` = the row whose value the audit cites (exact sheet text);
# `alternates` = other cited rows shown for context; a state with neither
# gets `status: assumed` and cites only nearest-analogue reference rows.
# `proxy: True` marks states whose primary row is a NEAREST-ANALOGUE (not
# the same food state) — they keep the cited value but carry status
# 'assumed' with rule 'analogue_transfer', never 'literature'.
STATES: dict[str, dict] = {
    # --- grains -----------------------------------------------------------
    "rice_boiled": {
        "primary": "Rice, boiled",
        "alternates": ["Rice, white, boiled", "Rice, hulled"],
        "note": "plated boiled-rice bulk density; matches the pantry 0.73 g/ml class"},
    "rice_oiled": {
        "primary": "Rice, boiled with fat",
        "alternates": ["Rice + potato/banana"],
        "note": "oil-dressed rice (pulao-style plated)"},
    "cereal_pulse_onepot": {
        "primary": "Githeri (muthugo + beans) + onion, boiled with fat",
        "alternates": ["Rice + beans + potato/banana",
                       "Githeri (muthugo + beans) + vegetable"],
        "proxy": True,
        "note": "cereal + pulse one-pot serving (bisi bele bath analogue)"},
    # --- pulses / liquids -------------------------------------------------
    "dal_thick": {
        "primary": "Lentils, green, small, boiled",
        "alternates": [],
        "note": "thick cooked whole/pureed lentils (muddha-pappu style)"},
    "dal_soup": {
        "primary": "Bean soup",
        "alternates": ["Soup, mixed"],
        "proxy": True,
        "note": "pourable lentil stew (sambar/rasam analogue)"},
    "veg_stew": {
        "primary": "Githeri (muthugo + beans) + vegetable",
        "alternates": ["Mataha (maize stew), beans + vegetable"],
        "proxy": True,
        "note": "boiled vegetable stew proxy"},
    # --- dairy -------------------------------------------------------------
    "curd": {
        "primary": "Milk, acidophilus cultured",
        "alternates": ["Milk, buttermilk"],
        "proxy": True,
        "note": "cultured-milk proxy: FAO v2 has no 'curd/yogurt' row; "
                "value carries the proxy status, NOT literature-grade for curd"},
    "milk": {
        "primary": "Milk, cow, whole",
        "alternates": ["Milk, liquid, partially skimmed"],
        "note": ""},
    "milk_sweet": {
        "primary": "Milk, cow, whole",
        "alternates": [],
        "proxy": True,
        "note": "milk-based sweets (payasam/kheer) inherit the whole-milk proxy"},
    # --- fats / small dry components ----------------------------------------
    "cooking_oil": {
        "primary": "Oil, other than palmoil",
        "alternates": ["Oil, sunflower", "Cooking oil, sima"],
        "note": "generic vegetable cooking oil 0.88-0.92 g/ml band"},
    # --- nearest-analogue only (status: assumed) ------------------------------
    "papad_fried": {
        "primary": None,
        "alternates": [],
        "note": "no FAO analogue for a crisp-fried lentil wafer stack; serving "
                "assumption stays (porous stacking dominates)"},
    "boondi_fried": {"primary": None, "alternates": [],
                     "note": "no FAO analogue for fried chickpea boondi"},
    "salad_raw": {
        "primary": "Salad, green, leaves, raw",
        "alternates": ["Salad dressing"],
        "proxy": True,
        "note": "loose-leaf packing 0.06 g/ml is NOT the kachumber/mixed "
                "salad state — kept as leafy-analogue context only; the "
                "serving value stays assumed"},
    "pickle_oily": {"primary": None, "alternates": [],
                    "note": "no FAO analogue for oily Indian pickle"},
    "veg_fried_dry": {
        "primary": "Onions, fried, cubed",
        "alternates": [],
        "proxy": True,
        "note": "dry-fried vegetable analogue; serving assumed value stays"},
    "chutney": {
        "primary": "Sauce, soy",
        "alternates": [],
        "proxy": True,
        "note": "condiment paste proxy; serving assumed value stays"},
    "gravy_curry": {
        "primary": "Soup, mixed",
        "alternates": ["Mataha (maize stew), maize + banana/potato + vegetable"],
        "proxy": True,
        "note": "curry/gravied mix analogue, wide FAO spread 0.86-1.10"},
    "papaya_fruit": {"primary": None, "alternates": [],
                     "note": "DB has no ripe-papaya row (only 'Paw Paw, "
                             "unripe' 0.56 KEN — vegetable-usage density, "
                             "not a ripe-fruit analogue); serving value stays assumed"},
    "banana_fruit": {"primary": None, "alternates": [],
                     "note": "no fresh-fruit rows for banana in FAO v2; "
                             "serving value stays assumed"},
    "melon_fruit": {"primary": None, "alternates": [],
                    "note": "no fresh-melon rows in FAO v2; serving value stays assumed"},
    "watermelon_fruit": {"primary": None, "alternates": [],
                         "note": "no fresh-watermelon rows in FAO v2; "
                                 "serving value stays assumed"},
    "salt": {"primary": "Salt, table", "alternates": [], "note": ""},
    "sugar": {"primary": "Sugar", "alternates": [], "note": ""},
}

# Serving values being audited (extracted verbatim 2026-10-29 from
# data/menu.yaml components and data/wed_dishes.yaml components).
SERVING_AUDIT = [
    ("rice_boiled", 0.75),          # menu rice_sambar.rice / wed veg-pulao etc.
    ("sambar", 1.03),               # menu rice_sambar.sambar (dal_soup state)
    ("vegetable_rice", 0.85),       # menu / wed (rice_oiled state)
    ("bisibelebath", 0.90),         # menu (cereal_pulse_onepot state)
    ("dal_curry", 1.00),            # wed (dal_thick state)
    ("sambar_type", 1.03),          # wed rasam/sambar pour-dish rows
    ("rasam_type", 1.00),           # wed (dal_soup state)
    ("chutney_type", 1.00),         # wed (chutney state)
    ("raita_type", 0.98),           # wed (curd state)
    ("curd", 1.03),                 # wed curd dish
    ("papad_type", 0.40),           # wedge snack rows (papad_fried state)
    ("boondi_type", 0.40),          # wed snack rows (boondi_fried state)
    ("salad_type", 0.50),           # wed salad rows (salad_raw state)
    ("pickle_type", 1.00),          # wed (pickle_oily state)
    ("vegetable_curry", 0.95),      # wed curry rows (veg_stew state)
    ("vegetable_fry", 0.90),        # wed fry rows (veg_fried_dry state)
    ("chicken_biryani_type", 0.85),  # wed biryani rows (cereal_pulse_onepot analogue)
    ("payasam_type", 1.05),         # wed (milk_sweet state)
    ("banana_fruit", 0.94),         # wed
    ("papaya_fruit", 0.95),         # wed
    ("muskmelon_fruit", 0.93),      # wed (melon_fruit state)
    ("watermelon_fruit", 0.92),     # wed
]

# serving generic_id -> density-table state
SERVING_TO_STATE = {
    "rice_boiled": "rice_boiled",
    "sambar": "dal_soup",
    "sambar_type": "dal_soup",
    "rasam_type": "dal_soup",
    "vegetable_rice": "rice_oiled",
    "bisibelebath": "cereal_pulse_onepot",
    "dal_curry": "dal_thick",
    "chutney_type": "chutney",
    "chicken_biryani_type": "cereal_pulse_onepot",
    "raita_type": "curd",
    "curd": "curd",
    "papad_type": "papad_fried",
    "boondi_type": "boondi_fried",
    "salad_type": "salad_raw",
    "pickle_type": "pickle_oily",
    "vegetable_curry": "veg_stew",
    "vegetable_fry": "veg_fried_dry",
    "payasam_type": "milk_sweet",
    "banana_fruit": "banana_fruit",
    "papaya_fruit": "papaya_fruit",
    "muskmelon_fruit": "melon_fruit",
    "watermelon_fruit": "watermelon_fruit",
}

VAL_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)")


def parse_value(raw) -> dict:
    s = str(raw)
    m = VAL_RE.match(s)
    if not m:
        return {"value": None, "raw": s}
    return {"value": float(m.group(1)), "raw": s}


def load_rows(xlsx_path: Path) -> tuple[list[tuple], str]:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb["Density DB"]
    rows = []
    for i, r in enumerate(ws.iter_rows(values_only=True), 1):
        rows.append((i, r[0], r[1], r[3]))
    with open(xlsx_path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    return rows, digest


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="path to density_DB_v2_*.xlsx")
    ap.add_argument("--out", default=str(DATA_DIR / "ingredient_densities.yaml"))
    args = ap.parse_args()

    rows, digest = load_rows(Path(args.src))
    by_name: dict[str, list[tuple]] = {}
    for rownum, name, dens, bib in rows:
        if name is None or dens is None:
            continue
        by_name.setdefault(str(name).strip(), []).append(
            (rownum, parse_value(dens), str(bib).strip() if bib else None))

    now = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%MZ")
    states = {}
    for state, spec in STATES.items():
        entry: dict = {}
        used = []
        primary = spec.get("primary")
        if primary and primary in by_name:
            rownum, val, bib = by_name[primary][0]
            proxy = bool(spec.get("proxy"))
            entry = {"density_g_ml": val["value"], "density_raw": val["raw"],
                     "rule": "analogue_transfer" if proxy else "literature",
                     "status": "assumed" if proxy else "literature",
                     "provenance": (
                         ("nearest-analogue: " if proxy else "direct: ") +
                         f"FAO/INFOODS density DB v2 sheet 'Density DB' row "
                         f"{rownum}: \"{primary}\" (BiblioID {bib})")}
            used.append((primary, rownum, val, bib))
        else:
            extra = (" nearest-analogue rows are cited below for context only"
                     if spec.get("alternates") else
                     " no FAO analogue exists — serving value stays assumed")
            entry = {"rule": "assumed_transfer", "status": "assumed",
                     "provenance": ("no FAO/INFOODS v2 row matched this state;"
                                    + extra)}
        alts = []
        for alt in spec.get("alternates", []):
            if alt in by_name:
                rownum, val, bib = by_name[alt][0]
                alts.append({"row": alt, "density_g_ml": val["value"],
                             "density_raw": val["raw"], "biblio_id": bib,
                             "xlsx_row": rownum})
                used.append((alt, rownum, val, bib))
        if alts:
            entry["reference_rows"] = alts
        if spec.get("note"):
            entry["note"] = spec["note"]
        states[state] = entry

    audit = []
    for gid, served in SERVING_AUDIT:
        state = SERVING_TO_STATE.get(gid)
        st = states.get(state, {})
        if "density_g_ml" in st:
            fao = st["density_g_ml"]
            delta = round((served - fao) / fao * 100.0, 1)
            value_status = st["rule"]  # literature | analogue_transfer
        else:
            fao, delta, value_status = None, None, "assumed"
        audit.append({
            "serving_id": gid, "state": state,
            "served_density_g_ml": served, "fao_density_g_ml": fao,
            "value_status": value_status,
            "delta_pct": delta,
            "status": "assumed" if fao is None else "audit_only",
        })

    # menu aliases the stack reads but whose serving rows were listed above
    doc = {
        "source": {
            "dataset": "FAO/INFOODS Density Database, Version 2 (2012)",
            "publisher": "FAO/INFOODS",
            "url": ("https://www.fao.org/fileadmin/templates/food_composition/"
                    "documents/density_DB_v2_0_final-1__1_.xlsx"),
            "landing_page": ("https://www.fao.org/infoods/infoods/tables-and-"
                             "databases/faoinfoods-databases/en/"),
            "fetched": "2026-10-29",
            "xlsx_sha256": digest,
            "extraction_tool": "tools/import_density_table.py",
            "extracted_at": now,
        },
        "license": {
            "posture": "use-with-citation — FAO/INFOODS compiled the values "
                       "from third-party food-composition tables; only the "
                       "cited rows (row text + value + BiblioID) are "
                       "reproduced here, one per reference, never the sheet",
            "citation": "FAO/INFOODS. Density Database Version 2.0 (2012). "
                        "FAO, Rome.",
        },
        "role": ("provenanced density priors for the ingredient-state alphabet "
                 "(ticket 07c). The serving stack keeps reading "
                 "density_g_ml from the menu/yaml dish entries; this table is "
                 "the audit + cite layer behind those values until a "
                 "pre-registered ledger experiment changes them."),
        "learned_residuals": ("none yet — per-state residuals from measured "
                              "plates land with future ledger experiments; "
                              "the density_sigma_pct MC term stays the "
                              "uncertainty vehicle in the meantime"),
        "states": states,
        "audit": {
            "role": ("cross-check of currently served assumed densities vs "
                     "FAO literature rows; audit-only, never auto-applied"),
            "entries": audit,
        },
    }

    with open(args.out, "w") as f:
        f.write("# Ingredient-state density priors (ticket 07c) — derived from\n"
                "# the FAO/INFOODS Density Database v2 by "
                "tools/import_density_table.py.\n"
                "# Regenerate: uv run --python /usr/bin/python3 --with openpyxl \\\n"
                "#   python -m tools.import_density_table --src <xlsx>\n")
        yaml.safe_dump(doc, f, sort_keys=False, width=100)

    n_lit = sum(1 for s in states.values() if s.get("rule") == "literature")
    print(f"wrote {args.out}: {len(states)} states ({n_lit} literature, "
          f"{len(states) - n_lit} assumed), {len(audit)} audit entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
