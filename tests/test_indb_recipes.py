"""07d test: data/indb_recipes.yaml shape and honesty rules.

Guards the artifact's audit layer: unit-resolution policy (g/kg direct, ml
recorded water-approximation, everything else unresolved), the
invisible-component flag (method doc section 7 rule), the Atwater energy
audit, and the source/provenance meta. Serving code locates recipes by
recipe code and reads per-100g/per-serving tables; nothing here may change
that contract silently. Regenerate the artifact with:
.venv/bin/python -m tools.import_indb_recipes --recipes ... --indb ...
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

DATA = Path(__file__).resolve().parents[1] / "data" / "indb_recipes.yaml"
MACROS = {"energy_kcal", "carb_g", "protein_g", "fat_g"}


@pytest.fixture(scope="module")
def doc():
    return yaml.safe_load(DATA.read_text())


def test_meta_provenance(doc):
    meta = doc["meta"]
    assert meta["dataset"] == "Indian Nutrient Databank (INDB)"
    assert meta["use_with_citation"] is True
    assert "redistribution" in meta
    assert meta["extraction_tool"].startswith("tools/import_indb_recipes.py")
    s = meta["audit_summary"]
    assert s["recipes"] >= 1000
    assert s["atwater_median_abs_delta_pct"] is not None


def test_unit_resolution_policy(doc):
    for r in doc["recipes"].values():
        for ing in r["ingredients"]:
            g, how = ing["amount_g"], ing["g_resolution"]
            unit = (ing["unit"] or "").strip().lower()
            if g is None:
                assert how is None, (r["name"], ing)
                assert unit not in ("g", "kg", "ml", "l"), (r["name"], ing)
            else:
                assert g >= 0
                if unit in ("g", "kg"):
                    assert how in ("g", "kg"), (r["name"], ing)
                elif unit in ("ml", "l"):
                    assert how in ("ml_as_1g_per_ml", "l_as_1g_per_ml"), (r["name"], ing)
                else:
                    raise AssertionError(
                        f"resolved but unsupported unit: {(r['name'], ing)}")
            # full sweep: unit-resolution invariant for every row
            if g is None:
                assert how is None and str(unit) not in ("g", "kg", "ml", "l")
            else:
                assert str(unit) in ("g", "kg", "ml", "l")


def test_mass_audit_consistency(doc):
    for r in doc["recipes"].values():
        audit = r["mass_audit_g"]
        resolved = sum(i["amount_g"] for i in r["ingredients"] if i["amount_g"])
        assert abs(resolved - audit["resolved_total"]) < 0.5, r["name"]
        assert audit["invisible_resolved"] >= 0
        assert audit["visible_resolved"] >= 0
        assert audit["resolved_rows"] <= audit["total_rows"]


def test_invisible_flag_and_energy_audit_blocks(doc):
    assert doc["invisible_rule"]["statement"]
    for r in doc["recipes"].values():
        assert "energy_audit" in r
        assert "atwater_delta_pct" in r["energy_audit"]
        for ing in r["ingredients"]:
            assert isinstance(ing["visible"], bool)
        break


def test_per100g_macros_present_for_most_recipes(doc):
    have = sum(1 for r in doc["recipes"].values()
               if all(r["per_100g"].get(m) is not None for m in MACROS))
    assert have / len(doc["recipes"]) > 0.99


def test_atwater_audit_is_sane(doc):
    """Median |delta| small (INDB is internally consistent); big |delta|
    recipes exist (retention + unmodelled absorption) but audit-only."""
    vals = sorted(abs(r["energy_audit"]["atwater_delta_pct"])
                  for r in doc["recipes"].values()
                  if r["energy_audit"]["atwater_delta_pct"] is not None)
    assert vals[len(vals) // 2] < 5.0
