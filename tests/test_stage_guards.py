"""Stage guards over HTTP: a raising stage becomes cannot_verify, never 500.

The model-loading deps seam does not cross the HTTP boundary, so these tests
patch the stage entry points in the same places analyze() resolves them.
"""
import cv2
import pytest
from fastapi.testclient import TestClient

import engine.pipeline as pipeline
import models.dish_segmenter as dish_segmenter
import models.food_classifier as food_classifier
from engine.contract import WIRE_KEYS
from main import app
from tests.test_pipeline_seams import make_deps

client = TestClient(app)


@pytest.fixture(scope="module")
def scene():
    from tests.synth.scene import render_scene
    return render_scene()


def _stub_stages(scene, monkeypatch, *, classify=None):
    """Wire GT stubs in exactly where analyze() resolves them (no models)."""
    deps = make_deps(scene, classify=classify)
    monkeypatch.setattr(dish_segmenter, "segment_food", deps["segment"])
    monkeypatch.setattr(food_classifier, "classify_dish", deps["classify"])
    monkeypatch.setattr(pipeline, "_get_depth_provider", lambda: deps["depth"])


def _post(image_bgr, day="mon", band="1-5"):
    ok, buf = cv2.imencode(".jpg", image_bgr)
    assert ok
    r = client.post("/analyze", files={"file": ("p.jpg", buf.tobytes())},
                    data={"day": day, "band": band})
    assert r.status_code == 200
    return r.json()


def _assert_guard(body, stage_name):
    assert body["verdict"] == "cannot_verify"
    assert body["failures"][0]["kind"] == "stage_failed"
    assert body["failures"][0]["stage"] == stage_name
    assert body["reasons"][0]["kind"] == "stage_failed"
    assert stage_name in body["reasons"][0]["text"]


def test_classify_raise_is_guarded(scene, monkeypatch):
    def boom(img):
        raise RuntimeError("classifier exploded")
    _stub_stages(scene, monkeypatch, classify=boom)
    body = _post(scene["image_bgr"])
    _assert_guard(body, "classify")
    assert body["segmentation"] is not None and body["dish"] is None


def test_nutrition_raise_is_guarded(scene, monkeypatch):
    _stub_stages(scene, monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("mc exploded")
    monkeypatch.setattr(pipeline, "sample_nutrients", boom)
    body = _post(scene["image_bgr"])
    _assert_guard(body, "nutrition")
    assert body["portion"] is not None and body["nutrition"] is None


def test_compliance_raise_is_guarded(scene, monkeypatch):
    _stub_stages(scene, monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("assess exploded")
    monkeypatch.setattr(pipeline, "assess", boom)
    body = _post(scene["image_bgr"])
    _assert_guard(body, "compliance")
    assert body["nutrition"] is not None and body["coverage"] is None


def test_anchor_raise_degrades_to_prior(scene, monkeypatch):
    _stub_stages(scene, monkeypatch)

    def boom(*a, **k):
        raise RuntimeError("card detector died")
    monkeypatch.setattr(pipeline, "estimate_anchor", boom)
    body = _post(scene["image_bgr"])
    assert body["failures"] == []            # degrade: silent, no failures[]
    assert body["anchor"]["tier"] == "prior"
    assert body["verdict"] in {"PASS", "FAIL", "BORDERLINE",
                               "cannot_verify", "out_of_scope"}


def test_unreadable_image_is_full_shape():
    r = client.post("/analyze", files={"file": ("p.jpg", b"not an image")},
                    data={"day": "mon", "band": "1-5"})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == set(WIRE_KEYS)
    assert body["verdict"] == "cannot_verify"
    assert body["failures"][0]["kind"] == "input_unreadable"
    assert body["reasons"][0]["kind"] == "unreadable"
    assert body["policy"]["policy_version"]
