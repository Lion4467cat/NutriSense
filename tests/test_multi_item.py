"""Spec 003 seam tests: multi-item portion path.

Seams:
  1. two vessels -> per-item classify + portion, aggregate meal verdict
  2. per-item learned head on the prior tier (one predict() call per item)
  3. single-vessel / detector-unavailable frames keep the single-serving
     flow, with items[] as a one-element mirror of the top-level blocks
  4. detection failure degrades (tagged), never fails the analysis
  5. partially unrecognized plates: skipped items reported, not guessed
  6. every item unrecognized -> byte-level fall-through to the single flow
"""
import cv2
import numpy as np
import pytest

from engine.pipeline import analyze as pipe_analyze
from tests.synth.scene import render_scene


@pytest.fixture(scope="module")
def scene():
    return render_scene()


@pytest.fixture(scope="module")
def no_card_scene():
    return render_scene({"anchor": {"card": False}})


def _half_masks(scene):
    """Two disjoint vessel masks: left/right halves of the food mask."""
    m = scene["mask_food"]
    ys, xs = np.nonzero(m)
    x_mid = int(np.median(xs))
    left = np.zeros_like(m)
    right = np.zeros_like(m)
    left[:, :x_mid] = m[:, :x_mid]
    right[:, x_mid:] = m[:, x_mid:]

    def item(mask):
        ys, xs = np.nonzero(mask)
        return {"mask": mask, "sam_score": 0.9,
                "area_frac": float(mask.mean()),
                "bbox": [int(xs.min()), int(ys.min()),
                         int(xs.max()) + 1, int(ys.max()) + 1]}

    return {"items": [item(left), item(right)], "strategy": "grid9_box"}


def make_deps(scene, **extra):
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

    return {"segment": seg, "depth": dep, "classify": cls} | extra


class _FakeHead:
    """WeightHead stand-in: deterministic grams per call."""

    meta = {"recipe": "fake-test-head", "test_mae_g": 14.51}

    def __init__(self, grams=310.0):
        self.grams = grams
        self.calls = []

    def predict(self, image_bgr, mask, slot_ids, device=None):
        self.calls.append(list(slot_ids))
        n = len(slot_ids)
        per = {s: round(self.grams / n, 2) for s in slot_ids}
        return {"grams": self.grams, "slots": per, "slots_clamped": False}


# --- seam 1: two vessels, measured tier, geometry per item -----------------

def test_two_items_aggregate_meal(scene):
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene,
                                      segment_items=lambda img: _half_masks(scene)))
    assert out["path_used"] == "multi_item"
    assert out["segmentation"]["n_items"] == 2
    assert len(out["items"]) == 2
    for item in out["items"]:
        assert item["dish"]["id"] == "rice_sambar"
        assert item["portion"] is not None
        assert item["bbox"] is not None
    item_grams = sum(i["portion"]["grams"] for i in out["items"])
    assert out["portion"]["grams"] == pytest.approx(item_grams, abs=0.2)
    assert out["dish"]["id"] == "meal"
    assert " + " in out["dish"]["display_name"]
    assert all(":" in k for k in out["portion"]["components_g"])
    assert "multi_item_meal" in out["portion"]["flags"]
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}
    assert out["compliance"]["probs"]
    assert any("multi_item_meal" in a for a in out["assumptions"])
    # the aggregate nutrition is the sum of the per-item MCs
    assert out["nutrition"]["diagnostics"]["multi_item_count"] == 2


# --- seam 2: prior tier, learned head per item ------------------------------

def test_learned_head_per_item(no_card_scene):
    head = _FakeHead(310.0)
    out = pipe_analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(no_card_scene,
                                      weight_head=head,
                                      segment_items=lambda img: _half_masks(no_card_scene)))
    assert out["path_used"] == "multi_item"
    # rice_sambar maps to [steamed-rice, sambar] slots; one call per item
    assert head.calls == [[33, 32], [33, 32]]
    assert out["portion"]["grams"] == pytest.approx(620.0, abs=0.2)
    assert out["portion"]["grams_source"] == "learned_weight"
    assert all(i["portion"]["base_method"] == "learned_weight"
               for i in out["items"])
    assert out["anchor"]["tier"] == "prior"
    assert any(r["kind"] == "no_reference_card" for r in out["reasons"])
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}


# --- seam 3: single-serving frames ------------------------------------------

def test_single_flow_items_mirror(scene):
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    assert out["path_used"] != "multi_item"
    assert len(out["items"]) == 1
    mirror = out["items"][0]
    assert mirror["portion"]["grams"] == out["portion"]["grams"]
    assert mirror["dish"]["id"] == out["dish"]["id"]
    assert mirror["bbox"] is None


def test_single_vessel_detection_keeps_single_flow(scene):
    one = {"items": [_half_masks(scene)["items"][0]], "strategy": "grid9_box"}
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene,
                                      segment_items=lambda img: one))
    assert out["path_used"] != "multi_item"
    assert len(out["items"]) == 1
    assert out["items"][0]["bbox"] is None  # mirror, not a detected item


# --- seam 4: detection failure degrades --------------------------------------

def test_detection_failure_degrades(scene):
    def boom(img):
        raise RuntimeError("grid9 exploded")

    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, segment_items=boom))
    assert "multi_item_detection_failed" in out["degradations"]
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}
    assert len(out["items"]) == 1


# --- seam 5: partially unrecognized plate ------------------------------------

def test_unrecognized_item_skipped_not_guessed(scene):
    calls = {"n": 0}

    def cls(img):
        calls["n"] += 1
        if calls["n"] == 2:  # first item crop abstains
            return {"dish": None, "confidence": 0.2, "method": "gallery",
                    "match_score": 0.3, "reason": "below threshold"}
        return {"dish": "rice_sambar", "confidence": 1.0, "method": "stub",
                "match_score": 0.9, "reason": "stub"}

    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, classify=cls,
                                      segment_items=lambda img: _half_masks(scene)))
    assert out["path_used"] == "multi_item"
    assert len(out["items"]) == 2
    skipped = [i for i in out["items"] if i["portion"] is None]
    measured = [i for i in out["items"] if i["portion"] is not None]
    assert len(skipped) == 1 and len(measured) == 1
    assert skipped[0]["dish"] is None
    assert skipped[0]["reason"]["kind"] == "unrecognized"
    assert out["portion"]["grams"] == pytest.approx(
        measured[0]["portion"]["grams"], abs=0.2)
    assert any("excluded from the aggregate" in a for a in out["assumptions"])


# --- seam 6: every item unrecognized -> single flow --------------------------

def test_all_items_unrecognized_falls_back(scene):
    calls = {"n": 0}

    def cls(img):
        calls["n"] += 1
        if calls["n"] == 1:  # primary full-frame classification
            return {"dish": "rice_sambar", "confidence": 1.0,
                    "method": "stub", "match_score": 0.9, "reason": "stub"}
        return {"dish": None, "confidence": 0.2, "method": "gallery",
                "match_score": 0.3, "reason": "below threshold"}

    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, classify=cls,
                                      segment_items=lambda img: _half_masks(scene)))
    assert out["path_used"] != "multi_item"
    assert "multi_item_fallback" in out["degradations"]
    assert len(out["items"]) == 1
    assert out["items"][0]["bbox"] is None


# --- spec 004: combo decomposition -----------------------------------------

def _combo_classify(crop_scores):
    """Classify stub: primary full-frame -> rice_sambar; per-crop scores from
    the crop_scores list (one entry per item call)."""
    calls = {"n": 0}

    def cls(img):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"dish": "rice_sambar", "confidence": 1.0,
                    "method": "gallery", "match_score": 0.95,
                    "reason": "stub",
                    "scores": {"rice_sambar": 0.95, "steamed-rice": 0.5,
                               "sambar": 0.5}}
        scores = crop_scores[min(calls["n"] - 2, len(crop_scores) - 1)]
        best = max(scores, key=scores.get)
        return {"dish": best, "confidence": 1.0, "method": "gallery",
                "match_score": scores[best], "reason": "stub",
                "scores": dict(scores)}

    return cls


def test_combo_decomposition_per_item(scene):
    cls = _combo_classify([
        {"rice_sambar": 0.95, "steamed-rice": 0.91, "sambar": 0.55},
        {"rice_sambar": 0.95, "steamed-rice": 0.55, "sambar": 0.92},
    ])
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, classify=cls,
                                      segment_items=lambda img: _half_masks(scene)))
    assert out["path_used"] == "multi_item"
    ids = [i["dish"]["id"] for i in out["items"]]
    assert ids == ["steamed-rice", "sambar"]  # decomposed, not 2x combo
    keys = set(out["portion"]["components_g"])
    assert any(k.startswith("steamed-rice:") for k in keys)
    assert any(k.startswith("sambar:") for k in keys)
    assert any("combo_decomposition" in a for a in out["assumptions"])
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}


def test_combo_below_threshold_keeps_unrestricted(scene):
    # component scores below gallery_match_threshold (0.8) -> the item keeps
    # its unrestricted classification (spec 004 fallback)
    cls = _combo_classify([
        {"rice_sambar": 0.95, "steamed-rice": 0.6, "sambar": 0.55},
        {"rice_sambar": 0.95, "steamed-rice": 0.55, "sambar": 0.6},
    ])
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, classify=cls,
                                      segment_items=lambda img: _half_masks(scene)))
    assert out["path_used"] == "multi_item"
    assert [i["dish"]["id"] for i in out["items"]] == ["rice_sambar",
                                                       "rice_sambar"]


# --- spec 005: capture-angle lint -------------------------------------------

def test_capture_angle_in_band_no_note(scene):
    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    assert out["anchor"]["tier"] == "measured"
    assert not any("capture angle" in n for n in out["lint"]["notes"])


def test_capture_angle_out_of_band_notes(scene):
    # near-top-down camera (~14° from face-on) -> below the 25° band floor
    steep = render_scene({"camera": {"pos": (0.0, -100.0, 400.0)}})
    out = pipe_analyze(steep["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(steep))
    assert any("capture angle" in n for n in out["lint"]["notes"])
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}  # non-blocking
