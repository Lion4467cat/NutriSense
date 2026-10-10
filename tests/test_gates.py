"""Hard gates: one table, consulted by analyze() — the path production crosses.

Every abstention carries Failure + Reason from the single gate_reject helper,
with stage attribution zoom/day/band -> input and scope -> classify.
"""
import pytest

from engine.contract import FailureKind, ReasonKind, Stage
from engine.pipeline import analyze as pipe_analyze
from tests.test_pipeline_seams import make_deps


@pytest.fixture(scope="module")
def scene():
    from tests.synth.scene import render_scene
    return render_scene()


def _admitted_plate(scene, **kw):
    deps = make_deps(scene, **kw)
    return deps


def _zoom_gate(scene):
    exif = {"focal_mm": 4.0, "subject_distance_cm": None,
            "digital_zoom": 2.0, "camera": None}
    deps = _admitted_plate(scene)
    return pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                        exif=exif, deps=deps)


def test_zoom_gate_abstains_with_kind_membership(scene):
    out = _zoom_gate(scene)
    assert out["verdict"] == "cannot_verify"
    assert out["reasons"][0]["kind"] == "zoom"
    assert out["failures"][0]["kind"] == "gate_rejected"
    assert out["failures"][0]["stage"] == "input"
    assert out["failures"][0]["error"] == out["reasons"][0]["text"]


def test_unknown_day_gate(scene):
    deps = _admitted_plate(scene)
    out = pipe_analyze(scene["image_bgr"], day="sunday", band="1-5", deps=deps)
    assert out["verdict"] == "cannot_verify"
    assert out["reasons"][0]["kind"] == "unknown_day"
    assert out["failures"][0]["stage"] == "input"


def test_unknown_band_gate(scene):
    deps = _admitted_plate(scene)
    out = pipe_analyze(scene["image_bgr"], day="mon", band="99-100", deps=deps)
    assert out["verdict"] == "cannot_verify"
    assert out["reasons"][0]["kind"] == "unknown_band"
    assert out["failures"][0]["stage"] == "input"


def test_scope_gate_abstains_at_classify(scene):
    deps = _admitted_plate(scene, classify=lambda img: {
        "dish": "wheat_product", "confidence": 1.0, "method": "stub",
        "match_score": 0.9, "reason": "stub"})
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5", deps=deps)
    assert out["verdict"] == "out_of_scope"
    assert out["reasons"][0]["kind"] == "out_of_scope"
    assert out["failures"][0]["kind"] == "gate_rejected"
    assert out["failures"][0]["stage"] == "classify"


def test_admitted_plate_carries_no_gate_abstentions(scene):
    deps = _admitted_plate(scene)
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5", deps=deps)
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}
    assert out["failures"] == []
    gate_kinds = {"zoom", "unknown_day", "unknown_band", "out_of_scope"}
    assert not any(r["kind"] in gate_kinds for r in out["reasons"])
