"""Protection + CLI guards for the WED evaluation (loop-setup chunks A+B).

Five things are pinned here:
  1. docs/locked_manifest.txt covers every file the evaluation is made of
     (eval code, the split definition, locked images) and check_locked
     agrees with it;
  2. check_locked actually FAILS on a changed/missing/unpinned entry —
     a lock that never fires is not a lock — and REJECTS model/training
     artifacts, which are deliberately outside the pin set;
  3. tools/run_eval refuses the locked tier without the deliberate flag and
     refuses --stress anywhere but DEV, and the DEV tier never reads the
     test split;
  4. tools/run_eval's locked path works end-to-end on a tiny fake dataset
     (temp dir, temp access log — the real log is never touched);
  5. tools/stress_suite stays behaviourally identical to the STAGE 1B
     perturbations in tools/bn_experiment.py (frozen copy, not an import).

No test here loads a model or touches the GPU.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

import tools.check_locked as check_locked
import tools.run_eval as run_eval
import tools.stress_suite as stress_suite

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "locked_manifest.txt"

REQUIRED_PINS = [
    "tools/run_eval.py",
    "tools/stress_suite.py",
    "tools/compare_runs.py",
    "tools/check_locked.py",
    "tools/build_wed_manifest.py",
    "data/wed_manifest.jsonl",
]


# ------------------------------------------------------------------- lock --
def test_manifest_pins_the_eval_code_data_and_locked_images():
    entries = check_locked.read_manifest(MANIFEST)
    for rel in REQUIRED_PINS:
        assert rel in entries, f"{rel} not pinned"
    assert any(k.startswith("data/wed/test/") for k in entries), \
        "locked images must be pinned"


def test_model_and_training_artifacts_are_not_pinned(tmp_path):
    """The model is what gets evaluated — it must stay outside the lock."""
    entries = check_locked.read_manifest(MANIFEST)
    for rel in check_locked.MODEL_ARTIFACTS:
        assert rel not in entries, f"{rel} must not be pinned"
        assert rel not in REQUIRED_PINS
    # and the guard actively rejects them if they sneak into a manifest
    bad = tmp_path / "manifest.txt"
    bad.write_text(f"{'0' * 64}  models/weight_head.py\n"
                   f"{'0' * 64}  data/weight_head_sigma.yaml\n")
    assert check_locked.check(bad, ROOT, quiet=True) == 1


def test_check_locked_passes_on_this_repo():
    assert check_locked.check(MANIFEST, ROOT, quiet=True) == 0


def test_check_locked_fails_on_a_changed_file(tmp_path):
    good = check_locked.read_manifest(MANIFEST)
    tampered = tmp_path / "manifest.txt"
    lines = [f"{'0' * 64}  {rel}" for rel in REQUIRED_PINS]
    tampered.write_text("\n".join(lines) + "\n")
    assert set(REQUIRED_PINS) <= set(good)
    assert check_locked.check(tampered, ROOT, quiet=True) == 1


def test_check_locked_fails_on_a_missing_required_file(tmp_path):
    manifest = tmp_path / "manifest.txt"
    manifest.write_text(f"{'0' * 64}  tools/definitely_not_here.py\n")
    assert check_locked.check(manifest, ROOT, quiet=True) == 1


def test_check_locked_fails_on_an_unpinned_new_eval_file(tmp_path):
    manifest = tmp_path / "manifest.txt"
    manifest.write_text("")            # nothing pinned, but scope is non-empty
    assert check_locked.check(manifest, ROOT, quiet=True) == 1


def test_check_locked_skips_absent_locked_images(tmp_path):
    """CI has no dataset: an absent data/wed/test/ file is SKIP, not a failure."""
    entries = check_locked.read_manifest(MANIFEST)
    rel = "data/wed/test/99-jan/imgsFine/never_captured.jpg"
    assert not (ROOT / rel).exists()
    entries[rel] = "0" * 64
    manifest = tmp_path / "manifest.txt"
    manifest.write_text("".join(f"{h}  {p}\n" for p, h in sorted(entries.items())))
    assert check_locked.check(manifest, ROOT, quiet=True) == 0


# -------------------------------------------------------------- eval CLI --
def test_run_eval_refuses_the_locked_tier_without_the_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        run_eval.main(["--tier", "locked"])
    assert exc.value.code == 2
    assert "--i-know-this-is-locked" in capsys.readouterr().err


def test_run_eval_refuses_stress_outside_dev(capsys):
    with pytest.raises(SystemExit) as exc:
        run_eval.main(["--tier", "train", "--stress"])
    assert exc.value.code == 2
    assert "DEV-only" in capsys.readouterr().err


def test_dev_tier_never_reads_the_test_split():
    run_eval.LOADED.clear()
    rows = run_eval.dev_rows()
    assert rows, "DEV carve is empty"
    assert "test" not in run_eval.LOADED
    assert 0 < len({run_eval.plate_key(r) for r in rows}) < 40


# ------------------------------------------------------ metric arithmetic --
def _fake_samples():
    """4 plates x 6 ROIs: steamed-rice (sigma known) + ghost-dish (no sigma),
    plus one zero-label ROI (MAPE must ignore it)."""
    sigma = run_eval.sigma_map()["steamed-rice"]
    samples, abs_errs = [], []
    for plate in range(4):
        for i in range(5):
            gt = 100.0 + 10 * i
            err = (5.0 + plate + 0.1 * i) * (1 if i % 2 == 0 else -1)
            samples.append({"plate": f"p{plate}", "dish": "steamed-rice",
                            "pred": gt + err, "gt": gt, "err": err})
            abs_errs.append(abs(err))
        samples.append({"plate": f"p{plate}", "dish": "ghost-dish",
                        "pred": 50.0, "gt": 55.0, "err": -20.0})
        abs_errs.append(20.0)
    samples.append({"plate": "p0", "dish": "steamed-rice", "pred": 3.0,
                    "gt": 0.0, "err": 3.0})
    abs_errs.append(3.0)
    return samples, float(np.mean(abs_errs)), sigma


def test_summarize_metrics_intervals_and_skips():
    samples, expect_mae, sigma = _fake_samples()
    rep = run_eval.summarize(samples, tier="dev", seed=42, views=8)
    assert rep["tier"] == "dev"
    assert rep["n_samples"] == 25 and rep["n_plates"] == 4 and rep["n_views"] == 8
    assert rep["mae_g"] == pytest.approx(round(expect_mae, 3))
    assert rep["n_mape_excluded_lt1g"] == 1          # the gt = 0 ROI
    assert rep["mape_pct"] > 0
    assert rep["n_skipped_no_sigma"] == 4            # ghost-dish has no sigma entry
    assert rep["coverage_90"] == pytest.approx(1.0)  # pred sits inside +-z*sigma
    assert rep["mean_interval_width_g"] == pytest.approx(
        round(2 * run_eval.Z90 * sigma, 2))
    assert rep["worst3_dishes"][0] == ("ghost-dish", 20.0)
    assert len(rep["per_dish_mae_g"]) == 2


def test_bootstrap_is_over_plates_and_seed_deterministic():
    samples, *_ = _fake_samples()
    a = run_eval.summarize(samples, tier="dev", seed=7, views=8)
    b = run_eval.summarize(samples, tier="dev", seed=7, views=8)
    assert run_eval.BOOTSTRAP_REPS >= 1000
    assert a["mae_g_bootstrap_95ci"] is not None
    assert a["coverage_bootstrap_95ci"] == [1.0, 1.0]
    assert a["mae_g_bootstrap_95ci"] == b["mae_g_bootstrap_95ci"]   # fixed seed
    assert a["coverage_bootstrap_95ci"] == b["coverage_bootstrap_95ci"]
    lo, hi = a["mae_g_bootstrap_95ci"]
    assert lo <= a["mae_g"] <= hi


def test_bootstrap_resamples_plates_not_views():
    """One perfect plate + one terrible plate: only a plate bootstrap can
    produce the degenerate ends 0 g and 100 g (a view bootstrap of 24 iid
    ROIs never does)."""
    samples = []
    for plate, err in (("good", 0.0), ("bad", 100.0)):
        for _ in range(12):
            gt = 200.0
            samples.append({"plate": plate, "dish": "steamed-rice",
                            "pred": gt + err, "gt": gt, "err": err})
    rep = run_eval.summarize(samples, tier="dev", seed=42, views=24)
    assert rep["mae_g"] == pytest.approx(50.0)
    assert rep["mae_g_bootstrap_95ci"] == [0.0, 100.0]


# --------------------------------------------------------- frozen stress --
def _probe() -> tuple[np.ndarray, np.ndarray]:
    """Deterministic 64x64 RGB image + uint8 mask (fixed pattern, no RNG)."""
    y, x = np.mgrid[0:64, 0:64]
    img = np.stack([(x * 4) % 256, (y * 4) % 256, ((x + y) * 2) % 256],
                   axis=-1).astype(np.uint8)
    mask = np.where(((x - 32) ** 2 + (y - 32) ** 2) < 400, 1, 0).astype(np.uint8)
    return img, mask


def test_stress_suite_matches_the_bn_experiment():
    from PIL import Image
    from tools import bn_experiment

    assert set(stress_suite.PERTURBATIONS) == set(bn_experiment.STRESS)
    base_img, base_mask = _probe()
    for name, fn in stress_suite.PERTURBATIONS.items():
        got_i, got_m = fn(Image.fromarray(base_img), Image.fromarray(base_mask))
        want_i, want_m = bn_experiment.STRESS[name](Image.fromarray(base_img),
                                                    Image.fromarray(base_mask))
        assert np.array_equal(np.array(got_i), np.array(want_i)), f"image drift: {name}"
        assert np.array_equal(np.array(got_m), np.array(want_m)), f"mask drift: {name}"


def test_stress_is_labelled_as_not_real_world():
    assert stress_suite.STRESS_LABEL == "WED stress test, not real-world"
    assert len(stress_suite.PERTURBATIONS) == 5


# ------------------------------------------------ locked path (fake data) --
def _prepare_fake_locked(tmp_path, monkeypatch):
    """Tiny synthetic 'WED test' dataset + a stub head; nothing real is read."""
    import torch
    from PIL import Image

    wed = tmp_path / "wed"
    wed.mkdir()
    rows = []
    for vi in range(2):
        img = np.full((32, 32, 3), 120 + 20 * vi, dtype=np.uint8)
        mask = np.zeros((32, 32), dtype=np.uint8)
        mask[:16, :] = 1          # class_id 1 -> slot 0
        mask[16:, :] = 2          # class_id 2 -> slot 1
        Image.fromarray(img).save(wed / f"img{vi}.png")
        Image.fromarray(mask).save(wed / f"mask{vi}.png")
        rows.append({
            "split": "test", "date_key": f"2026010{vi}", "set": "set1",
            "image": f"img{vi}.png", "mask": f"mask{vi}.png",
            "dishes": [{"class_id": 1, "name": "steamed-rice", "weight_g": 100.0},
                       {"class_id": 2, "name": "sambar", "weight_g": 50.0}],
        })

    class _StubHead:
        def eval(self):
            return self

        def encode(self, imgs):
            return torch.zeros(imgs.shape[0], 4, 4, 4, device=imgs.device)

        def __call__(self, feats, rois):
            return torch.full((rois.shape[0], 2), 60.0, device=rois.device)

    class _StubWeightHead:
        @staticmethod
        def load(path, device=None):
            return _StubHead()

    log = tmp_path / "locked_access_log.txt"
    monkeypatch.setattr(run_eval, "WeightHead", _StubWeightHead)
    monkeypatch.setattr(run_eval, "wed_root", lambda: wed)
    monkeypatch.setattr(run_eval, "slot_names",
                        lambda: {0: "steamed-rice", 1: "sambar"})
    monkeypatch.setattr(run_eval, "sigma_map", lambda: {"steamed-rice": 20.0})
    monkeypatch.setattr(run_eval, "LOCKED_LOG", log)
    monkeypatch.setattr(run_eval, "load_manifest",
                        lambda split: [dict(r) for r in rows])
    run_eval.LOADED.clear()
    return log


def test_locked_path_refuses_without_the_flag(tmp_path, monkeypatch):
    log = _prepare_fake_locked(tmp_path, monkeypatch)
    with pytest.raises(SystemExit) as exc:
        run_eval.main(["--tier", "locked", "--out", str(tmp_path / "r.json")])
    assert exc.value.code != 0
    assert not log.exists()
    assert run_eval.LOADED == []            # nothing was read


def test_locked_path_runs_and_appends_exactly_one_line(tmp_path, monkeypatch):
    import json
    real_log = ROOT / "docs" / "locked_access_log.txt"
    before = real_log.read_text() if real_log.exists() else None
    log = _prepare_fake_locked(tmp_path, monkeypatch)
    out = tmp_path / "run_eval_locked.json"
    rc = run_eval.main(["--tier", "locked", "--i-know-this-is-locked",
                        "--out", str(out)])
    assert rc == 0
    lines = log.read_text().splitlines()
    assert len(lines) == 1, "exactly one access-log line per locked run"
    assert "tier=locked" in lines[0]
    assert "--i-know-this-is-locked" in lines[0]
    rep = json.loads(out.read_text())
    assert rep["tier"] == "locked"
    assert sorted(rep["per_plate"]) == ["20260100_set1", "20260101_set1"]
    assert isinstance(rep["wall_s"], float)
    assert run_eval.LOADED == ["test"]
    after = real_log.read_text() if real_log.exists() else None
    assert after == before                 # the real access log is never touched


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
