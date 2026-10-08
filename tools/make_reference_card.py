#!/usr/bin/env python3
"""Generate the NutriSense A6 reference scale card.

Layout: white A6 card, 100.0 mm black square, white inner gap, 60.0 mm
ArUco DICT_4X4_50 marker (id 7) centred. Print at 100% / no-scaling and
ruler-verify the black square before first use (set ruler_checked in
data/anchor_config.json).

Usage:  .venv/bin/python -m tools.make_reference_card [--dpi 300] [--outdir docs/assets]
"""
import argparse
from pathlib import Path

import cv2
import numpy as np

CARD_MM = (105.0, 148.0)      # A6 portrait
SQUARE_MM = 100.0             # ruler-verified scale square
INNER_WHITE_MM = 78.0         # white quiet zone inside black square (>= 0.9 marker module)
MARKER_MM = 60.0              # ArUco marker outer size (incl. black border)
MARKER_ID = 7
DICT_NAME = "DICT_4X4_50"

TEXT_MAIN = "NutriSense scale card - verify square = 100.0 mm"
TEXT_SUB = f"ArUco 4x4_50 id {MARKER_ID}, marker {MARKER_MM:.1f} mm | v1"
TEXT_FOOT = "ruler check: ______   date: ______"


def mm2px(mm, dpi):
    return int(round(mm / 25.4 * dpi))


def card_layout(dpi=300):
    """Pixel geometry of the card. Rects are (x0, y0, x1, y1), marker centred."""
    w, h = mm2px(CARD_MM[0], dpi), mm2px(CARD_MM[1], dpi)
    sq = mm2px(SQUARE_MM, dpi)
    x0 = (w - sq) // 2
    y0 = int(round(h * 0.10))
    cx, cy = x0 + sq // 2, y0 + sq // 2
    inner = mm2px(INNER_WHITE_MM, dpi)
    m = mm2px(MARKER_MM, dpi)
    return {
        "dpi": dpi,
        "size": (w, h),
        "square": (x0, y0, x0 + sq, y0 + sq),
        "white": (cx - inner // 2, cy - inner // 2, cx + inner // 2, cy + inner // 2),
        "marker": (cx - m // 2, cy - m // 2, cx - m // 2 + m, cy - m // 2 + m),
    }


def marker_rect_corners(marker_rect):
    """Marker rect (x0,y0,x1,y1) -> 4 corners TL,TR,BR,BL as float points."""
    x0, y0, x1, y1 = marker_rect
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float64)


def _generate_marker(marker_id, dict_name, size_px):
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dict_name))
    gen = getattr(cv2.aruco, "generateImageMarker", None) or getattr(cv2.aruco, "generateMarker")
    try:
        m = gen(dictionary, marker_id, int(size_px))
        m = np.asarray(m)
    except TypeError:
        m = np.zeros((int(size_px), int(size_px)), dtype=np.uint8)
        gen(dictionary, marker_id, int(size_px), m, 1)
    if m.ndim == 3:
        m = cv2.cvtColor(m, cv2.COLOR_BGR2GRAY)
    m = (m > 127).astype(np.uint8) * 255
    if m.shape != (size_px, size_px):
        m = cv2.resize(m, (size_px, size_px), interpolation=cv2.INTER_NEAREST)
    return m


def build_card(dpi=300):
    """Render the card as a grayscale uint8 image."""
    L = card_layout(dpi)
    w, h = L["size"]
    img = np.full((h, w), 255, dtype=np.uint8)

    x0, y0, x1, y1 = L["square"]
    cv2.rectangle(img, (x0, y0), (x1 - 1, y1 - 1), 0, -1)
    wx0, wy0, wx1, wy1 = L["white"]
    cv2.rectangle(img, (wx0, wy0), (wx1 - 1, wy1 - 1), 255, -1)

    mx0, my0, mx1, my1 = L["marker"]
    marker = _generate_marker(MARKER_ID, DICT_NAME, mx1 - mx0)
    img[my0:my1, mx0:mx1] = marker

    thick = max(1, dpi // 150)
    fs = dpi / 72.0 * 0.09
    y_sq = y1
    cv2.putText(img, TEXT_MAIN, (x0, y_sq + mm2px(10, dpi)),
                cv2.FONT_HERSHEY_SIMPLEX, fs, 0, thick, cv2.LINE_AA)
    cv2.putText(img, TEXT_SUB, (x0, y_sq + mm2px(17, dpi)),
                cv2.FONT_HERSHEY_SIMPLEX, fs * 0.75, 60, thick, cv2.LINE_AA)
    cv2.putText(img, TEXT_FOOT, (x0, h - mm2px(8, dpi)),
                cv2.FONT_HERSHEY_SIMPLEX, fs * 0.75, 0, thick, cv2.LINE_AA)
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--outdir", default=str(Path(__file__).resolve().parents[1] / "docs" / "assets"))
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    img = build_card(args.dpi)
    out = outdir / f"reference_card_A6_{args.dpi}dpi.png"
    cv2.imwrite(str(out), img)
    L = card_layout(args.dpi)
    print(f"wrote {out}")
    print(f"  card {L['size'][0]}x{L['size'][1]} px ({CARD_MM[0]:.0f}x{CARD_MM[1]:.0f} mm)")
    print(f"  square {mm2px(SQUARE_MM, args.dpi)} px (= {SQUARE_MM} mm)  marker {mm2px(MARKER_MM, args.dpi)} px (= {MARKER_MM} mm)")
    print("PRINT AT 100% (no scaling), then ruler-verify the black square is exactly 100.0 mm")


if __name__ == "__main__":
    main()
