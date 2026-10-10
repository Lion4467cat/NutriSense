"""S4: MC nutrient engine."""
import numpy as np
import pytest

from config import load_menu
from engine.mc import sample_nutrients, load_standards, load_yields
from engine.nutrients import load_nutrients

DISHES = load_menu()["dishes"]
NUTRIENTS = load_nutrients()


def _portion(grams=400.0, sigma=0.28):
    return {
        "grams": grams,
        "components_g": {"rice": 0.6 * grams, "sambar": 0.4 * grams},
        "sigma_rel": {"depth": 0.113, "area": 0.055, "base": 0.23, "density": 0.08},
        "sigma_grams_rel": sigma,
    }


def test_deterministic_with_seed():
    a = sample_nutrients(_portion(), DISHES["rice_sambar"], "1-5", seed=7)
    b = sample_nutrients(_portion(), DISHES["rice_sambar"], "1-5", seed=7)
    assert a["kcal"]["mean"] == b["kcal"]["mean"]
    assert np.array_equal(a["kcal_samples"], b["kcal_samples"])


def test_mean_matches_point_estimate():
    p = _portion(grams=400.0, sigma=0.10)
    out = sample_nutrients(p, DISHES["rice_sambar"], "1-5", n=20000, seed=3)
    # E[grams] = grams; E[share] ~= nominal; nutrient means exact
    assert out["grams"]["mean"] == pytest.approx(400.0, rel=0.02)
    k, prot, _ = NUTRIENTS["rice_boiled"]["kcal_per_100g"], NUTRIENTS["rice_boiled"]["protein_g_per_100g"], None
    ks = NUTRIENTS["sambar"]["kcal_per_100g"]
    ps = NUTRIENTS["sambar"]["protein_g_per_100g"]
    exp_kcal = 400 * (0.6 * k + 0.4 * ks) / 100.0
    exp_prot = 400 * (0.6 * prot + 0.4 * ps) / 100.0
    assert out["kcal"]["mean"] == pytest.approx(exp_kcal, rel=0.05)
    assert out["protein_g"]["mean"] == pytest.approx(exp_prot, rel=0.05)


def test_grams_spread_matches_sigma():
    p = _portion(grams=400.0, sigma=0.28)
    out = sample_nutrients(p, DISHES["rice_sambar"], "1-5", n=40000, seed=1)
    cv = out["grams"]["sd"] / out["grams"]["mean"]
    assert cv == pytest.approx(0.28, rel=0.10)
    # 90% interval roughly mean +- 1.64 sd
    assert out["grams"]["p95"] - out["grams"]["p05"] == pytest.approx(2 * 1.645 * out["grams"]["sd"], rel=0.10)


def test_component_shares_sum_to_grams():
    out = sample_nutrients(_portion(), DISHES["rice_sambar"], "1-5", n=5000, seed=2)
    total = out["components_g"]["rice"]["mean"] + out["components_g"]["sambar"]["mean"]
    assert total == pytest.approx(out["grams"]["mean"], rel=0.01)


def test_assumed_nutrients_reported():
    out = sample_nutrients(_portion(), DISHES["rice_sambar"], "1-5", n=500, seed=4)
    assert out["assumed_nutrients"] == ["sambar"]
    vr = {"grams": 400.0, "components_g": {"vegetable_rice": 400.0},
          "sigma_rel": {"depth": 0.11, "area": 0.05, "base": 0.23, "density": 0.08},
          "sigma_grams_rel": 0.28}
    out2 = sample_nutrients(vr, DISHES["vegetable_rice"], "1-5", n=500, seed=4)
    assert out2["assumed_nutrients"] == ["vegetable_rice"]
    assert out2["wider_ranges"] is True


def test_raw_diagnostic_and_allocation():
    out = sample_nutrients(_portion(grams=400.0), DISHES["rice_sambar"], "1-5", n=500, seed=5)
    raw = out["diagnostics"]["raw_equivalent_g"]
    assert raw["rice"] == pytest.approx(0.6 * 400 / 3.0, rel=0.01)
    assert out["diagnostics"]["raw_allocation_per_day_g"]["rice"] == 100
    assert "informational" in out["diagnostics"]["raw_basis_note"]


def test_temperature_widens_interval():
    p = _portion()
    dish = DISHES["rice_sambar"]
    a = sample_nutrients(p, dish, "1-5", n=4000, seed=9)
    import engine.mc as mcmod
    saved = dict(mcmod.load_params())
    try:
        mcmod.load_params()["temperature_scale"]["value"] = 2.0
        b = sample_nutrients(p, dish, "1-5", n=4000, seed=9)
    finally:
        mcmod.load_params().clear()
        mcmod.load_params().update(saved)
    wa = a["kcal"]["p95"] - a["kcal"]["p05"]
    wb = b["kcal"]["p95"] - b["kcal"]["p05"]
    assert wb == pytest.approx(2.0 * wa, rel=0.05)
