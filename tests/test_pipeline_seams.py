"""TDD seam tests for the full pipeline (S6 analyze + API).

Confirmed seams (7):
  1. lint resolution-note branch
  2. segment-failure branch
  3. classify-unrecognized branch
  4. depth-calibration wiring (measured vs prior)
  5. portion-failure branch
  6. result-assembly contract
  7. HTTP contract (validation + serving_style echo)
"""
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

import models.food_classifier as fc
from engine.pipeline import analyze as pipe_analyze
from main import app
from tests.synth.scene import render_scene

client = TestClient(app)


@pytest.fixture(scope="module")
def scene():
    return render_scene()


def make_deps(scene, *, segment=None, classify=None, depth=None):
    """Deps with GT stubs that adapt to the input image size."""
    def seg(img):
        h, w = img.shape[:2]
        m = scene["mask_food"]
        if m.shape[:2] != (h, w):
            m = cv2.resize(m.astype(np.uint8), (w, h),
                           interpolation=cv2.INTER_NEAREST)
        return {"mask": m, "strategy": "stub", "sam_score": 1.0,
                "n_candidates": 1, "area_frac": 0.2}

    def dep(img):
        h, w = img.shape[:2]
        d = scene["depth_m"]
        if d.shape[:2] != (h, w):
            d = cv2.resize(d, (w, h))
        return {"depth_m": d, "model": "gt"}

    def cls(img):
        return {"dish": "rice_sambar", "confidence": 1.0, "method": "stub",
                "match_score": 0.9, "reason": "stub"}

    return {"segment": segment or seg,
            "depth": depth or dep,
            "classify": classify or cls}


# --- seam 1: lint resolution-note branch --------------------------------

def test_lint_resolution_note_is_non_blocking(scene):
    # default scene min side = 1100 < 1280 protocol minimum
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    assert out["lint"]["resolution_ok"] is False
    assert any("min side" in n for n in out["lint"]["notes"])
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}


def test_lint_resolution_ok_large_image(scene):
    big = cv2.resize(scene["image_bgr"], (1500, 1400),
                     interpolation=cv2.INTER_CUBIC)
    out = pipe_analyze(big, day="mon", band="1-5", deps=make_deps(scene))
    assert out["lint"]["resolution_ok"] is True
    assert out["lint"]["notes"] == []
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}


# --- seam 2: segment-failure branch --------------------------------------

def test_segment_failure_cannot_verify(scene):
    def boom(img):
        raise RuntimeError("segment exploded")

    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, segment=boom))
    assert out["verdict"] == "cannot_verify"
    assert any(r["kind"] == "stage_failed"
               and "segment exploded" in r["text"] for r in out["reasons"])
    assert out["failures"][0]["stage"] == "segment"
    assert out["anchor"] is not None  # anchor ran before segment
    assert out["segmentation"] is None
    assert out["classification"] is None
    assert out["portion"] is None


# --- seam 3: classify-unrecognized branch ---------------------------------

def test_classify_unrecognized_cannot_verify(scene):
    def unknown(img):
        return {"dish": None, "confidence": 0.2, "method": "gallery",
                "match_score": 0.3, "reason": "below threshold"}

    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, classify=unknown))
    assert out["verdict"] == "cannot_verify"
    assert any(r["kind"] == "unrecognized" and "dish unrecognized" in r["text"]
               for r in out["reasons"])
    assert out["failures"] == []  # abstain is an outcome, not a hard failure
    assert out["classification"]["dish"] is None
    assert out["classification"]["reason"] == "below threshold"
    assert out["segmentation"] is not None  # segment ran before classify
    assert out["portion"] is None
    assert out["nutrition"] is None


# --- seam 4: depth-calibration wiring -------------------------------------

@pytest.fixture(scope="module")
def no_card_scene():
    return render_scene({"anchor": {"card": False}})


def test_depth_scale_calibrated_and_recorded(scene):
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    assert out["anchor"]["tier"] == "measured"
    assert out["anchor"]["depth_scale_source"] == "card"
    # GT depth is already metric: calibration factor must stay near 1
    assert 0.5 < out["anchor"]["depth_scale_factor"] < 2.0


def test_depth_scale_none_on_prior_tier(no_card_scene):
    out = pipe_analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(no_card_scene))
    assert out["anchor"]["tier"] == "prior"
    assert out["anchor"]["depth_scale_source"] == "none"
    assert out["anchor"]["depth_scale_factor"] == 1.0
    # plan rule: prior tier caps coverage at 0.60 -> never PASS/FAIL
    assert out["verdict"] == "BORDERLINE"


# --- seam 5: portion-failure branch ---------------------------------------

def test_depth_failure_cannot_verify(scene):
    def boom(img):
        raise RuntimeError("depth exploded")

    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, depth=boom))
    assert out["verdict"] == "cannot_verify"
    assert any(r["kind"] == "stage_failed" and "depth exploded" in r["text"]
               for r in out["reasons"])
    assert out["failures"][0]["stage"] == "depth"
    assert out["classification"]["dish"] == "rice_sambar"
    assert out["dish"] is not None  # dish lookup happened before portion
    assert out["portion"] is None
    assert out["nutrition"] is None


# --- seam 6: result-assembly contract -------------------------------------

def test_result_contract_keys_and_types(scene):
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene), serving_style="mixed")
    # API response contract (spec literal, not derived from the code)
    assert set(out) == {
        "verdict", "reasons", "failures", "lint", "anchor", "segmentation",
        "classification", "dish", "portion", "nutrition", "coverage",
        "assumptions", "advisory", "model_versions", "compliance", "policy",
    }
    assert out["failures"] == []
    assert out["policy"]["pass_p"] == 0.9 and out["policy"]["lint_min_side_px"] == 1280
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}
    assert isinstance(out["reasons"], list)
    assert isinstance(out["portion"]["grams"], float) and out["portion"]["grams"] > 0
    assert isinstance(out["portion"]["sigma_grams_rel"], float)
    assert set(out["portion"]["flags"]) <= {
        "depth_partial", "vessel_shape_uncertain", "base_sign_flip",
        "thin_layer", "size_prior_scale"}
    assert "interval_90" in out["nutrition"]["kcal"]
    assert "interval_90" in out["nutrition"]["protein_g"]
    assert isinstance(out["coverage"]["score"], float)
    assert 0.0 <= out["coverage"]["score"] <= 1.0
    assert set(out["model_versions"]) == {"segmenter", "classifier", "depth"}
    assert out["model_versions"]["segmenter"] == "facebook/sam2.1-hiera-large"
    assert out["dish"]["serving_style"] == "mixed"
    assert out["dish"]["id"] == "rice_sambar"
    assert isinstance(out["assumptions"], list)


def test_result_contract_flags_populated_on_ring_path(scene):
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    # card anchor + healthy area -> ring path, no uncertainty flags
    assert out["portion"]["base_method"] == "ring"
    assert out["portion"]["flags"] == []


# --- seam 7: HTTP contract -------------------------------------------------

@pytest.fixture(scope="module")
def jpg_bytes(scene):
    ok, buf = cv2.imencode(".jpg", scene["image_bgr"],
                           [cv2.IMWRITE_JPEG_QUALITY, 95])
    assert ok
    return buf.tobytes()


def test_http_missing_required_field_422(jpg_bytes):
    r = client.post("/analyze",
                    files={"file": ("p.jpg", jpg_bytes, "image/jpeg")},
                    data={"day": "mon"})  # band omitted
    assert r.status_code == 422
    locs = [e["loc"] for e in r.json()["detail"]]
    assert any("band" in loc for loc in locs)


def test_http_serving_style_echo(jpg_bytes, monkeypatch):
    monkeypatch.setattr(fc, "classify_dish", lambda img, **kw: {
        "dish": "rice_sambar", "confidence": 1.0, "method": "stub",
        "match_score": 0.9, "margin": None, "scores": {}, "uncovered": [],
        "reason": "test stub"})
    r = client.post("/analyze",
                    files={"file": ("p.jpg", jpg_bytes, "image/jpeg")},
                    data={"day": "mon", "band": "1-5",
                          "serving_style": "mixed"})
    assert r.status_code == 200
    body = r.json()
    assert body["dish"]["serving_style"] == "mixed"
    assert body["dish"]["id"] == "rice_sambar"
    assert body["verdict"] in {"PASS", "FAIL", "BORDERLINE"}


# --- seam 8 (added for frontend): compliance data pass-through -------------

def test_result_contract_compliance_block(scene):
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    comp = out["compliance"]
    assert comp["day"] == "mon"
    assert comp["band"] == "1-5"
    assert set(comp["probs"]) == {"kcal", "protein_g"}
    for key in ("kcal", "protein_g"):
        assert 0.0 <= comp["probs"][key] <= 1.0
        row = comp["nutrients"][key]
        assert row["min"] > 0
        assert row["p_at_or_above_min"] == pytest.approx(comp["probs"][key])
        lo, hi = row["interval_90"]
        assert lo <= row["mean"] <= hi
        assert row["headroom_at_interval_low"] == pytest.approx(
            lo - row["min"], abs=0.011)  # API rounds to 2 decimals
