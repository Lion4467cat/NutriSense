"""STAGE 3: OOM handling — one retry per model stage, then a structured result.

Every test raises torch.OutOfMemoryError from a stub stage; no real GPU
allocation is attempted, so these run on CPU-only machines too (the import
of torch itself is what the guard checks, not CUDA availability).
"""
import torch

from engine.contract import WIRE_KEYS
from engine.pipeline import analyze as pipe_analyze
from models import registry
from tests.test_pipeline_seams import make_deps, no_card_scene, scene


def _fake_oom():
    return torch.OutOfMemoryError("CUDA out of memory (synthetic test)")


class _OomOnceHead:
    """WeightHead stand-in: the first predict() call raises a fake CUDA OOM."""

    meta = {"recipe": "oom-test-head"}

    def __init__(self, grams=250.0):
        self.grams = grams
        self.calls = 0
        self.pending_oom = True

    def predict(self, image_bgr, mask, slot_ids, device=None):
        self.calls += 1
        if self.pending_oom:
            self.pending_oom = False
            raise _fake_oom()
        n = len(slot_ids)
        return {"grams": self.grams,
                "slots": {s: round(self.grams / n, 2) for s in slot_ids},
                "slots_clamped": False}


def test_oom_retries_once_then_succeeds(scene, monkeypatch):
    recovered = {"unload": 0, "clear_cache": 0}
    monkeypatch.setattr(
        registry, "unload",
        lambda *a, **k: recovered.__setitem__("unload", recovered["unload"] + 1))
    monkeypatch.setattr(
        registry, "clear_cache",
        lambda: recovered.__setitem__("clear_cache", recovered["clear_cache"] + 1))

    deps = make_deps(scene)
    calls = {"n": 0}

    def flaky_segment(img):
        calls["n"] += 1
        if calls["n"] == 1:
            raise _fake_oom()
        return deps["segment"](img)

    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, segment=flaky_segment))
    assert calls["n"] == 2                      # exactly one retry
    assert recovered["unload"] >= 1             # registry model offload ran
    assert recovered["clear_cache"] >= 1        # cache clear ran
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}
    assert out["failures"] == []
    assert out["degradations"] == ["gpu_oom_retried"]
    assert out["portion"]["grams"] > 0
    assert out["path_used"] == "card_geometry"


def test_oom_twice_is_structured_failure_never_crash(scene):
    def always_oom(img):
        raise _fake_oom()

    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, segment=always_oom))
    assert set(out) == set(WIRE_KEYS)           # full shape, never a 500
    assert out["verdict"] == "cannot_verify"
    assert out["failures"][0]["kind"] == "stage_failed"
    assert out["failures"][0]["stage"] == "segment"
    assert "OutOfMemoryError" in out["failures"][0]["error"]
    assert out["reasons"][0]["kind"] == "stage_failed"
    assert out["degradations"] == ["gpu_oom_retried"]  # retry was attempted
    assert out["portion"] is None
    assert out["path_used"] is None


def test_oom_inside_head_retries_to_learned_grams(no_card_scene):
    head = _OomOnceHead(250.0)
    out = pipe_analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(no_card_scene) | {"weight_head": head})
    assert head.calls == 2                      # OOM, then the successful retry
    assert out["failures"] == []
    assert out["degradations"] == ["gpu_oom_retried"]
    assert out["portion"]["grams_source"] == "learned_weight"
    assert out["path_used"] == "learned_head"
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}


def test_clean_run_records_no_degradations(scene):
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    assert out["degradations"] == []
    assert out["failures"] == []
    assert out["path_used"] == "card_geometry"
