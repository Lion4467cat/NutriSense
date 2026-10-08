"""Minimal synthetic scene renderer (S0 v0).

Just enough to smoke-test the anchor ladder: perspective-warps an image
(e.g. the reference card) onto a plain background with optional noise.
The full dish renderer (geometry + material + camera) arrives with S2 tests.
"""
import cv2
import numpy as np


def trapezoid_quad(w, h, scale=0.34, y_frac=0.16, taper=0.10, x_frac=0.5):
    """A plausible 'card lying on a table' quad inside a (w,h) canvas.

    Top edge wider than bottom by 2*taper (perspective foreshortening).
    """
    cw = w * scale
    ch = cw * (148.0 / 105.0) * (1.0 - 0.5 * taper)
    x0 = w * x_frac - cw / 2.0
    y0 = h * y_frac
    t = cw * taper / 2.0
    return np.array([
        [x0 + t, y0],
        [x0 + cw - t, y0],
        [x0 + cw, y0 + ch],
        [x0, y0 + ch],
    ], dtype=np.float64)


def warp_with_mask(img, quad, canvas_size):
    """Perspective-warp img (any size) onto quad of a canvas.

    Returns (warped_bgr, mask, H) where H maps img px -> canvas px.
    """
    cw, ch = canvas_size
    ih, iw = img.shape[:2]
    src = np.array([[0, 0], [iw - 1, 0], [iw - 1, ih - 1], [0, ih - 1]], dtype=np.float32)
    dst = np.asarray(quad, dtype=np.float32)
    H = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, H, (cw, ch), flags=cv2.INTER_LINEAR)
    mask = cv2.warpPerspective(np.full((ih, iw), 255, np.uint8), H, (cw, ch),
                               flags=cv2.INTER_NEAREST)
    return warped, mask, H


def render_on_background(img, quad, canvas_size=(1400, 1100), bg=205,
                         noise=4.0, seed=0):
    """Composite img onto a flat noisy background at quad. Returns BGR uint8."""
    cw, ch = canvas_size
    rng = np.random.default_rng(seed)
    base = np.full((ch, cw), bg, dtype=np.float64)
    if noise > 0:
        base += rng.normal(0.0, noise, base.shape)
    base = np.clip(base, 0, 255).astype(np.uint8)

    if img.ndim == 2:
        img3 = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        img3 = img
    warped, mask, H = warp_with_mask(img3, quad, canvas_size)
    canvas = cv2.cvtColor(base, cv2.COLOR_GRAY2BGR)
    sel = mask > 127
    canvas[sel] = warped[sel]
    return canvas, H
