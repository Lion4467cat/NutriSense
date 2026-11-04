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

import engine.pipeline as pipeline
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

    return {"items": [item(left), item(right)],
            "strategy": "synthetic_grid9_box"}


def _fuzzy_half_masks(scene, frac_target=0.02):
    """Two vessel masks sharing configurable boundary fuzz.

    The smaller (left) mask keeps `frac_target` of its pixels inside the
    larger (right) mask, like adjacent plate-and-bowl segmentation proposals.
    """
    pair = _half_masks(scene)
    left, right = pair["items"][0]["mask"], pair["items"][1]["mask"]
    ys, xs = np.nonzero(left)
    take = max(1, int(len(ys) * frac_target))
    x_mid = int(np.nonzero(right)[1].min())
    sl = np.argsort(x_mid - xs)[:take]
    shared = np.zeros_like(left)
    shared[ys[sl], xs[sl]] = True
    right = right | shared
    ys_r, xs_r = np.nonzero(right)
    pair["items"][1] = {
        **pair["items"][1],
        "mask": right,
        "area_frac": float(right.mean()),
        "bbox": [int(xs_r.min()), int(ys_r.min()),
                 int(xs_r.max()) + 1, int(ys_r.max()) + 1],
    }
    return {"items": [pair["items"][0], pair["items"][1]],
            "strategy": "synthetic_grid9_box"}, shared


def test_boundary_fuzz_scores_and_no_double_count(scene):
    pair, shared = _fuzzy_half_masks(scene)
    assert shared.sum() > 0
    world = pair["items"][0]["mask"] | pair["items"][1]["mask"]
    frac = shared.sum() / min(pair["items"][0]["mask"].sum(),
                              pair["items"][1]["mask"].sum())
    assert 0 < frac < 0.05
    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                   deps=make_deps(
                       scene,
                       classify=_combo_classify([
                           {"rice_sambar": 0.95, "steamed-rice": 0.91,
                            "sambar": 0.55},
                           {"rice_sambar": 0.95, "steamed-rice": 0.55,
                            "sambar": 0.92},
                       ]),
                       segment_items=lambda img: pair))
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}
    assert out["path_used"] == "multi_item"
    assert out["segmentation"]["n_items"] == 2
    item_grams = sum(i["portion"]["grams"] for i in out["items"])
    assert out["portion"]["grams"] == pytest.approx(item_grams, abs=0.2)
    # Every shared pixel is assigned to one vessel before portioning.
    from engine.pipeline import _assign_boundary_overlap
    assigned = _assign_boundary_overlap(pair["items"])
    assert world.sum() == pytest.approx(
        sum(int(i["mask"].sum()) for i in assigned), abs=1)


def test_large_overlap_is_partitioned_and_scored_without_double_count(scene):
    pair, _ = _fuzzy_half_masks(scene, frac_target=0.20)
    union = pair["items"][0]["mask"] | pair["items"][1]["mask"]
    shared = pair["items"][0]["mask"] & pair["items"][1]["mask"]
    assert shared.sum() / min(pair["items"][0]["mask"].sum(),
                              pair["items"][1]["mask"].sum()) >= 0.05
    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                   deps=make_deps(
                       scene,
                       classify=_combo_classify([
                           {"rice_sambar": 0.95, "steamed-rice": 0.91,
                            "sambar": 0.55},
                           {"rice_sambar": 0.95, "steamed-rice": 0.55,
                            "sambar": 0.92},
                       ]),
                       segment_items=lambda img: pair))
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}
    assert out["path_used"] == "multi_item"
    assert out["portion"] is not None
    assert out["segmentation"]["overlap_resolution"] == "nearest-exclusive-region"
    assert out["segmentation"]["item_detection_strategy"] == (
        "synthetic_grid9_box")
    assert any("shared pixels were assigned once" in note
               for note in out["assumptions"])
    item_grams = sum(i["portion"]["grams"] for i in out["items"])
    assert out["portion"]["grams"] == pytest.approx(item_grams, abs=0.2)
    from engine.pipeline import _assign_boundary_overlap
    assigned = _assign_boundary_overlap(pair["items"])
    assert not np.logical_and(assigned[0]["mask"], assigned[1]["mask"]).any()
    assert np.logical_or(assigned[0]["mask"], assigned[1]["mask"]).sum() == union.sum()
    for item in assigned:
        mask = item["mask"]
        ys, xs = np.nonzero(mask)
        assert item["area_frac"] == pytest.approx(float(mask.mean()))
        assert item["bbox"] == [int(xs.min()), int(ys.min()),
                                int(xs.max()) + 1, int(ys.max()) + 1]


def test_below_threshold_full_frame_candidate_is_estimate_only(scene):
    def classify(_img):
        return {
            "dish": None,
            "confidence": 0.42,
            "method": "gallery",
            "match_score": 0.71,
            "scores": {"sambar": 0.71, "steamed-rice": 0.69},
            "reason": "best gallery match below threshold",
        }

    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                   deps=make_deps(scene, classify=classify,
                                  segment_items=lambda _img: {
                                      "items": [_half_masks(scene)["items"][0]],
                                      "strategy": "grid9_box",
                                  }))

    assert out["verdict"] == "ESTIMATED"
    assert out["portion"] is not None
    assert out["nutrition"] is not None
    assert out["compliance"] is None
    assert any(reason["kind"] == "estimate_only"
               for reason in out["reasons"])
    item_grams = sum(i["portion"]["grams"] for i in out["items"])
    assert out["portion"]["grams"] == pytest.approx(item_grams, abs=0.2)


def test_three_way_overlap_preserves_union_and_assigns_each_pixel_once():
    from engine.pipeline import _assign_boundary_overlap

    yy, xx = np.ogrid[:128, :160]
    masks = [((xx - center) ** 2 + (yy - 64) ** 2 <= 30 ** 2)
             for center in (45, 80, 115)]
    union = np.logical_or.reduce(masks)
    items = []
    for score, mask in zip((0.8, 0.9, 0.7), masks):
        ys, xs = np.nonzero(mask)
        items.append({
            "mask": mask,
            "sam_score": score,
            "area_frac": float(mask.mean()),
            "bbox": [int(xs.min()), int(ys.min()),
                     int(xs.max()) + 1, int(ys.max()) + 1],
        })

    assigned = _assign_boundary_overlap(items)
    assert len(assigned) == 3
    assigned_masks = [item["mask"] for item in assigned]
    assert np.logical_or.reduce(assigned_masks).sum() == union.sum()
    assert sum(int(mask.sum()) for mask in assigned_masks) == union.sum()
    assert all(item["area_frac"] == pytest.approx(item["mask"].mean())
               for item in assigned)


def test_duplicate_masks_resolve_to_one_highest_score_region():
    from engine.pipeline import _assign_boundary_overlap

    yy, xx = np.ogrid[:80, :80]
    mask = (xx - 40) ** 2 + (yy - 40) ** 2 <= 20 ** 2
    items = [
        {"mask": mask, "sam_score": 0.7, "area_frac": float(mask.mean()),
         "bbox": [20, 20, 61, 61]},
        {"mask": mask.copy(), "sam_score": 0.95,
         "area_frac": float(mask.mean()), "bbox": [20, 20, 61, 61]},
    ]

    assigned = _assign_boundary_overlap(items)
    assert len(assigned) == 1
    assert assigned[0]["sam_score"] == 0.95
    assert np.array_equal(assigned[0]["mask"], mask)


def test_same_food_in_distinct_regions_still_gets_meal_estimate(scene):
    pair = _half_masks(scene)
    # A coarse full-meal mask can be smaller than the union of the separately
    # detected item masks. That must not block two individually measured bowls
    # of the same food class.
    pair["items"][0]["mask"][0, 0] = True
    pair["items"][1]["mask"][-1, -1] = True

    def classify(_img):
        return {"dish": "sambar", "confidence": 0.95,
                "method": "stub", "match_score": 0.95, "reason": "stub"}

    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                   deps=make_deps(scene, classify=classify,
                                  segment_items=lambda _img: pair))
    assert out["path_used"] == "multi_item"
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}
    assert out["portion"] is not None
    assert len(out["items"]) == 2
    assert [item["dish"]["id"] for item in out["items"]] == ["sambar", "sambar"]
    assert any("repeated_food_regions" in note for note in out["assumptions"])


def test_automatic_multi_item_coverage_is_estimate_only(scene):
    pair = _half_masks(scene)
    pair["strategy"] = "dense_grid_box"

    def classify(_img):
        return {"dish": "sambar", "confidence": 0.95,
                "method": "stub", "match_score": 0.95, "reason": "stub"}

    out = _analyze(
        scene["image_bgr"], day="mon", band="1-5",
        deps=make_deps(scene, classify=classify,
                       segment_items=lambda _img: pair))

    assert out["path_used"] == "multi_item"
    assert out["verdict"] == "ESTIMATED"
    assert out["compliance"] is None
    assert out["nutrition"] is not None
    assert out["segmentation"]["multi_item_status"] == "coverage-unverified"
    assert any("whole-meal coverage" in reason["text"]
               for reason in out["reasons"])


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


def _analyze(image, **kwargs):
    """Admit these fixtures with explicit, compliant capture metadata."""
    kwargs.setdefault("exif", {"digital_zoom": 1.0})
    return pipe_analyze(image, **kwargs)


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
    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                   deps=make_deps(
                       scene,
                       classify=_combo_classify([
                           {"rice_sambar": 0.95, "steamed-rice": 0.91,
                            "sambar": 0.55},
                           {"rice_sambar": 0.95, "steamed-rice": 0.55,
                            "sambar": 0.92},
                       ]),
                       segment_items=lambda img: _half_masks(scene)))
    assert out["path_used"] == "multi_item"
    assert out["segmentation"]["n_items"] == 2
    assert len(out["items"]) == 2
    assert [item["dish"]["id"] for item in out["items"]] == [
        "steamed-rice", "sambar"]
    for item in out["items"]:
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
    out = _analyze(no_card_scene["image_bgr"], day="mon", band="1-5",
                   deps=make_deps(
                       no_card_scene,
                       classify=_combo_classify([
                           {"rice_sambar": 0.95, "steamed-rice": 0.91,
                            "sambar": 0.55},
                           {"rice_sambar": 0.95, "steamed-rice": 0.55,
                            "sambar": 0.92},
                       ]),
                       weight_head=head,
                       segment_items=lambda img: _half_masks(no_card_scene)))
    assert out["path_used"] == "multi_item"
    # rice_sambar maps to [steamed-rice, sambar] slots; one call per item
    assert head.calls == [[33], [32]]
    assert out["portion"]["grams"] == pytest.approx(620.0, abs=0.2)
    assert out["portion"]["grams_source"] == "learned_weight"
    assert all(i["portion"]["base_method"] == "learned_weight"
               for i in out["items"])
    assert out["anchor"]["tier"] == "prior"
    assert any(r["kind"] == "no_reference_card" for r in out["reasons"])
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}


# --- seam 3: single-serving frames ------------------------------------------

def test_single_flow_items_mirror(scene):
    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    assert out["path_used"] != "multi_item"
    assert len(out["items"]) == 1
    mirror = out["items"][0]
    assert mirror["portion"]["grams"] == out["portion"]["grams"]
    assert mirror["dish"]["id"] == out["dish"]["id"]
    assert mirror["bbox"] is None


def test_single_vessel_detection_keeps_single_flow(scene):
    one = {"items": [_half_masks(scene)["items"][0]], "strategy": "grid9_box"}
    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene,
                                      segment_items=lambda img: one))
    assert out["path_used"] != "multi_item"
    assert len(out["items"]) == 1
    assert out["items"][0]["bbox"] is None  # mirror, not a detected item


# --- seam 4: detection failure degrades --------------------------------------

def test_detection_failure_uses_top_level_mask_for_estimated_meal(scene):
    def boom(img):
        raise RuntimeError("grid9 exploded")

    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, segment_items=boom))
    assert "multi_item_detection_failed" in out["degradations"]
    assert out["verdict"] == "ESTIMATED"
    assert out["portion"] is not None
    assert out["nutrition"] is not None
    assert out["compliance"] is None
    assert len(out["items"]) == 1
    assert (out["segmentation"]["multi_item_status"]
            == "whole-mask-estimate")
    assert "top-level food mask" in out["reasons"][0]["text"]


# --- seam 5: partially unrecognized plate ------------------------------------

def test_unrecognized_item_falls_back_to_whole_mask_estimate(scene):
    calls = {"n": 0}

    def cls(img):
        calls["n"] += 1
        if calls["n"] == 2:  # first item crop abstains
            return {"dish": None, "confidence": 0.2, "method": "gallery",
                    "match_score": 0.3, "reason": "below threshold"}
        return {"dish": "rice_sambar", "confidence": 1.0, "method": "stub",
                "match_score": 0.9, "reason": "stub"}

    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, classify=cls,
                                      segment_items=lambda img: _half_masks(scene)))
    assert out["path_used"] == "multi_item"
    assert out["verdict"] == "ESTIMATED"
    assert out["segmentation"]["item_detection_fallback"] == "top-level-food-mask"
    assert out["portion"] is not None
    assert out["nutrition"] is not None
    assert out["compliance"] is None
    assert len(out["items"]) == 1
    assert any("item-level total is incomplete" in a
               for a in out["assumptions"])


# --- seam 6: every item unrecognized -> abstain from the aggregate ----------

def test_all_items_unrecognized_still_returns_whole_mask_estimate(scene):
    calls = {"n": 0}

    def cls(img):
        calls["n"] += 1
        if calls["n"] == 1:  # primary full-frame classification
            return {"dish": "rice_sambar", "confidence": 1.0,
                    "method": "stub", "match_score": 0.9, "reason": "stub"}
        return {"dish": None, "confidence": 0.2, "method": "gallery",
                "match_score": 0.3, "reason": "below threshold"}

    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, classify=cls,
                                      segment_items=lambda img: _half_masks(scene)))
    assert out["path_used"] == "multi_item"
    assert out["verdict"] == "ESTIMATED"
    assert out["portion"] is not None
    assert out["nutrition"] is not None
    assert out["compliance"] is None
    assert len(out["items"]) == 1
    assert out["segmentation"]["item_detection_fallback"] == "top-level-food-mask"


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
    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
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


def test_combo_below_threshold_produces_estimate_without_compliance(scene):
    # The component candidates may still support a tentative total, but they
    # are not strong enough to justify a school compliance verdict.
    cls = _combo_classify([
        {"rice_sambar": 0.95, "steamed-rice": 0.6, "sambar": 0.55},
        {"rice_sambar": 0.95, "steamed-rice": 0.55, "sambar": 0.6},
    ])
    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene, classify=cls,
                                      segment_items=lambda img: _half_masks(scene)))
    assert out["path_used"] == "multi_item"
    assert out["verdict"] == "ESTIMATED"
    assert out["portion"] is not None
    assert out["nutrition"] is not None
    assert out["compliance"] is None
    assert any("below threshold" in reason["text"]
               for reason in out["reasons"])


def test_combo_component_mismatch_falls_back_to_whole_meal_estimate(scene):
    cls = _combo_classify([
        {"rice_sambar": 0.95, "steamed-rice": 0.91, "sambar": 0.55},
        {"rice_sambar": 0.95, "steamed-rice": 0.92, "sambar": 0.54},
    ])
    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                   deps=make_deps(scene, classify=cls,
                                  segment_items=lambda img: _half_masks(scene)))
    assert out["verdict"] == "ESTIMATED"
    assert out["portion"] is not None
    assert out["nutrition"] is not None
    assert out["compliance"] is None
    assert out["segmentation"]["item_detection_fallback"] == "top-level-food-mask"


# --- spec 005: capture-angle lint -------------------------------------------

def test_capture_angle_in_band_no_note(scene):
    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(scene))
    assert out["anchor"]["tier"] == "measured"
    assert not any("capture angle" in n for n in out["lint"]["notes"])


def test_capture_angle_out_of_band_notes(scene):
    # near-top-down camera (~14° from face-on) -> below the 25° band floor
    steep = render_scene({"camera": {"pos": (0.0, -100.0, 400.0)}})
    out = _analyze(steep["image_bgr"], day="mon", band="1-5",
                       deps=make_deps(steep))
    assert any("capture angle" in n for n in out["lint"]["notes"])
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}  # non-blocking


def test_high_capture_angle_keeps_estimate_but_withholds_school_verdict(
    scene, monkeypatch,
):
    original_estimate_anchor = pipeline.estimate_anchor

    def high_angle_anchor(image, **kwargs):
        anchor = original_estimate_anchor(image, **kwargs)
        if anchor.get("label") == "measured":
            return {**anchor, "tilt_deg": 75.0}
        return anchor

    monkeypatch.setattr(pipeline, "estimate_anchor", high_angle_anchor)
    out = _analyze(scene["image_bgr"], day="mon", band="1-5",
                   deps=make_deps(scene))

    assert out["verdict"] == "ESTIMATED"
    assert out["portion"] is not None
    assert out["nutrition"] is not None
    assert out["compliance"] is None
    assert any("footprint correction is not validated" in reason["text"]
               for reason in out["reasons"])
