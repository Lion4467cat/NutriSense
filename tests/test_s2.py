from pathlib import Path

import cv2
import numpy as np
import pytest

from models.food_classifier import (MODEL_ID, build_gallery, classify_dish,
                                    menu_dish_keys)
from models.dish_segmenter import segment_food
from tests.synth.scene import render_scene

DATASET = Path(__file__).resolve().parent.parent.parent / "DATASET"
CLS_DIRS = ["pepper_rasam_rice", "tomato_rasam_rice", "vegetable_rice"]


def _files():
    return {c: sorted(str(p) for p in (DATASET / c).glob("*.jpg"))
            for c in CLS_DIRS}


def _label(c):
    from models.food_classifier import menu_aliases
    for k in menu_dish_keys():
        if c == k or c in menu_aliases(k):
            return k
    raise AssertionError(f"no dish for {c}")


def test_menu_dish_keys_exclude_out_of_scope():
    keys = menu_dish_keys()
    assert "wheat_product" not in keys
    assert set(keys) <= {"rice_sambar", "vegetable_rice", "bisibelebath"}


def test_segmenter_iou_on_synthetic():
    s = render_scene()
    gt = s["mask_food"]
    out = segment_food(s["image_bgr"])
    m = out["mask"]
    assert m.shape == gt.shape and m.dtype == bool
    assert m.any()
    iou = float((m & gt).sum()) / float((m | gt).sum())
    assert iou >= 0.75, f"food mask IoU {iou:.3f}"
    assert out["strategy"] == "centre_point"
    assert 0.01 < out["area_frac"] < 0.5


def test_gallery_held_out_photos():
    fl = _files()
    entries, held = [], []
    for c, fs in fl.items():
        assert len(fs) >= 8, f"{c}: need >=8 photos"
        entries += [(f, _label(c)) for f in fs[:-1]]
        held.append((fs[-1], _label(c)))
    gal = build_gallery(entries)
    assert set(gal["labels"]) == {"rice_sambar", "vegetable_rice"}
    for path, want in held:
        res = classify_dish(cv2.imread(path), gallery=gal, threshold=0.82)
        assert res["method"] == "gallery"
        assert res["dish"] == want, (path, res["dish"], res["scores"])
        assert res["match_score"] is not None and res["match_score"] >= 0.82
        assert res["margin"] is not None and res["margin"] > 0
        assert 0.0 <= res["confidence"] <= 1.0
        assert res["uncovered"] == ["bisibelebath"]


def test_synthetic_render_abstains():
    s = render_scene()
    res = classify_dish(s["image_bgr"])          # uses data/gallery.npz
    assert res["method"] == "gallery"
    assert res["dish"] is None, res
    assert res["match_score"] < 0.82
    assert "match" in res["reason"]


def test_text_fallback_when_gallery_empty():
    s = render_scene()
    empty = {"emb": np.zeros((0, 4), np.float32),
             "labels": np.array([], dtype=str),
             "sources": np.array([], dtype=str),
             "model": MODEL_ID}
    res = classify_dish(s["image_bgr"], gallery=empty)
    assert res["method"] == "text"
    assert res["dish"] in menu_dish_keys()
    assert 0.0 <= res["confidence"] <= 1.0
    assert set(res["scores"]) == set(menu_dish_keys())
