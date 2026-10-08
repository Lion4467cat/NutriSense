import numpy as np


def fit_plane(points_xyz):
    """Least-squares plane z = a*x + b*y + c through Nx3 points.

    Returns (a, b, c, rms).
    """
    p = np.asarray(points_xyz, dtype=np.float64).reshape(-1, 3)
    A = np.column_stack([p[:, 0], p[:, 1], np.ones(len(p))])
    (a, b, c), *_ = np.linalg.lstsq(A, p[:, 2], rcond=None)
    rms = float(np.sqrt(np.mean(plane_residuals(p, a, b, c) ** 2)))
    return float(a), float(b), float(c), rms


def plane_residuals(points_xyz, a, b, c):
    """Signed z residuals of points against plane z = a*x + b*y + c."""
    p = np.asarray(points_xyz, dtype=np.float64).reshape(-1, 3)
    return p[:, 2] - (a * p[:, 0] + b * p[:, 1] + c)
