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

import engine.pipeline as _pipeline
import models.dish_segmenter as dish_segmenter
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

    def dep(img, **_kw):
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
    # STAGE 5: a headless no-card run on a mapped dish cannot verify, so a
    # working fake head is injected to reach the prior-tier depth wiring.
    out = pipe_analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(no_card_scene) | {"weight_head": _FakeHead(310.0)})
    assert out["anchor"]["tier"] == "prior"
    assert out["anchor"]["depth_scale_source"] == "none"
    assert out["anchor"]["depth_scale_factor"] == 1.0
    # no reference card + learned grams -> scored verdict with the
    # no-card disclaimer leading the reasons
    assert out["verdict"] in {"PASS", "BORDERLINE", "FAIL"}
    assert any(r["kind"] == "no_reference_card" for r in out["reasons"])


# --- seam 5: portion-failure branch ---------------------------------------

def test_depth_failure_cannot_verify(scene):
    def boom(img, **_kw):
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
        "path_used", "degradations", "items",
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
    assert out["degradations"] == []            # nothing degraded on this run
    assert out["path_used"] == "card_geometry"  # measured tier ran geometry


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


def test_http_serving_style_echo(jpg_bytes, monkeypatch, scene):
    # HTTP does not cross the deps seam: stub segment/depth at the exact
    # points analyze() resolves them (as test_stage_guards does) so this
    # non-gpu test never loads SAM2/MoGe weights.
    deps = make_deps(scene)
    monkeypatch.setattr(dish_segmenter, "segment_food", deps["segment"])
    monkeypatch.setattr(_pipeline, "_get_depth_provider", lambda: deps["depth"])
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


# --- seam 9: assess()'s failures reach the wire (typed result) -------------

def test_assess_failures_reach_the_wire(scene, monkeypatch):
    from engine import pipeline as pl
    from engine.compliance import AssessResult
    from engine.contract import (Failure, FailureKind, Stage,
                                 reason_for_failure)

    f = Failure(FailureKind.STAGE_FAILED, Stage.NUTRITION,
                "no nutrient samples")

    def fake_assess(mc, portion, dish, band, anchor_label, day=None,
                    depth_scale_source=None):
        return AssessResult(verdict="cannot_verify",
                            reasons=[reason_for_failure(f)], failures=[f],
                            day=day, band=band)

    monkeypatch.setattr(pl, "assess", fake_assess)
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    assert out["verdict"] == "cannot_verify"
    assert out["failures"] and out["failures"][0]["stage"] == "nutrition"
    assert any(r["kind"] == "stage_failed" for r in out["reasons"])


# --- seam 10: fov_x reaches the depth stage -------------------------------

def test_depth_receives_known_fov_x(scene):
    seen = {}

    def dep(img, **kw):
        seen.update(kw)
        h, w = img.shape[:2]
        d = scene["depth_m"]
        if d.shape[:2] != (h, w):
            d = cv2.resize(d, (w, h))
        return {"depth_m": d, "model": "gt"}

    pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                 deps=make_deps(scene, depth=dep))
    assert "fov_x" in seen
    assert 0.0 < seen["fov_x"] < 180.0


# --- seam 11: declined calibration caps coverage --------------------------

def test_uncalibrated_measured_depth_cannot_certify(scene, monkeypatch):
    from engine import pipeline as pl

    def decline(depth_m, anchor, K):
        return depth_m, 1.0, "none"

    monkeypatch.setattr(pl, "calibrate_depth_scale", decline)
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    assert out["anchor"]["tier"] == "measured"
    factors = out["coverage"]["factors"]
    assert factors["depth_uncalibrated"] == 0.80
    assert out["coverage"]["score"] == 0.80
    assert out["verdict"] == "BORDERLINE"  # C < pass_min: no PASS/FAIL


# --- seam 12: learned weight head (no reference card, ADR-0002) -----------

class _FakeHead:
    """WeightHead stand-in: same predict() contract, deterministic grams."""

    meta = {"recipe": "fake-test-head", "test_mae_g": 14.51}

    def __init__(self, grams=310.0):
        self.grams = grams
        self.calls = []

    def predict(self, image_bgr, mask, slot_ids, device=None):
        self.calls.append(list(slot_ids))
        n = len(slot_ids)
        per = {s: round(self.grams / n, 2) for s in slot_ids}
        return {"grams": self.grams, "slots": per, "slots_clamped": False}


def test_learned_head_replaces_prior_geometry(no_card_scene):
    head = _FakeHead(310.0)
    out = pipe_analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(no_card_scene) | {"weight_head": head})
    # rice_sambar maps to [steamed-rice, sambar] slots in wed_dishes.yaml
    assert head.calls and head.calls[0] == [33, 32]
    p = out["portion"]
    assert p["grams"] == 310.0
    assert p["base_method"] == "learned_weight"
    assert p["grams_source"] == "learned_weight"
    assert p["scale_tier"] == "prior"
    assert p["mean_h_mm"] is None and p["area_cm2"] is None  # no depth aux
    assert "learned_weight_applied" in p["flags"]
    assert p["sigma_grams_rel"] > 0
    assert set(p["head_slots"]) == {"33", "32"}
    assert abs(sum(p["components_g"].values()) - 310.0) < 0.5
    # graduated (ADR-0002 amendment): scored verdict + no-card disclaimer
    assert out["verdict"] in {"PASS", "BORDERLINE", "FAIL"}
    assert out["coverage"]["factors"]["estimated_weight"] == 0.9
    assert any(r["kind"] == "no_reference_card" for r in out["reasons"])
    assert any("learned model" in r["text"] for r in out["reasons"])
    assert any("learned weight head" in a for a in out["assumptions"])
    assert out["model_versions"]["weight_head"] == "fake-test-head (test MAE 14.51g)"
    assert out["failures"] == []
    assert out["path_used"] == "learned_head"   # head produced the grams
    assert out["degradations"] == []            # head present: nothing degraded


def test_learned_head_failure_cannot_verify(no_card_scene):
    class Boom:
        meta = {}

        def predict(self, *a, **k):
            raise RuntimeError("cuda exploded")

    out = pipe_analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(no_card_scene) | {"weight_head": Boom()})
    # STAGE 3: no silent geometry substitution — the plate cannot be verified
    assert out["verdict"] == "cannot_verify"
    assert out["portion"] is None                 # no grams reach the wire
    assert out["failures"][0]["kind"] == "weight_head_unavailable"
    assert out["failures"][0]["stage"] == "portion"
    assert out["reasons"][0]["kind"] == "weight_head_unavailable"
    assert "cuda exploded" in out["reasons"][0]["text"]
    assert out["path_used"] is None               # no portion path ran


def test_weight_head_none_cannot_verify_mapped_dish(no_card_scene):
    # STAGE 5: explicit None head == failing head on a mapped dish
    out = pipe_analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(no_card_scene) | {"weight_head": None})
    assert out["verdict"] == "cannot_verify"
    assert out["portion"] is None               # no grams reach the wire
    assert out["path_used"] is None
    assert out["degradations"] == []
    assert out["failures"][0]["kind"] == "weight_head_unavailable"
    assert out["failures"][0]["stage"] == "portion"
    assert out["reasons"][0]["kind"] == "weight_head_unavailable"
    assert "checkpoint missing or failed to load" in out["reasons"][0]["text"]


def test_missing_checkpoint_cannot_verify_mapped_dish(no_card_scene):
    # STAGE 5: no weight_head in deps -> _get_weight_head() -> the hermetic
    # registry pin (a stand-in for a missing data/weight_head.pt) -> None.
    out = pipe_analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(no_card_scene))
    assert out["verdict"] == "cannot_verify"
    assert out["portion"] is None
    assert out["path_used"] is None
    assert out["degradations"] == []
    assert len(out["failures"]) == 1
    assert out["failures"][0]["kind"] == "weight_head_unavailable"
    assert out["failures"][0]["stage"] == "portion"
    assert out["reasons"][0]["kind"] == "weight_head_unavailable"
    assert "checkpoint missing or failed to load" in out["reasons"][0]["text"]


def test_learned_head_not_used_when_card_measured(scene):
    head = _FakeHead(310.0)
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene) | {"weight_head": head})
    assert head.calls == []                          # measured tier wins
    assert out["portion"]["base_method"] == "ring"
    assert out["portion"]["grams_source"] == "geometry"
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}


def test_measured_moge_uses_table_plane_but_gt_depth_keeps_ring(scene):
    deps = make_deps(scene)

    def moge(img, **kw):
        out = deps["depth"](img, **kw)
        out["model"] = _pipeline.MOGE_MODEL_ID
        return out

    real = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                        deps=deps | {"depth": moge})
    synthetic = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                             deps=deps)
    assert real["portion"]["base_method"] == "table_prior"
    assert "vessel_shape_uncertain" in real["portion"]["flags"]
    assert synthetic["portion"]["base_method"] == "ring"


# --- seam 13: recognized off-menu dish (spec 002 decision 3, ledger 003) ---
#
# A recognized-but-not-on-menu dish IS recognized: grams + nutrients on the
# wire, verdict cannot_verify, `off_menu_dish` LEADING the reasons;
# out_of_scope stays only for unrecognized captures and explicitly-scoped
# menu dishes (SCOPE gate). Menu-dish paths are untouched above.

def _classify_stub(key):
    def cls(img):
        return {"dish": key, "confidence": 0.8, "method": "stub",
                "match_score": 0.91, "reason": "stub"}
    return cls


def test_recognized_off_menu_learns_grams_and_cannot_verify(no_card_scene):
    from config import load_wed_index

    head = _FakeHead(220.0)
    out = pipe_analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(no_card_scene)
                       | {"weight_head": head, "classify": _classify_stub("rajma")})
    assert out["verdict"] == "cannot_verify"
    assert out["reasons"][0]["kind"] == "off_menu_dish"       # leads the reasons
    assert any(r["kind"] == "no_reference_card" for r in out["reasons"][1:])
    assert out["failures"] == []                              # an outcome, not a fault
    assert out["dish"]["id"] == "rajma"
    assert out["dish"]["nutrition_source"] == "generic"       # generic table, not menu
    assert out["portion"]["grams"] == 220.0
    assert out["portion"]["base_method"] == "learned_weight"
    assert out["portion"]["grams_source"] == "learned_weight"
    assert head.calls and head.calls[0] == [load_wed_index()["rajma"]]
    assert "interval_90" in out["nutrition"]["kcal"]
    assert "interval_90" in out["nutrition"]["protein_g"]
    assert "dal_curry" in out["nutrition"]["assumed_nutrients"]  # assumed, flagged
    assert out["compliance"] is None                          # no school compliance
    assert out["path_used"] == "learned_head"
    assert not any(r["kind"] == "out_of_scope" for r in out["reasons"])


def test_recognized_off_menu_geometry_with_measured_card(scene):
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene) | {"classify": _classify_stub("steamed-rice")})
    assert out["verdict"] == "cannot_verify"
    assert out["reasons"][0]["kind"] == "off_menu_dish"
    assert not any(r["kind"] == "no_reference_card" for r in out["reasons"])
    assert out["portion"]["grams"] > 0
    assert out["portion"]["base_method"] == "ring"           # measured geometry ran
    assert out["path_used"] == "card_geometry"
    assert "interval_90" in out["nutrition"]["kcal"]
    assert out["compliance"] is None
    assert out["failures"] == []


def test_off_menu_head_unavailable_still_precedes_nothing(no_card_scene):
    # off-menu mapped dish + missing head keeps the mapped-dish contract:
    # WeightHeadUnavailable -> cannot_verify, no grams, no silent geometry.
    out = pipe_analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(no_card_scene)
                       | {"classify": _classify_stub("rajma")})
    assert out["verdict"] == "cannot_verify"
    assert out["portion"] is None
    assert out["path_used"] is None
    assert out["failures"][0]["kind"] == "weight_head_unavailable"


def test_menu_equivalent_class_keeps_out_of_scope_verdict(scene):
    # 'phulka' is a WED class whose serving target is the menu dish
    # wheat_product (out_of_scope) — that verdict path stays byte-for-byte.
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene) | {"classify": _classify_stub("phulka")})
    assert out["verdict"] == "out_of_scope"
    assert out["reasons"][0]["kind"] == "out_of_scope"
    assert out["dish"]["id"] == "wheat_product"
    assert out["portion"] is None
    assert out["failures"][0]["kind"] == "gate_rejected"


def test_unknown_classified_key_fails_the_classify_stage(scene):
    # A classifier key with no serving entry anywhere is a stage failure —
    # never an off-menu serve, never a crash.
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene) | {"classify": _classify_stub("not_a_key")})
    assert out["verdict"] == "cannot_verify"
    assert out["failures"][0]["stage"] == "classify"
    assert out["portion"] is None
