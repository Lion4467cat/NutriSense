"""S5: compliance verdict rules."""
import numpy as np
import pytest

from config import load_menu
from engine.compliance import assess, coverage
from engine.contract import FailureKind, ReasonKind

DISHES = load_menu()["dishes"]


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
    assert out.verdict == "PASS"
    assert out.coverage["score"] == 1.0
    assert out.probs["kcal"] == 1.0 and out.probs["protein_g"] == 1.0


def test_fail_case():
    mc = _mc(np.full(1000, 300.0), np.full(1000, 6.0))
    out = assess(mc, _portion(), DISHES["rice_sambar"], "1-5", "measured")
    assert out.verdict == "FAIL"


def test_borderline_probabilities():
    rng = np.random.default_rng(0)
    mc = _mc(rng.normal(450, 30, 4000), np.full(4000, 15.0))
    out = assess(mc, _portion(), DISHES["rice_sambar"], "1-5", "measured")
    assert out.verdict == "BORDERLINE"
    assert 0.1 < out.probs["kcal"] < 0.9


def test_geometry_prior_still_capped_with_disclaimer():
    """No card + geometry grams: coverage stays 0.60, so the scored verdict
    can only be BORDERLINE — and the no-card disclaimer leads the reasons."""
    mc = _mc(np.full(1000, 600.0), np.full(1000, 15.0))
    out = assess(mc, _portion(anchor="prior"), DISHES["rice_sambar"], "1-5", "prior")
    assert out.verdict == "BORDERLINE"           # zone met, C=0.60 < 0.85 gate
    assert out.coverage["score"] == pytest.approx(0.60)
    assert out.reasons[0].kind == ReasonKind.NO_REFERENCE_CARD
    mc2 = _mc(np.full(1000, 300.0), np.full(1000, 6.0))
    out2 = assess(mc2, _portion(anchor="prior"), DISHES["rice_sambar"], "1-5", "prior")
    assert out2.verdict == "BORDERLINE"          # fail zone met, C < 0.90 gate
    assert out2.reasons[0].kind == ReasonKind.NO_REFERENCE_CARD


def test_learned_prior_is_scored_with_no_card_disclaimer():
    """Graduation (2026-10-11, ADR-0002 amendment): learned grams without a
    card ARE scored — coverage 0.90 keeps PASS and FAIL reachable — with the
    no-card disclaimer as the first reason."""
    mc = _mc(np.full(1000, 600.0), np.full(1000, 15.0))
    portion = _portion(anchor="prior")
    portion["grams_source"] = "learned_weight"
    out = assess(mc, portion, DISHES["rice_sambar"], "1-5", "prior")
    assert out.verdict == "PASS"
    assert out.coverage["score"] == pytest.approx(0.90)
    assert out.reasons[0].kind == ReasonKind.NO_REFERENCE_CARD
    assert "estimate" in out.reasons[0].text and "No reference card" in out.reasons[0].text
    # fail zone is reachable too (0.90 >= fail gate 0.90)
    mc2 = _mc(np.full(1000, 300.0), np.full(1000, 6.0))
    out2 = assess(mc2, dict(portion), DISHES["rice_sambar"], "1-5", "prior")
    assert out2.verdict == "FAIL"
    assert out2.reasons[0].kind == ReasonKind.NO_REFERENCE_CARD


def test_estimated_reason_names_learned_source():
    mc = _mc(np.full(1000, 600.0), np.full(1000, 15.0))
    portion = _portion(anchor="prior")
    portion["grams_source"] = "learned_weight"
    out = assess(mc, portion, DISHES["rice_sambar"], "1-5", "prior")
    assert out.verdict == "PASS"                 # scored — ESTIMATED is legacy-only
    assert any("learned model" in r.text for r in out.reasons)
    assert any("learned weight head" in a for a in out.assumptions)


def test_coverage_gate_fail_needs_090():
    # table-prior base alone: C = 0.85 -> PASS allowed, FAIL blocked
    mc_pass = _mc(np.full(1000, 600.0), np.full(1000, 15.0))
    out = assess(mc_pass, _portion(base="table_prior"), DISHES["rice_sambar"], "1-5", "measured")
    assert out.verdict == "PASS"
    assert out.coverage["score"] == pytest.approx(0.85)
    mc_fail = _mc(np.full(1000, 300.0), np.full(1000, 6.0))
    out2 = assess(mc_fail, _portion(base="table_prior"), DISHES["rice_sambar"], "1-5", "measured")
    assert out2.verdict == "BORDERLINE"
    assert any(r.kind == ReasonKind.COVERAGE_GATE for r in out2.reasons)


def test_missing_mc_cannot_score():
    # scoring precondition, not a gate: assess() never sees None in production
    out = assess(None, _portion(), DISHES["rice_sambar"], "1-5", "measured")
    assert out.verdict == "cannot_verify"
    assert out.failures[0].kind is FailureKind.STAGE_FAILED


def test_advisory_and_diagnostics_passthrough():
    mc = _mc(np.full(100, 600.0), np.full(100, 15.0))
    out = assess(mc, _portion(), DISHES["rice_sambar"], "1-5", "measured")
    assert out.advisory is not None and "advisory only" in out.advisory["note"]
    assert out.diagnostics["raw_equivalent_g"]["rice"] == 85.0


def test_coverage_function_factors():
    s, f = coverage(_portion(), "measured")
    assert s == 1.0 and f == {}
    s, f = coverage(_portion(base="table_prior", flags=["depth_partial"]), "prior")
    assert f.keys() == {"anchor_prior", "base_table_prior", "quality_degraded"}
    assert s == pytest.approx(0.60 * 0.85 * 0.90, rel=1e-6)
    # learned grams without a card: estimated_weight replaces anchor_prior
    lp = _portion(anchor="prior")
    lp["grams_source"] = "learned_weight"
    s, f = coverage(lp, "prior")
    assert f == {"estimated_weight": 0.90}
    assert s == pytest.approx(0.90)


def test_coverage_depth_uncalibrated_factor():
    # reported "none" on a measured anchor = calibration declined
    s, f = coverage(_portion(), "measured", depth_scale_source="none")
    assert f == {"depth_uncalibrated": 0.80}
    assert s == pytest.approx(0.80)
    # calibrated: no factor
    s, f = coverage(_portion(), "measured", depth_scale_source="card")
    assert f == {}
    # prior tier is already capped by anchor_prior — no double penalty
    s, f = coverage(_portion(anchor="prior"), "prior", depth_scale_source="none")
    assert set(f) == {"anchor_prior"}
    # not reported (unit-test calls) never invents a factor
    s, f = coverage(_portion(), "measured")
    assert f == {}
