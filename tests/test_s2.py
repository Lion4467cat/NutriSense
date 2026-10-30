from pathlib import Path

import cv2
import numpy as np
import pytest

from models.food_classifier import (MODEL_ID, build_gallery, classify_dish,
                                    menu_dish_keys, serving_dish_keys)
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


def _n_uncovered():
    # gold-only gallery: every serving key without a gold entry is uncovered
    return len(set(serving_dish_keys()) - {"rice_sambar", "vegetable_rice"})


@pytest.mark.gpu
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
        res = classify_dish(cv2.imread(path), gallery=gal,
                            threshold=0.80)
        assert res["method"] == "gallery"
        assert res["dish"] == want, (path, res["dish"], res["scores"])
        assert res["match_score"] is not None and res["match_score"] >= 0.80
        assert res["margin"] is not None and res["margin"] > 0
        assert 0.0 <= res["confidence"] <= 1.0
        assert len(res["uncovered"]) == _n_uncovered()
        assert "bisibelebath" in res["uncovered"]


@pytest.mark.gpu
def test_deployed_gallery_covers_the_41_wed_classes():
    """data/gallery.npz (ledger 003): every WED class name appears as a
    gallery label — 46 golds kept + WED train ROI crops per class."""
    from models.food_classifier import load_gallery, MODEL_ID
    from config import load_wed_index
    gal = load_gallery()
    labels = set(gal["labels"].tolist())
    assert set(load_wed_index()) <= labels
    assert {"rice_sambar", "vegetable_rice"} <= labels
    assert str(gal["model"]) == MODEL_ID


@pytest.mark.gpu
def test_synthetic_render_abstains():
    s = render_scene()
    res = classify_dish(s["image_bgr"])          # uses data/gallery.npz
    from models.food_classifier import gallery_match_threshold
    thr = gallery_match_threshold()
    assert res["method"] == "gallery"
    assert res["dish"] is None, res
    assert res["match_score"] < thr
    assert "match" in res["reason"]


@pytest.mark.gpu
def test_text_fallback_when_gallery_empty():
    s = render_scene()
    empty = {"emb": np.zeros((0, 4), np.float32),
             "labels": np.array([], dtype=str),
             "sources": np.array([], dtype=str),
             "model": MODEL_ID}
    res = classify_dish(s["image_bgr"], gallery=empty)
    assert res["method"] == "text"
    assert res["dish"] in serving_dish_keys()      # menu keys + off-menu keys
    assert 0.0 <= res["confidence"] <= 1.0
    assert set(res["scores"]) == set(serving_dish_keys())
