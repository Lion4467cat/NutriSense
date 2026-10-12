"""Card-path stress suite guards (tools/card_stress.py).

Two properties must never regress:

1. Seed determinism — same (scenes, seed, reps, groups) produces the same
   report (bit-identical modulo the timestamp / wall-clock / git keys).
2. False accepts are honest — a miss (`prior`) is never counted as an
   accept, and a "detected" anchor whose cm/px is more than 5% off the
   render ground truth is flagged as a false accept. Non-finite pose
   tilts are counted (n_tilt_nan), never imputed into the tilt error.

Nothing here loads a model or touches the GPU.
"""
from __future__ import annotations

import numpy as np
import pytest

import tools.card_stress as card_stress
from tools.card_stress import _portion_summary, score_detection

VOLATILE = ("created", "wall_s", "git", "branch")


def _gt(**over) -> dict:
    base = {"cm_per_px": 0.25, "tilt_deg": 30.0, "marker_side_px": 120.0}
    base.update(over)
    return base


def _est(**over) -> dict:
    base = {"method": "card_aruco", "cm_per_px": 0.25, "tilt_deg": 30.0}
    base.update(over)
    return base


# --------------------------------------------------------- score_detection --
def test_known_bad_cm_is_a_false_accept():
    """10% scale error trips the 5% false-accept gate; 3% does not."""
    bad = score_detection(_gt(), _est(cm_per_px=0.275))
    assert bad["detected"] and bad["false_accept"]
    assert bad["cm_rel_err"] == pytest.approx(0.10)
    ok = score_detection(_gt(), _est(cm_per_px=0.2575))
    assert ok["detected"] and not ok["false_accept"]
    assert ok["cm_rel_err"] == pytest.approx(0.03)


def test_a_miss_is_not_an_accept():
    miss = score_detection(_gt(), {"method": "prior", "cm_per_px": None})
    assert not miss["detected"]
    assert not miss["false_accept"]
    assert miss["cm_rel_err"] is None and miss["tilt_err_deg"] is None


def test_nonfinite_tilt_is_counted_not_imputed():
    nan = score_detection(_gt(), _est(tilt_deg=float("nan")))
    assert nan["detected"] and not nan["false_accept"]
    assert nan["tilt_err_deg"] is None and nan["tilt_nan"] is True
    good = score_detection(_gt(), _est(tilt_deg=33.0))
    assert good["tilt_err_deg"] == pytest.approx(3.0)
    assert good["tilt_nan"] is False


# ------------------------------------------------------------ reporting ----
def test_first_below_95_picks_earliest_level_only():
    rows = [
        {"group": "dim_light", "level": "none", "detection_rate": 1.0,
         "false_accept_rate": 0.0, "cm_rel_err_median": 0.01},
        {"group": "dim_light", "level": "mild", "detection_rate": 0.9,
         "false_accept_rate": 0.0, "cm_rel_err_median": None},
        {"group": "dim_light", "level": "strong", "detection_rate": 0.5,
         "false_accept_rate": 0.0, "cm_rel_err_median": None},
        {"group": "card_tilt_deg", "level": 60, "detection_rate": 1.0,
         "false_accept_rate": 0.0, "cm_rel_err_median": 0.01},
    ]
    out = card_stress._first_below_95(rows)
    assert out["dim_light"] == {"level": "mild", "detection_rate": 0.9}  # earliest
    assert out["card_tilt_deg"] is None                                 # never below


def test_portion_summary_excludes_nans_and_is_seeded():
    rows = [
        {"scene_idx": 0, "vol_rel_err": 0.10, "rel_err": -0.05},
        {"scene_idx": 1, "vol_rel_err": 0.20, "rel_err": -0.15},
        {"scene_idx": 2, "vol_rel_err": None, "rel_err": None},   # NaN pose
    ]
    a = _portion_summary(rows, reps=100, seed=42)
    b = _portion_summary(rows, reps=100, seed=42)
    assert a == b                                # bootstrap is seeded
    assert a["n_scenes"] == 3 and a["n_nan"] == 1
    assert a["volume"]["n"] == 2 and a["grams"]["n"] == 2
    assert a["volume"]["signed_median"] == pytest.approx(0.15)
    assert a["grams"]["signed_median"] == pytest.approx(-0.10)


# ------------------------------------------------------------ determinism --
def test_run_suite_is_seed_deterministic():
    def run():
        return card_stress.run_suite(scenes=2, seed=13, reps=50,
                                     groups=["jpeg"], include_portion=False)
    a = run()
    card_stress._BASE_CACHE.clear()          # force a fresh re-render
    b = run()
    strip = lambda d: {k: v for k, v in d.items() if k not in VOLATILE}
    assert strip(a) == strip(b)


def test_unknown_group_is_rejected():
    with pytest.raises(ValueError, match="unknown group"):
        card_stress.run_suite(scenes=1, seed=1, reps=10,
                              groups=["no_such_group"])
