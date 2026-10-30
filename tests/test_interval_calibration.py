"""Interval-calibration machinery (ticket 03, ledger 004) — hermetic math.

The leave-one-plate-out conformal calibration is exercised on synthetic
samples with known residuals; no dataset, no torch, no GPU. The GPU-side
scoring path is tools/run_eval's own (already guarded by test_locked_eval).
"""
import itertools
from pathlib import Path

import numpy as np
import pytest
import yaml

from tools.calibrate_intervals import (
    Z90,
    apply_calibration,
    calibrate,
    choose_multiplier,
    conformal_quantile,
    coverage_at,
    fold_sigma_refit,
    normalized_scores,
    read_sigma_doc,
    wire_interval,
    wire_width_rel,
)


def _sample(plate, dish, pred, gt):
    return {"plate": plate, "dish": dish, "pred": pred, "gt": gt,
            "err": pred - gt}


# ------------------------------------------------------------ conformal ---
def test_conformal_quantile_finite_sample_position():
    # n=10, alpha=0.10 -> k = ceil(0.9 * 11) = 10 -> the 10th smallest
    scores = np.arange(1, 11, dtype=float)
    assert conformal_quantile(scores) == pytest.approx(10.0)
    # n=100 -> k = ceil(0.9 * 101) = 91
    scores = np.arange(1, 101, dtype=float)
    assert conformal_quantile(scores) == pytest.approx(91.0)


def test_conformal_quantile_guarantee_on_exchangeable_scores():
    # the >= 90% guarantee is marginal over (cal, new) draws — one realization
    # can dip; average over repetitions
    rng = np.random.default_rng(7)
    covs = []
    for _ in range(60):
        cal = np.abs(rng.normal(0.0, 1.0, 1218))
        new = np.abs(rng.normal(0.0, 1.0, 400))
        covs.append(float(np.mean(new <= conformal_quantile(cal))))
    assert float(np.mean(covs)) >= 0.89


def test_coverage_at_and_choose_multiplier_smallest_passing():
    scores = np.full(100, 1.10)  # all residuals exactly 1.10 sigma wide
    assert coverage_at(scores, 1.05) == 0.0
    assert coverage_at(scores, 1.10) == 1.0
    t = choose_multiplier(scores, target=0.90, lo=0.50, hi=1.50, step=0.005)
    assert t == pytest.approx(1.10)


def test_choose_multiplier_none_when_never_reached():
    scores = np.full(100, 2.0)
    assert choose_multiplier(scores, target=0.90, lo=0.5, hi=1.5,
                             step=0.005) is None


def test_choose_multiplier_monotone_in_t():
    rng = np.random.default_rng(3)
    scores = np.abs(rng.normal(0.0, 1.0, 500))
    covs = [coverage_at(scores, t) for t in np.arange(0.5, 1.51, 0.05)]
    assert all(b >= a for a, b in itertools.pairwise(covs))


# ---------------------------------------------------------------- folds ---
def _two_plate_samples():
    """Class 'a' has 4 residuals spread +-2 on plate 1; plate 2 holds the
    same class once (fold fallback) and a rare class 'b' twice."""
    s = [_sample("p1", "a", 0.0, r) for r in (-2.0, -1.0, 1.0, 2.0)]
    s += [_sample("p2", "a", 0.0, 0.5), _sample("p2", "b", 0.0, 1.0),
          _sample("p2", "b", 0.0, 3.0)]
    return s


def test_fold_sigma_refit_measured_and_fallback_classes():
    file_g, file_rel = {"a": 99.0, "b": 7.0}, {"a": 0.9, "b": 0.5}
    sg, srel, fb = fold_sigma_refit(
        [s for s in _two_plate_samples() if s["plate"] == "p1"],
        file_g, file_rel)
    # class 'a': 4 in-fold residuals -> measured std (ddof 0) = sqrt(2.5)
    assert sg["a"] == pytest.approx(np.std([-2.0, -1.0, 1.0, 2.0]))
    # sigma_rel = sigma / max(1, mean gt); mean gt here is 0 -> floored to 1
    assert srel["a"] == pytest.approx(sg["a"])
    assert fb == 0


def test_fold_sigma_refit_falls_back_below_min_count():
    file_g, file_rel = {"a": 99.0, "b": 7.0}, {"a": 0.9, "b": 0.5}
    # in-fold = plate 2 only: 'a' has 1 in-fold sample, 'b' has 2 — both
    # below min_count 3 -> both fall back to the file's full-DEV sigma
    sg, srel, fb = fold_sigma_refit(
        [s for s in _two_plate_samples() if s["plate"] == "p2"],
        file_g, file_rel)
    assert sg["a"] == 99.0 and srel["a"] == 0.9
    assert sg["b"] == 7.0 and srel["b"] == 0.5
    assert fb == 3


def test_fold_sigma_refit_missing_artifact_entry_raises():
    with pytest.raises(KeyError):
        fold_sigma_refit(_two_plate_samples(), {}, {})


def test_normalized_scores_shape_and_value():
    samples = _two_plate_samples()
    sg = {"a": 2.0, "b": 1.0}
    sc = normalized_scores(samples, sg)
    assert sc[0] == pytest.approx(2.0 / (Z90 * 2.0))
    assert sc[-1] == pytest.approx(3.0 / (Z90 * 1.0))


def test_normalized_scores_unknown_dish_raises():
    with pytest.raises(KeyError):
        normalized_scores([_sample("p", "ghost", 0.0, 1.0)], {})


# ----------------------------------------------------------- wire shape ---
def test_wire_interval_is_the_lognormal_central_90():
    pred, s = 100.0, 0.2
    lo, hi = wire_interval(pred, s)
    median = pred * np.exp(-0.5 * s * s)
    assert lo == pytest.approx(pred * np.exp(-0.5 * s * s - Z90 * s))
    assert hi == pytest.approx(pred * np.exp(-0.5 * s * s + Z90 * s))
    assert lo < median < hi


def test_wire_interval_monotone_wider_in_sigma_rel():
    lo1, hi1 = wire_interval(100.0, 0.1)
    lo2, hi2 = wire_interval(100.0, 0.3)
    assert lo2 < lo1 and hi2 > hi1
    assert wire_width_rel(0.3) > wire_width_rel(0.1)


# ------------------------------------------------------- full machinery ---
def _mixture_samples(plates=("p1", "p2"), per_plate=60, seed=11):
    """Residual shape that is NOT Gaussian: +-1 with p .80, +-3 with p .20
    (std ~1.61). The fold refit measures the std, but a Gaussian sigma-band
    at +-1.645*std covers only the ~80% body -> the multiplier must climb
    above 1 to reach 0.90 out-of-fold coverage."""
    rng = np.random.default_rng(seed)
    samples = []
    for p in plates:
        for _ in range(per_plate):
            mag = 1.0 if rng.random() < 0.80 else 3.0
            r = float(mag if rng.random() < 0.5 else -mag)
            samples.append(_sample(p, "a", 10.0, 10.0 + r))
    return samples


def test_calibrate_end_to_end_synthetic():
    samples = _mixture_samples()
    # the file's sigma layer IS the full-DEV residual std (as in production)
    res = np.array([s["pred"] - s["gt"] for s in samples])
    file_g = {"a": float(np.std(res))}
    file_rel = {"a": file_g["a"] / 10.0}

    rep = calibrate(samples, file_g, file_rel)
    assert rep["n_folds"] == 2 and rep["n_samples"] == 120
    # nominal OOF coverage clearly below 0.90 (shape mismatch, ~0.80 truth)
    assert rep["nominal_check"][
        "oof_coverage_90_band_at_multiplier_1.0"] < 0.90
    t = rep["stage_c"]["multiplier"]
    assert t is not None and 1.0 <= t <= 1.35
    # selection rule guarantees the gate at the deployed multiplier
    assert rep["stage_c"]["oof_coverage_90_band"] >= 0.90
    assert rep["stage_c"]["band_width_growth_pct"] == \
        pytest.approx(100 * (t - 1))
    # wire growth ~ band growth for small sigma_rel (ratio ~ multiplier)
    assert rep["stage_c"]["wire_width_growth_pct"] == pytest.approx(
        rep["stage_c"]["band_width_growth_pct"], abs=3)
    # wire OOF corroborates the band within a few points (lognormal asymmetry)
    assert abs(rep["stage_c"]["oof_coverage_90_wire"]
               - rep["stage_c"]["oof_coverage_90_band"]) <= 0.06
    # per-fold procedure: each fold calibrated by its own in-fold quantile —
    # held coverage is >= k/n = ceil(0.9*(m+1))/m >= 0.90 structurally
    assert rep["per_fold_procedure_pooled_oof_coverage_90"] >= 0.90
    assert rep["fallback_samples_total"] == 0
    assert rep["stage_c"]["gate"]["oof_coverage_90_ge_0.90"] is True


def test_calibrate_stage_b_per_class_multipliers():
    """Stage B: class 'a' is well-behaved Gaussian (multiplier ~ 1), class
    'b' carries the miscalibrated shape (~ 1.2) — per-class multipliers
    must differ in the right direction while pooled coverage holds."""
    rng = np.random.default_rng(5)
    samples = []
    for p in ("p1", "p2", "p3"):
        for _ in range(40):
            samples.append(_sample(p, "a", 10.0,
                                   10.0 + float(rng.normal(0.0, 1.6))))
        for s in _mixture_samples(plates=(p,), per_plate=40, seed=7):
            samples.append(_sample(p, "b", s["pred"], s["gt"]))
    res_a = np.array([s["pred"] - s["gt"] for s in samples if s["dish"] == "a"])
    res_b = np.array([s["pred"] - s["gt"] for s in samples if s["dish"] == "b"])
    file_g = {"a": float(np.std(res_a)), "b": float(np.std(res_b))}
    file_rel = {"a": file_g["a"] / 10.0, "b": file_g["b"] / 10.0}

    rep = calibrate(samples, file_g, file_rel)
    assert rep["n_folds"] == 3 and rep["n_samples"] == 240
    tb = rep["stage_b"]
    assert set(tb["multiplier_per_class"]) == {"a", "b"}
    assert tb["multiplier_per_class"]["a"] < tb["multiplier_per_class"]["b"]
    assert tb["oof_coverage_90_band"] >= 0.90
    assert tb["gate"]["oof_coverage_90_ge_0.90"] is True
    assert tb["classes_capped_at_grid_ceiling"] == []


# ---------------------------------------------------------------- apply ---
def _write_raw_sigma(tmp_path: Path) -> Path:
    doc = {"_meta": {"dataset": "WED", "trained": "2026-10-15"},
           "sigma_g": {"a": 1.00, "b": 2.50},
           "sigma_rel": {"a": 0.1000, "b": 0.2500},
           "note": "raw"}
    p = tmp_path / "weight_head_sigma.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return p


def test_apply_scales_sigma_and_records_provenance(tmp_path):
    p = _write_raw_sigma(tmp_path)
    landed = apply_calibration(1.1, None, "data/reports/x.json",
                               0.9007, 0.8988, 0.8522, sigma_path=p)
    doc = read_sigma_doc(p)
    assert doc["sigma_g"] == {"a": 1.1, "b": 2.75}
    assert doc["sigma_rel"] == {"a": 0.11, "b": 0.275}
    cal = doc["_meta"]["calibration"]
    assert cal == landed
    assert cal["multiplier"] == pytest.approx(1.1)
    assert cal["stage"] == "C"
    assert cal["status"] == "calibrated"
    assert cal["oof_coverage_90_band"] == pytest.approx(0.9007)
    assert "conformal" in cal["method"]
    assert "value / multiplier" in doc["note"]


def test_apply_stage_b_scales_per_class(tmp_path):
    p = _write_raw_sigma(tmp_path)
    landed = apply_calibration(None, {"a": 1.1, "b": 1.0},
                               "data/reports/x.json",
                               0.9007, 0.8988, 0.8522, sigma_path=p)
    doc = read_sigma_doc(p)
    assert doc["sigma_g"] == {"a": 1.1, "b": 2.5}
    assert doc["sigma_rel"] == {"a": 0.11, "b": 0.25}
    cal = doc["_meta"]["calibration"]
    assert cal == landed
    assert cal["stage"] == "B"
    assert cal["multiplier"] is None
    assert cal["multiplier_per_class"] == {"a": 1.1, "b": 1.0}


def test_apply_refuses_ambiguous_stage(tmp_path):
    p = _write_raw_sigma(tmp_path)
    with pytest.raises(ValueError, match="exactly one"):
        apply_calibration(1.1, {"a": 1.1}, "x.json", 0.9, 0.9, 0.85,
                          sigma_path=p)


def test_apply_refuses_second_application(tmp_path):
    p = _write_raw_sigma(tmp_path)
    apply_calibration(1.1, None, "x.json", 0.9, 0.9, 0.85, sigma_path=p)
    with pytest.raises(ValueError, match="already carries"):
        apply_calibration(1.1, None, "x.json", 0.9, 0.9, 0.85, sigma_path=p)
