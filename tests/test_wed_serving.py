"""Data-level serving coverage (spec 002 decision 3, ticket 02, ledger 003).

Every non-background WED class in data/wed/index_map.json must resolve:
into a menu-dish `wed_slots` entry (3 menu-equivalent classes keep their
current verdict path, incl. wheat_product's out_of_scope gate) or an
`off_menu` entry with its own slot, resolvable in the index, and one
component whose generic_id exists in data/nutrients.yaml. `background` is
not a dish. Pure data test — no models, no GPU.
"""
import pytest

from config import load_menu, load_nutrients, load_wed_dishes, load_wed_index


@pytest.fixture
def wed():
    d = load_wed_dishes()
    for key in ("serving", "off_menu"):
        assert key in d, f"data/wed_dishes.yaml missing section {key!r}"
    return d


def test_every_wed_class_resolves(wed):
    """41 non-background classes, each with a serving target that exists."""
    index = load_wed_index()
    assert "background" not in index
    assert len(index) == 41
    serving = wed["serving"]
    off_menu = wed["off_menu"]
    menu = load_menu()["dishes"]
    for name in index:
        assert name in serving, f"WED class {name!r} not in serving map"
        target = serving[name]["dish"]
        assert target in menu or target in off_menu, \
            f"WED class {name!r} -> unknown serving target {target!r}"
    assert "background" not in serving and "background" not in off_menu


def test_menu_dish_slot_mappings_unchanged(wed):
    """The four pre-existing menu-dish entries keep their exact mappings."""
    dishes = wed["dishes"]
    assert dishes["rice_sambar"]["wed_slots"] == ["steamed-rice", "sambar"]
    assert dishes["vegetable_rice"]["wed_slots"] == ["veg-pulao"]
    assert dishes["bisibelebath"]["wed_slots"] == ["bisi-bele-bath"]
    assert dishes["wheat_product"]["wed_slots"] == ["phulka"]


def test_menu_equivalent_classes_route_to_their_menu_dish(wed):
    serving = wed["serving"]
    assert serving["veg-pulao"]["dish"] == "vegetable_rice"
    assert serving["bisi-bele-bath"]["dish"] == "bisibelebath"
    assert serving["phulka"]["dish"] == "wheat_product"


def test_off_menu_entries_are_serveable(wed):
    """Every off-menu entry has its own valid slot and a serveable recipe:
    components with a nutrients.yaml generic_id, positive share, density."""
    index = load_wed_index()
    nutrients = load_nutrients()
    for key, entry in wed["off_menu"].items():
        assert key in index, f"off_menu key {key!r} is not a WED class"
        assert entry["wed_slots"] == [key], \
            f"off_menu entry {key!r} must own exactly its own slot"
        assert entry.get("nutrition_source") == "generic", f"{key!r} nutrition_source"
        assert entry.get("display_name")
        comps = entry["components"]
        assert comps and len(comps) == 1, f"{key!r}: one self-entry expected"
        total_share = sum(float(c.get("share", 1.0)) for c in comps.values())
        assert total_share == pytest.approx(1.0), f"{key!r} share must sum to 1"
        for comp in comps.values():
            gid = comp["generic_id"]
            assert gid in nutrients, f"{key!r}: no nutrient row for {gid!r}"
            assert comp["density_g_ml"] > 0, f"{key!r} density"


def test_the_three_menu_routed_classes_have_no_off_menu_entry(wed):
    """veg-pulao / bisi-bele-bath / phulka already live as menu dish slots —
    their serving goes through the menu path; no duplicate off_menu entry."""
    for cls in ("veg-pulao", "bisi-bele-bath", "phulka"):
        assert cls not in wed["off_menu"]


def test_classify_labels_cover_all_classes():
    """The classifier must accept every WED class name as a gallery label
    (recognition space) and resolve every serving target."""
    from models.food_classifier import menu_dish_keys, serving_dish_keys
    from models.food_classifier import serving_targets

    index = set(load_wed_index())
    targets = serving_targets()
    assert index <= set(targets)
    assert set(menu_dish_keys()) <= set(targets.values())
    assert set(serving_dish_keys()) == set(targets.values())
