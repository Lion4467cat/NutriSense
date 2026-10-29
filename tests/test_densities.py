"""Ticket 07c: ingredient-state density table (data/ingredient_densities.yaml).

Guards the artifact's shape and honesty rules: every state carries a rule
(literature / assumed_transfer), every literature value traces to an FAO
row with BiblioID + xlsx row number, and the audit entries cover every
serving generic_id the stack reads. This table is the provenance/audit
layer — the serving code keeps reading density_g_ml from the dish entries;
nothing here may silently change a served value.
"""
import pytest

from config import DENSITIES_PATH, load_densities


@pytest.fixture(scope="module")
def doc():
    return load_densities()


def test_loader_cached_and_cwd_independent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import config

    config.reset_caches()
    try:
        assert load_densities() is load_densities()
        assert "states" in load_densities()
    finally:
        config.reset_caches()


def test_provenance_blocks_are_complete(doc):
    for key in ("source", "license", "role", "learned_residuals"):
        assert key in doc, f"density table missing {key}"
    src = doc["source"]
    assert "fao.org" in src["url"]
    assert src["fetched"] == "2026-10-29"
    assert len(src["xlsx_sha256"]) == 64
    assert "extraction_tool" in src and "extracted_at" in src
    assert "use-with-citation" in doc["license"]["posture"]


def test_every_state_cites_values_or_admits_no_match(doc):
    for state, st in doc["states"].items():
        if st.get("rule") == "literature":
            assert isinstance(st["density_g_ml"], (int, float))
            assert 0.05 <= st["density_g_ml"] <= 2.3, state
            prov = st["provenance"]
            assert prov.startswith("direct:")
            assert "Density DB" in prov and "BiblioID" in prov, state
        elif st.get("rule") == "analogue_transfer":
            # nearest-analogue: value cited, but status stays assumed
            assert st["status"] == "assumed", state
            assert st["provenance"].startswith("nearest-analogue:")
            assert "Density DB" in st["provenance"]
        else:
            assert st["rule"] == "assumed_transfer"
            assert st["status"] == "assumed"
            # no silently-invented value: no FAO analogue -> no value at all
            assert "density_g_ml" not in st, \
                f"{state} is assumed but carries a value"
            assert "FAO/INFOODS v2" in st["provenance"]


def test_literature_states_have_reference_rows(doc):
    rice = doc["states"]["rice_boiled"]
    assert rice["density_g_ml"] == pytest.approx(0.73)
    assert rice["rule"] == "literature"
    assert any(r["row"] == "Rice, white, boiled" for r in rice["reference_rows"])
    oil = doc["states"]["cooking_oil"]
    assert 0.85 <= oil["density_g_ml"] <= 0.95
    assert oil["density_raw"]  # raw sheet text preserved
    # a proxy state keeps the cited value but never the 'literature' rule
    curd = doc["states"]["curd"]
    assert curd["rule"] == "analogue_transfer" and curd["status"] == "assumed"


def test_audit_covers_every_serving_generic_id():
    serving = set()
    for path in ("menu.yaml", "wed_dishes.yaml"):
        text = (DENSITIES_PATH.parent / path).read_text()
        import re
        for m in re.finditer(r"generic_id: ([a-z_]+)", text):
            serving.add(m.group(1))
    serving.discard("background")
    doc = load_densities()
    audited = {e["serving_id"] for e in doc["audit"]["entries"]}
    missing = serving - audited
    assert not missing, f"serving ids missing from density audit: {missing}"
    for e in doc["audit"]["entries"]:
        assert e["status"] in ("assumed", "audit_only")
        if e["delta_pct"] is not None:
            assert e["fao_density_g_ml"] is not None


def test_audit_is_explicitly_not_a_gate(doc):
    assert "never auto-applied" in doc["audit"]["role"]


def test_no_state_claims_literature_for_a_proxy_food(doc):
    # FAO v2 has no curd/yogurt/chutney rows; these states must not be
    # presented as literature under any naming drift
    for state in ("curd", "dal_soup", "veg_fried_dry", "chutney",
                  "cereal_pulse_onepot", "milk_sweet"):
        assert doc["states"][state]["rule"] != "literature"
