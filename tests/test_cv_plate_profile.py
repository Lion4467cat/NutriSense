"""cv_plate_profile math — hermetic (synthetic samples, no model/dataset/GPU).

The scoring path is tools/run_eval's own (guarded elsewhere); only the
plate-concentration arithmetic of ledger 005 is covered here.
"""
import numpy as np
import pytest

from tools.cv_plate_profile import (
    concentration,
    gini,
    jackknife,
    overall_mae,
    plate_table,
)


def _samples() -> list[dict]:
    # plate A: 2 samples, err -10 / -10 (biased one direction)
    # plate B: 3 samples, err +5 / -5 / 0
    # plate C: 1 sample, err +2
    out = []
    out.append({"plate": "A", "dish": "d1", "pred": 90, "gt": 100, "err": -10})
    out.append({"plate": "A", "dish": "d1", "pred": 88, "gt": 98, "err": -10})
    out.append({"plate": "B", "dish": "d2", "pred": 105, "gt": 100, "err": 5})
    out.append({"plate": "B", "dish": "d2", "pred": 95, "gt": 100, "err": -5})
    out.append({"plate": "B", "dish": "d3", "pred": 100, "gt": 100, "err": 0})
    out.append({"plate": "C", "dish": "d1", "pred": 102, "gt": 100, "err": 2})
    return out


def test_overall_mae() -> None:
    s = _samples()
    assert overall_mae(s) == pytest.approx((10 + 10 + 5 + 5 + 0 + 2) / 6)


def test_plate_table_sorted_and_signed_means() -> None:
    rows = plate_table(_samples())
    by_plate = {r["plate"]: r for r in rows}
    assert by_plate["A"]["n"] == 2
    assert by_plate["A"]["mae"] == pytest.approx(10.0)
    assert by_plate["A"]["mean_err"] == pytest.approx(-10.0)
    assert by_plate["B"]["mean_err"] == pytest.approx(0.0)
    assert by_plate["C"]["n"] == 1
    # sorted by abs_err DESC: A first (20), then B (10), C (2)
    assert [r["plate"] for r in rows] == ["A", "B", "C"]
    total = sum(r["abs_err"] for r in rows)
    assert total == pytest.approx(32.0)
    assert sum(r["share"] for r in rows) == pytest.approx(1.0)


def test_concentration_shares_and_uniform() -> None:
    rows = plate_table(_samples())
    top1 = concentration(rows, 1)
    assert top1["share"] == pytest.approx(20.0 / 32.0)
    assert top1["uniform_share"] == pytest.approx(1.0 / 3.0, abs=1e-3)
    top2 = concentration(rows, 2)
    assert top2["share"] == pytest.approx(30.0 / 32.0)
    assert top2["uniform_share"] == pytest.approx(2.0 / 3.0, abs=1e-3)


def test_gini_extremes() -> None:
    # equal plates -> 0
    equal = [{"plate": "a", "abs_err": 1.0},
             {"plate": "b", "abs_err": 1.0},
             {"plate": "c", "abs_err": 1.0}]
    assert gini(equal) == pytest.approx(0.0)
    # all mass on one plate -> approaches 1
    all_in_one = [{"plate": "a", "abs_err": 10.0},
                  {"plate": "b", "abs_err": 0.0},
                  {"plate": "c", "abs_err": 0.0}]
    assert gini(all_in_one) == pytest.approx(2.0 / 3.0, rel=1e-3)


def test_gini_concentrated_profile() -> None:
    rows = plate_table(_samples())
    # mass is uneven (A dominates) -> positive Gini
    assert gini(rows) > 0.2


def test_jackknife_deltas() -> None:
    jk = jackknife(_samples())
    deltas = {r["plate"]: r["delta_g"] for r in jk}
    overall = 32.0 / 6.0
    # without A: (5+5+0+2)/4 = 3.0 -> delta 3.0 - 5.333..
    assert deltas["A"] == pytest.approx(3.0 - overall, abs=1e-3)
    # without C: (10+10+5+5+0)/5 = 6.0 -> delta 6.0 - 5.333..
    assert deltas["C"] == pytest.approx(6.0 - overall, abs=1e-3)
    # sorted ascending by delta: A (removing the worst plate LOWERS mae)
    assert next(r["plate"] for r in jk) == "A"
