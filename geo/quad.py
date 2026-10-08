import numpy as np


def order_corners(pts):
    """Order 4 points as TL, TR, BR, BL. pts: (4,2) array-like -> (4,2) float64."""
    p = np.asarray(pts, dtype=np.float64).reshape(4, 2)
    s = p[:, 0] + p[:, 1]          # TL small, BR large
    d = p[:, 1] - p[:, 0]          # TR small (y-x most negative), BL large
    tl = int(np.argmin(s))
    br = int(np.argmax(s))
    tr = int(np.argmin(d))
    bl = int(np.argmax(d))
    return p[[tl, tr, br, bl]]


def quad_side_lengths(quad):
    """4 side lengths of quad in order TL->TR->BR->BL->TL. Returns (4,) array."""
    q = np.asarray(quad, dtype=np.float64).reshape(4, 2)
    nxt = np.roll(q, -1, axis=0)
    return np.linalg.norm(nxt - q, axis=1)


def mean_side_px(quad):
    return float(np.mean(quad_side_lengths(quad)))


def quad_area(quad):
    """Shoelace area of quad (px^2, always positive)."""
    q = np.asarray(quad, dtype=np.float64).reshape(4, 2)
    x, y = q[:, 0], q[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def convex_quad(quad, tol=1e-6):
    """True if the 4 corners form a convex quadrilateral."""
    q = np.asarray(quad, dtype=np.float64).reshape(4, 2)
    u = np.roll(q, -1, axis=0) - q
    v = np.roll(q, -2, axis=0) - np.roll(q, -1, axis=0)
    z = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]   # 2-D cross (numpy>=2 has no np.cross for 2D)
    return bool(np.all(z > tol) or np.all(z < -tol))
