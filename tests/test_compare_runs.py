"""Paired comparison of two run_eval reports (tools/compare_runs.py).

The CI is a PAIRED bootstrap over plates: the same plate multiset is drawn
for both runs in every replicate, so a constant per-ROI offset shows up as a
sharp difference while plate-to-plate difficulty cancels out.

Nothing here loads a model or touches the GPU.
"""
from __future__ import annotations

import json

import pytest

import tools.compare_runs as compare_runs
from tools.compare_runs import CompareRefused, compare

STRESS_NAMES = ("brightness_contrast_0.7", "jpeg_q30")


def _plates(mae_offset_g: float = 0.0, *, drop: str | None = None) -> dict:
    """6 plates x 10 ROIs; per-plate baseline MAE 4..8 g so resampling is real."""
    pc = {}
    for i in range(6):
        plate = f"p{i}"
        if plate == drop:
            continue
        n = 10
        pc[plate] = {"n": n,
                     "sum_abs_err": round((40.0 + 4.0 * i) + mae_offset_g * n, 4),
                     "n_sigma": n,
                     "n_covered": 9 - (i % 3)}
    return pc


def _report(tier: str = "dev", mae_offset_g: float = 0.0, *,
            drop: str | None = None, with_stress: bool = True,
            with_per_plate: bool = True) -> dict:
    rep: dict = {"tier": tier, "n_plates": 6, "mae_g": 5.0, "coverage_90": 0.8}
    if with_per_plate:
        rep["per_plate"] = _plates(mae_offset_g, drop=drop)
    if with_stress:
        rep["stress"] = {name: {"per_plate": _plates(mae_offset_g, drop=drop),
                                "mae_g": 5.0, "coverage_90": 0.8}
                         for name in STRESS_NAMES}
    return rep


# ---------------------------------------------------------------- happy path --
def test_identical_runs_give_zero_difference_with_a_ci_around_zero():
    res = compare(_report(), _report(), seed=42)
    assert res["tier"] == "dev"
    assert res["mae_g"]["diff"] == pytest.approx(0.0)
    assert res["mae_g"]["diff_ci95"] == [0.0, 0.0]
    assert res["coverage_90"]["diff"] == pytest.approx(0.0)
    assert res["coverage_90"]["diff_ci95"] == [0.0, 0.0]
    lo, hi = res["mae_g"]["diff_ci95"]
    assert lo <= 0.0 <= hi


def test_constant_plus_2g_offset_is_detected_with_a_ci_excluding_zero():
    res = compare(_report(), _report(mae_offset_g=2.0), seed=42)
    assert res["mae_g"]["baseline"] == pytest.approx(5.0)
    assert res["mae_g"]["candidate"] == pytest.approx(7.0)
    assert res["mae_g"]["diff"] == pytest.approx(2.0)
    lo, hi = res["mae_g"]["diff_ci95"]
    assert lo == pytest.approx(2.0) and hi == pytest.approx(2.0)
    assert lo > 0.0, "CI must exclude 0 for a real regression/improvement"
    # coverage is untouched by a gram offset
    assert res["coverage_90"]["diff"] == pytest.approx(0.0)


def test_paired_bootstrap_is_seed_deterministic():
    a = compare(_report(), _report(mae_offset_g=1.5), seed=7)
    b = compare(_report(), _report(mae_offset_g=1.5), seed=7)
    assert a["mae_g"]["diff_ci95"] == b["mae_g"]["diff_ci95"]
    assert a["coverage_90"]["diff_ci95"] == b["coverage_90"]["diff_ci95"]


def test_each_stress_perturbation_is_paired_too():
    res = compare(_report(), _report(mae_offset_g=3.0), seed=42)
    assert set(res["stress"]["paired"]) == set(STRESS_NAMES)
    for name, block in res["stress"]["paired"].items():
        assert block["mae_g"]["diff"] == pytest.approx(3.0), name
        assert block["mae_g"]["diff_ci95"][0] > 0.0, name
    assert res["stress"]["missing_in_baseline"] == []
    assert res["stress"]["missing_in_candidate"] == []


def test_stress_present_in_only_one_run_is_reported_not_fatal():
    base = _report()
    cand = _report()
    cand["stress"].pop("jpeg_q30")
    res = compare(base, cand, seed=42)
    assert res["stress"]["missing_in_candidate"] == ["jpeg_q30"]
    assert set(res["stress"]["paired"]) == {"brightness_contrast_0.7"}


# ------------------------------------------------------------------ refusals --
def test_refuses_runs_from_different_tiers():
    with pytest.raises(CompareRefused, match="different tiers"):
        compare(_report(tier="dev"), _report(tier="train"))
    with pytest.raises(CompareRefused, match="different tiers"):
        compare(_report(tier="dev"), _report(tier="locked"))


def test_refuses_runs_over_different_plate_sets():
    with pytest.raises(CompareRefused, match="different plate sets"):
        compare(_report(), _report(drop="p3"))
    with pytest.raises(CompareRefused, match="different plate sets"):
        compare(_report(drop="p0"), _report())


def test_refuses_reports_without_per_plate_aggregates():
    with pytest.raises(CompareRefused, match="per_plate"):
        compare(_report(with_per_plate=False), _report())


def test_refuses_a_stress_plate_set_mismatch():
    base = _report()
    cand = _report()
    cand["stress"]["jpeg_q30"]["per_plate"] = _plates(drop="p5")
    with pytest.raises(CompareRefused, match="stress jpeg_q30"):
        compare(base, cand)


# ----------------------------------------------------------------------- CLI --
def test_cli_writes_the_comparison(tmp_path, capsys):
    b, c = tmp_path / "base.json", tmp_path / "cand.json"
    out = tmp_path / "compare.json"
    b.write_text(json.dumps(_report()))
    c.write_text(json.dumps(_report(mae_offset_g=2.0)))
    rc = compare_runs.main([str(b), str(c), "--out", str(out)])
    assert rc == 0
    printed = capsys.readouterr().out
    assert "paired_ci95" in printed and "tier=dev" in printed
    assert json.loads(out.read_text())["mae_g"]["diff"] == pytest.approx(2.0)


def test_cli_exits_nonzero_on_a_tier_mismatch(tmp_path, capsys):
    b, c = tmp_path / "base.json", tmp_path / "cand.json"
    b.write_text(json.dumps(_report(tier="dev")))
    c.write_text(json.dumps(_report(tier="train")))
    assert compare_runs.main([str(b), str(c)]) == 2
    assert "refused" in capsys.readouterr().err


def test_cli_exits_nonzero_on_a_plate_set_mismatch(tmp_path, capsys):
    b, c = tmp_path / "base.json", tmp_path / "cand.json"
    b.write_text(json.dumps(_report()))
    c.write_text(json.dumps(_report(drop="p2")))
    assert compare_runs.main([str(b), str(c)]) == 2
    assert "plate sets" in capsys.readouterr().err


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))
