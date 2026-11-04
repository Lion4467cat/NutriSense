import numpy as np
import pytest

from models import dish_segmenter


def _l_mask(size=100):
    mask = np.zeros((size, size), dtype=bool)
    mask[15:28, 15:78] = True
    mask[15:78, 15:28] = True
    return mask


def _disk_mask(size=100):
    yy, xx = np.ogrid[:size, :size]
    return (xx - size // 2) ** 2 + (yy - size // 2) ** 2 <= 24 ** 2


def test_multi_item_selection_rejects_irregular_only_proposals():
    irregular = _l_mask()
    candidates = [(irregular, irregular.astype(np.float32), 0.99)]

    assert dish_segmenter._select(candidates) == 0
    assert dish_segmenter._select(candidates, require_solid=True) is None


def test_multi_item_selection_keeps_solid_candidate_over_higher_score():
    irregular = _l_mask()
    solid = _disk_mask()
    candidates = [
        (irregular, irregular.astype(np.float32), 0.99),
        (solid, solid.astype(np.float32), 0.75),
    ]

    assert dish_segmenter._select(candidates, require_solid=True) == 1


def test_segment_items_does_not_promote_irregular_masks_to_vessels(monkeypatch):
    irregular = _l_mask()
    candidates = [(irregular, irregular.astype(np.float32), 0.99)]
    monkeypatch.setattr(dish_segmenter, "_load", lambda: None)
    monkeypatch.setattr(dish_segmenter, "_query_batch",
                        lambda crops: [candidates for _ in crops])
    image = np.zeros((100, 100, 3), dtype=np.uint8)

    with pytest.raises(RuntimeError, match="no usable food mask"):
        dish_segmenter.segment_items(image)




def test_segment_items_detects_more_than_nine_regions_without_truncation(monkeypatch):
    monkeypatch.setattr(dish_segmenter, "_load", lambda: None)
    calls = []

    def query(rgb, point, box=None):
        yy, xx = np.ogrid[:100, :100]
        mask = (xx - 50) ** 2 + (yy - 50) ** 2 <= 12 ** 2
        return [(mask, mask.astype(np.float32), 0.9)]

    def query_batch(crops):
        calls.extend((crop.shape[:2], (crop.shape[1] / 2, crop.shape[0] / 2),
                      [crop.shape[1] * 0.08, crop.shape[0] * 0.08,
                       crop.shape[1] * 0.92, crop.shape[0] * 0.92])
                     for crop in crops)
        return [query(crop, (crop.shape[1] / 2, crop.shape[0] / 2))
                for crop in crops]

    monkeypatch.setattr(dish_segmenter, "_query_batch", query_batch)
    image = np.zeros((500, 500, 3), dtype=np.uint8)

    out = dish_segmenter.segment_items(image)

    assert len(out["items"]) == 25
    assert out["candidate_count"] == 25
    assert out["truncated_count"] == 0
    assert len(calls) == 25
    assert all(point == (crop_w / 2.0, crop_h / 2.0)
               for (crop_h, crop_w), point, _box in calls)
    actual_centres = {
        (round((item["bbox"][0] + item["bbox"][2] - 1) / 2),
         round((item["bbox"][1] + item["bbox"][3] - 1) / 2))
        for item in out["items"]
    }
    expected_centres = {
        (round((dish_segmenter._crop_bounds(500, gx)[0]
                + dish_segmenter._crop_bounds(500, gx)[1] - 1) / 2),
         round((dish_segmenter._crop_bounds(500, gy)[0]
                + dish_segmenter._crop_bounds(500, gy)[1] - 1) / 2))
        for gy in dish_segmenter.ITEM_GRID
        for gx in dish_segmenter.ITEM_GRID
    }
    assert len(actual_centres) == 25
    assert all(any(abs(ax - ex) <= 6 and abs(ay - ey) <= 6
                   for ax, ay in actual_centres)
               for ex, ey in expected_centres)
