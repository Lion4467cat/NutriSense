"""S5: compliance verdict rules."""
import numpy as np
import pytest
import yaml

from engine.compliance import assess, coverage

DISHES = yaml.safe_load(open("data/menu.yaml"))["dishes"]


def _mc(kcal_arr, prot_arr):
    kcal = np.asarray(kcal_arr, dtype=float)
    prot = np.asarray(prot_arr, dtype=float)

    def summ(a):
        p05, p50, p95 = np.percentile(a, [5, 50, 95])
        return {"mean": float(a.mean()), "sd": float(a.std()),
                "p05": float(p05), "p50": float(p50), "p95": float(p95)}

    return {"kcal_samples": kcal, "protein_g_samples": prot,
            "kcal": summ(kcal), "protein_g": summ(prot),
            "assumed_nutrients": [], "diagnostics": {"raw_equivalent_g": {"rice": 85.0}}}


def _portion(base="ring", flags=(), anchor="measured"):
    return {"base_method": base, "flags": list(flags), "scale_tier": anchor}


def test_pass_case():
    mc = _mc(np.full(1000, 600.0), np.full(1000, 15.0))  # min 450 / 12
    out = assess(mc, _portion(), DISHES["rice_sambar"], "1-5", "measured")
    assert out["verdict"] == "PASS"
    assert out["coverage"]["score"] == 1.0
    assert out["probs"]["kcal"] == 1.0 and out["probs"]["protein_g"] == 1.0


def test_fail_case():
    mc = _mc(np.full(1000, 300.0), np.full(1000, 6.0))
    out = assess(mc, _portion(), DISHES["rice_sambar"], "1-5", "measured")
    assert out["verdict"] == "FAIL"


def test_borderline_probabilities():
    rng = np.random.default_rng(0)
    mc = _mc(rng.normal(450, 30, 4000), np.full(4000, 15.0))
    out = assess(mc, _portion(), DISHES["rice_sambar"], "1-5", "measured")
    assert out["verdict"] == "BORDERLINE"
    assert 0.1 < out["probs"]["kcal"] < 0.9


def test_prior_anchor_cannot_pass_or_fail():
    mc = _mc(np.full(1000, 600.0), np.full(1000, 15.0))
    out = assess(mc, _portion(anchor="prior"), DISHES["rice_sambar"], "1-5", "prior")
    assert out["verdict"] == "BORDERLINE"
    assert out["coverage"]["score"] == pytest.approx(0.60)
    assert any("coverage" in r for r in out["reasons"])
    mc2 = _mc(np.full(1000, 300.0), np.full(1000, 6.0))
    out2 = assess(mc2, _portion(anchor="prior"), DISHES["rice_sambar"], "1-5", "prior")
    assert out2["verdict"] == "BORDERLINE"  # FAIL blocked by coverage


def test_coverage_gate_fail_needs_090():
    # table-prior base alone: C = 0.85 -> PASS allowed, FAIL blocked
    mc_pass = _mc(np.full(1000, 600.0), np.full(1000, 15.0))
    out = assess(mc_pass, _portion(base="table_prior"), DISHES["rice_sambar"], "1-5", "measured")
    assert out["verdict"] == "PASS"
    assert out["coverage"]["score"] == pytest.approx(0.85)
    mc_fail = _mc(np.full(1000, 300.0), np.full(1000, 6.0))
    out2 = assess(mc_fail, _portion(base="table_prior"), DISHES["rice_sambar"], "1-5", "measured")
    assert out2["verdict"] == "BORDERLINE"
    assert any("coverage" in r for r in out2["reasons"])


def test_zoom_and_bad_band_cannot_verify():
    mc = _mc(np.full(100, 600.0), np.full(100, 15.0))
    out = assess(mc, _portion(), DISHES["rice_sambar"], "1-5", "measured",
                 lint={"digital_zoom": 2.0})
    assert out["verdict"] == "cannot_verify"
    out2 = assess(mc, _portion(), DISHES["rice_sambar"], "nonsense", "measured")
    assert out2["verdict"] == "cannot_verify"
    out3 = assess(None, _portion(), DISHES["rice_sambar"], "1-5", "measured")
    assert out3["verdict"] == "cannot_verify"


def test_out_of_scope_dish():
    mc = _mc(np.full(100, 600.0), np.full(100, 15.0))
    out = assess(mc, _portion(), DISHES["wheat_product"], "1-5", "measured")
    assert out["verdict"] == "out_of_scope"


def test_advisory_and_diagnostics_passthrough():
    mc = _mc(np.full(100, 600.0), np.full(100, 15.0))
    out = assess(mc, _portion(), DISHES["rice_sambar"], "1-5", "measured")
    assert out["advisory"] is not None and "advisory only" in out["advisory"]["note"]
    assert out["diagnostics"]["raw_equivalent_g"]["rice"] == 85.0


def test_coverage_function_factors():
    s, f = coverage(_portion(), "measured")
    assert s == 1.0 and f == {}
    s, f = coverage(_portion(base="table_prior", flags=["depth_partial"]), "prior")
    assert f.keys() == {"anchor_prior", "base_table_prior", "quality_degraded"}
    assert s == pytest.approx(0.60 * 0.85 * 0.90, rel=1e-6)
