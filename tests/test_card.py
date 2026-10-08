import numpy as np
import cv2

from tools.make_reference_card import build_card, card_layout, mm2px, MARKER_ID, DICT_NAME
from models.scale_anchor import _aruco_detect


def test_layout_geometry_300dpi():
    L = card_layout(300)
    assert L["size"] == (mm2px(105, 300), mm2px(148, 300))  # 1240 x 1748
    x0, y0, x1, y1 = L["square"]
    assert x1 - x0 == mm2px(100, 300) == 1181
    assert y1 - y0 == 1181
    mx0, my0, mx1, my1 = L["marker"]
    assert mx1 - mx0 == mm2px(60, 300) == 709
    # marker centred inside square
    assert (mx0 + mx1) // 2 == (x0 + x1) // 2
    assert (my0 + my1) // 2 == (y0 + y1) // 2


def test_build_card_size_and_marker_detection():
    img = build_card(300)
    L = card_layout(300)
    assert img.shape == (L["size"][1], L["size"][0])
    assert img.dtype == np.uint8

    found = _aruco_detect(img, MARKER_ID, DICT_NAME)
    assert len(found) == 1
    corners = found[0]
    sides = np.linalg.norm(np.roll(corners, -1, axis=0) - corners, axis=1)
    assert abs(sides.mean() - 709) < 4


def test_build_card_150dpi():
    img = build_card(150)
    L = card_layout(150)
    assert img.shape == (L["size"][1], L["size"][0])
    assert L["size"] == (620, 874)


def test_marker_is_black_on_white():
    L = card_layout(300)
    img = build_card(300)
    # white gap just outside marker (2 px band inside white square, outside marker)
    mx0, my0, mx1, my1 = L["marker"]
    band = img[my0 + 4:my1 - 4, mx0 - 6:mx0 - 3]
    assert band.mean() > 200
    # marker border is black
    border = img[my0 + 2:my0 + 6, mx0 + 10:mx1 - 10]
    assert border.mean() < 40
