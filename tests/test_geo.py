import numpy as np
import cv2

from geo import order_corners, quad_side_lengths, mean_side_px, quad_area, convex_quad
from geo import camera_matrix, pose_from_marker, plane_to_image_homography
from geo import fit_plane


def test_order_corners_shuffled():
    tl, tr, br, bl = [50, 40], [300, 45], [310, 200], [40, 210]
    pts = np.array([br, tl, bl, tr], dtype=float)
    got = order_corners(pts)
    assert np.allclose(got, [[50, 40], [300, 45], [310, 200], [40, 210]])


def test_quad_metrics_square():
    q = np.array([[0, 0], [100, 0], [100, 50], [0, 50]], dtype=float)
    assert np.allclose(quad_side_lengths(q), [100, 50, 100, 50])
    assert abs(quad_area(q) - 5000.0) < 1e-9
    assert abs(mean_side_px(q) - 75.0) < 1e-9
    assert convex_quad(q)


def test_convex_rejects_concave():
    q = np.array([[0, 0], [10, 0], [2, 4], [10, 8]], dtype=float)
    assert not convex_quad(q)


def test_fit_plane_exact():
    rng = np.random.default_rng(1)
    xy = rng.uniform(-10, 10, size=(50, 2))
    a_true, b_true, c_true = 2.0, -1.0, 5.0
    z = a_true * xy[:, 0] + b_true * xy[:, 1] + c_true
    a, b, c, rms = fit_plane(np.column_stack([xy, z]))
    assert abs(a - a_true) < 1e-9
    assert abs(b - b_true) < 1e-9
    assert abs(c - c_true) < 1e-9
    assert rms < 1e-9


def test_pose_from_marker_roundtrip():
    K = camera_matrix(4.0, 6.17, 1920, 1080)
    rvec_true = np.array([[np.radians(6.0)], [np.radians(-4.0)], [0.0]])
    R, _ = cv2.Rodrigues(rvec_true)
    t = np.array([25.0, -18.0, 600.0])  # mm
    h = 30.0
    obj = np.array([[-h, h, 0], [h, h, 0], [h, -h, 0], [-h, -h, 0]], dtype=float)
    pts = (R @ obj.T + t.reshape(3, 1)).T
    img = (K @ pts.T).T
    img = img[:, :2] / img[:, 2:]

    out = pose_from_marker(img, 60.0, K)
    tilt_true = np.degrees(np.arccos(np.clip(R[2, 2], -1, 1)))
    assert abs(out["tilt_deg"] - tilt_true) < 0.05
    assert abs(out["distance_cm"] - np.linalg.norm(t) / 10.0) < 0.1
    assert out["H"].shape == (3, 3)
    # homography maps plane mm -> image px: check marker corner correspondence
    p = out["H"] @ np.array([-30.0, 30.0, 1.0])
    p = p[:2] / p[2]
    assert np.allclose(p, img[0], atol=0.5)
