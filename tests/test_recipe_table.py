"""07d test: models/recipe_table.py — table access + invisible rule."""
from __future__ import annotations

import pytest
import yaml

from models.recipe_table import (distribute_invisible, invisible_ports,
                                 load_recipes, recipe_entry,
                                 recipe_nutrients_per_100g)


@pytest.fixture(scope="module")
def doc():
    return load_recipes()


def test_table_loads(doc):
    assert doc["recipes"]
    assert doc["invisible_rule"]["statement"]


def test_nutrient_lookup(doc):
    entry = recipe_entry("ASC167")  # sambar
    assert entry is not None
    per100 = recipe_nutrients_per_100g("ASC167")
    assert per100 is not None
    assert per100["energy_kcal"] > 0
    assert recipe_nutrients_per_100g("NOPE000") is None
    assert recipe_entry("NOPE000") is None


def test_invisible_ports(doc):
    entry = recipe_entry("ASC167")
    assert entry is not None
    inv, vis, total = invisible_ports(entry)
    assert 0 <= inv <= total and vis <= total


def test_distribute_invisible_preserves_shares(doc):
    raw = recipe_entry("ASC167")
    assert raw is not None
    entry = dict(raw)
    entry["mass_audit_g"] = {"invisible_resolved": 100.0,
                             "visible_resolved": 400.0,
                             "resolved_total": 500.0}
    out = distribute_invisible({"rice": 300.0, "curry": 100.0}, entry)
    assert out == {"rice": 375.0, "curry": 125.0}
    assert sum(out.values()) == pytest.approx(500.0)
    # relative shares preserved
    assert out["rice"] / sum(out.values()) == pytest.approx(0.75)


def test_distribute_invisible_edge_cases(doc):
    entry = {"mass_audit_g": {"invisible_resolved": 100.0,
                              "visible_resolved": 0.0,
                              "resolved_total": 100.0}}
    assert distribute_invisible({"a": 5.0}, entry) == {"a": 5.0}
    assert distribute_invisible({}, entry) == {}
    assert distribute_invisible({"a": 0.0}, entry) == {"a": 0.0}
