"""07e: general-mode ingredient-compositional serving (ledger 013).

Covers the three pre-registered criteria:
  1. with a head present and a viable recipe match, an off-menu dish takes
     the ingredient route (path_used "ingredient_head", composition_inferred
     flag, INDB nutrients in assumed_nutrients);
  2. an unmatched profile falls back to the existing off-menu path
     byte-for-byte (learned_head, no composition flags);
  3. a School-menu dish with the head present never takes the route.
Plus unit tests for match_recipe / recipe_profile / IngredientHead gating.
"""
import numpy as np
import pytest

import models.recipe_table as recipe_table
from engine.general_mode import (match_recipe, recipe_profile,
                                 serve_with_head)
from engine.pipeline import analyze as pipe_analyze
from tests.conftest import OK_EXIF
from tests.synth.scene import render_scene


# --- fixture: tiny INDB table (monkeypatched; the 11 MB real table stays
# out of the hermetic tests) -------------------------------------------------
RECIPE = {
    "name": "Test dal rice",
    "per_100g": {"energy_kcal": 120.0, "protein_g": 6.0},
    "ingredients": [
        {"name": "white rice", "amount_g": 100.0, "visible": True},
        {"name": "salt", "amount_g": 10.0, "visible": False},
    ],
    "mass_audit_g": {"resolved_total": 110.0, "invisible_resolved": 10.0,
                     "visible_resolved": 100.0, "resolved_rows": 2,
                     "total_rows": 2},
}

MINI_RECIPES = {"meta": {"recipes": 1}, "recipes": {"R001": RECIPE}}


@pytest.fixture()
def mini_tables(monkeypatch):
    monkeypatch.setattr(recipe_table, "_CACHE",
                        {"recipes": dict(MINI_RECIPES)})


class _FakeIngredientHead:
    """Duck-typed head: predict(image_bgr) -> named grams profile."""

    def __init__(self, profile, meta=None):
        self.profile = dict(profile)
        self.meta = meta or {}
        self.calls = []

    def predict(self, image_bgr):
        self.calls.append(image_bgr.shape)
        return self.profile


def _no_card_scene():
    scene = render_scene()
    # strip the card so the anchor is prior tier (the ingredient route's home)
    return scene


def _make_deps(scene, classify=None):
    import cv2

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

    mask = scene["mask_food"]
    ys, xs = np.nonzero(mask)
    one_item = {
        "mask": mask,
        "sam_score": 0.9,
        "area_frac": float(mask.mean()),
        "bbox": [int(xs.min()), int(ys.min()),
                 int(xs.max()) + 1, int(ys.max()) + 1],
    }

    return {"segment": seg, "depth": dep,
            "segment_items": lambda img: {
                "items": [one_item], "strategy": "stub",
                "truncated_count": 0,
            },
            "classify": classify or (lambda img: {
                "dish": "rajma", "confidence": 0.8, "method": "stub",
                "match_score": 0.91, "reason": "stub"})}


# --- unit: profile / matching ----------------------------------------------

def test_recipe_profile_sums_and_normalises():
    assert recipe_profile(RECIPE) == {"white rice": 100.0, "salt": 10.0}


def test_match_recipe_prefers_shared_mass(mini_tables):
    code, cos = match_recipe({"white rice": 90.0, "banana": 5.0})
    assert code == "R001"
    assert cos > 0.5


def test_match_recipe_none_when_no_shared_slot(mini_tables):
    code, cos = match_recipe({"unobtainium": 100.0})
    assert code is None and cos == 0.0


# --- unit: serve_with_head arithmetic ----------------------------------------

def test_serve_with_head_composition_and_uncertainty(mini_tables):
    head = _FakeIngredientHead({"white rice": 90.0, "banana": 5.0})
    out = serve_with_head(np.zeros((10, 10, 3), np.uint8), head,
                          {"components": {}}, {"id": "rajma"})
    assert out is not None
    portion = out["portion"]
    # visible 90 -> invisible inflation 1.10 -> 99; unknown banana mass is
    # excluded rather than assigned the recipe's nutrient profile.
    assert portion["grams"] == pytest.approx(99.0)
    assert out["unexplained_g"] == pytest.approx(5.0)
    assert portion["components_g"]["white rice"] == pytest.approx(99.0, abs=0.1)
    assert portion["base_method"] == "ingredient_compositional"
    assert "composition_inferred" in portion["flags"]
    assert "unknown_state_widening" in portion["flags"]
    assert portion["sigma_grams_rel"] == pytest.approx(0.45)
    assert portion["recipe_match"]["code"] == "R001"
    assert portion["recipe_match"]["confident"] is False
    # recipe per-100 g nutrients ride the synthetic generic id
    assert out["nutrition"]["assumed_nutrients"] == ["indb_R001"]
    assert out["nutrition"]["kcal"]["mean"] == pytest.approx(99 * 1.2, rel=0.05)


def test_serve_with_head_widens_band_when_coverage_weak(mini_tables):
    # same recipe but the prediction covers a sliver of it and drags in an
    # unexplained ingredient of similar size -> NOT confident
    head = _FakeIngredientHead({"white rice": 45.0, "banana": 20.0})
    out = serve_with_head(np.zeros((10, 10, 3), np.uint8), head,
                          {"components": {}}, {"id": "rajma"})
    assert out is not None
    assert out["confident"] is False
    p = out["portion"]
    assert "unknown_state_widening" in p["flags"]
    assert p["sigma_grams_rel"] == pytest.approx(0.45)


def test_serve_with_head_unmatched_returns_none(mini_tables):
    head = _FakeIngredientHead({"unobtainium": 100.0})
    out = serve_with_head(np.zeros((10, 10, 3), np.uint8), head,
                          {"components": {}}, {"id": "rajma"})
    assert out is None


# --- pipeline seams ----------------------------------------------------------

def test_pipeline_ingredient_route_fires():
    scene = render_scene({"anchor": {"card": False}})
    head = _FakeIngredientHead({"white rice": 90.0, "banana": 5.0})
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(recipe_table, "_CACHE", {"recipes": dict(MINI_RECIPES)})
        out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                           deps=_make_deps(scene) | {"ingredient_head": head},
                           exif=OK_EXIF, mode="general")
    assert out["verdict"] == "cannot_verify"
    assert out["reasons"][0]["kind"] == "off_menu_dish"
    assert out["path_used"] == "ingredient_head"
    p = out["portion"]
    assert p["grams_source"] == "ingredient_head"
    assert "composition_inferred" in p["flags"]
    assert "recipe_match" in p
    assert out["nutrition"]["assumed_nutrients"] == ["indb_R001"]
    assert out["segmentation"]["n_items"] == 1
    assert head.calls, "the route must have consulted the head"
    assert out["compliance"] is None


def test_off_menu_multi_item_detection_aggregates_without_school_verdict():
    scene = render_scene({"anchor": {"card": False}})
    mask = scene["mask_food"]
    _, xs = np.nonzero(mask)
    midpoint = int(np.median(xs))

    def make_item(item_mask):
        ys, xs = np.nonzero(item_mask)
        return {
            "mask": item_mask,
            "sam_score": 0.9,
            "area_frac": float(item_mask.mean()),
            "bbox": [int(xs.min()), int(ys.min()),
                     int(xs.max()) + 1, int(ys.max()) + 1],
        }

    left, right = mask.copy(), mask.copy()
    left[:, midpoint:] = False
    right[:, :midpoint] = False

    class _WedHead:
        meta = {"recipe": "fake-test-head", "test_mae_g": 14.51}

        def predict(self, image_bgr, mask, slot_ids, device=None):
            grams = 200.0
            return {"grams": grams,
                    "slots": {slot: grams / len(slot_ids)
                              for slot in slot_ids}}

    def classify(img):
        return {"dish": "rajma", "confidence": 0.8, "method": "stub",
                "match_score": 0.91, "reason": "stub"}

    detector = lambda img: {
        "items": [make_item(left), make_item(right)],
        "strategy": "stub", "truncated_count": 0,
    }
    out = pipe_analyze(
        scene["image_bgr"], day="mon", band="1-5",
        deps=_make_deps(scene, classify=classify)
        | {"segment_items": detector, "weight_head": _WedHead()},
        exif=OK_EXIF, mode="general",
    )

    assert out["path_used"] == "multi_item"
    assert out["segmentation"]["n_items"] == 2
    assert len(out["items"]) == 2
    assert out["portion"]["grams"] == pytest.approx(400.0)
    assert out["verdict"] == "cannot_verify"
    assert out["compliance"] is None
    assert out["reasons"][0]["kind"] == "off_menu_dish"


def test_pipeline_unmatched_profile_falls_back():
    scene = render_scene({"anchor": {"card": False}})
    ing = _FakeIngredientHead({"unobtainium": 100.0})

    class _WedHead:
        meta = {"recipe": "fake-test-head", "test_mae_g": 14.51}

        def predict(self, image_bgr, mask, slot_ids, device=None):
            return {"grams": 220.0, "slots": {s: 220.0 / len(slot_ids)
                                              for s in slot_ids}}

    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=_make_deps(scene)
                       | {"weight_head": _WedHead(), "ingredient_head": ing},
                       exif=OK_EXIF, mode="general")
    # existing off-menu path, byte-for-byte: learned dish-slot head
    assert out["path_used"] == "learned_head"
    assert out["portion"]["base_method"] == "learned_weight"
    assert out["portion"]["grams_source"] == "learned_weight"
    assert all("composition_inferred" not in f
               for f in out["portion"]["flags"])
    assert out["degradations"] == []      # silent fallback, no spam


def test_school_mode_scores_recognized_off_menu_class_against_standards():
    scene = render_scene({"anchor": {"card": False}})

    class _WedHead:
        meta = {"recipe": "fake-test-head", "test_mae_g": 14.51}

        def predict(self, image_bgr, mask, slot_ids, device=None):
            grams = 300.0
            return {"grams": grams,
                    "slots": {slot: grams / len(slot_ids)
                              for slot in slot_ids}}

    out = pipe_analyze(
        scene["image_bgr"], day="mon", band="1-5",
        deps=_make_deps(scene) | {"weight_head": _WedHead()},
        exif=OK_EXIF, mode="school",
    )

    assert out["dish"]["id"] == "rajma"
    assert out["dish"]["on_day"] is False
    assert out["verdict"] in {"PASS", "FAIL", "BORDERLINE"}
    assert out["compliance"]["day"] == "mon"
    assert out["compliance"]["band"] == "1-5"
    assert "dal_curry" in out["nutrition"]["assumed_nutrients"]
    assert not any(reason["kind"] == "off_menu_dish"
                   for reason in out["reasons"])


def test_general_mode_menu_dish_keeps_goal_tracking_without_school_verdict():
    scene = render_scene({"anchor": {"card": False}})

    class _WedHead:
        meta = {"recipe": "fake-test-head", "test_mae_g": 14.51}

        def predict(self, image_bgr, mask, slot_ids, device=None):
            grams = 310.0
            return {"grams": grams,
                    "slots": {slot: grams / len(slot_ids)
                              for slot in slot_ids}}

    def classify(img):
        return {"dish": "rice_sambar", "confidence": 1.0, "method": "stub",
                "match_score": 0.9, "reason": "stub"}

    out = pipe_analyze(
        scene["image_bgr"], day="mon", band="1-5",
        deps=_make_deps(scene, classify=classify)
        | {"weight_head": _WedHead()},
        exif=OK_EXIF, mode="general",
    )

    assert out["portion"] is not None and out["nutrition"] is not None
    assert out["verdict"] == "cannot_verify"
    assert out["compliance"] is None
    assert not any(reason["kind"] == "off_menu_dish"
                   for reason in out["reasons"])


def test_pipeline_school_dish_never_takes_ingredient_route():
    scene = render_scene({"anchor": {"card": False}})
    ing = _FakeIngredientHead({"white rice": 90.0})

    class _WedHead:
        meta = {"recipe": "fake-test-head", "test_mae_g": 14.51}

        def predict(self, image_bgr, mask, slot_ids, device=None):
            return {"grams": 310.0, "slots": {s: 310.0 / len(slot_ids)
                                              for s in slot_ids}}

    def cls(img):   # rice_sambar IS a menu dish
        return {"dish": "rice_sambar", "confidence": 1.0, "method": "stub",
                "match_score": 0.9, "reason": "stub"}

    out = pipe_analyze(scene["image_bgr"], day="mon", band="1-5",
                       deps=_make_deps(scene, classify=cls)
                       | {"weight_head": _WedHead(), "ingredient_head": ing}, exif=OK_EXIF)
    assert ing.calls == []                       # route never consulted
    assert out["path_used"] == "learned_head"
    assert out["verdict"] in {"PASS", "BORDERLINE", "FAIL"}
