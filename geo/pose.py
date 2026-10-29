import numpy as np
import cv2


def camera_matrix(focal_length_mm, sensor_width_mm, image_width_px, image_height_px):
    """Pinhole K assuming principal point at image centre."""
    f_px = focal_length_mm / sensor_width_mm * float(image_width_px)
    return np.array([
        [f_px, 0.0, image_width_px / 2.0],
        [0.0, f_px, image_height_px / 2.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)


def camera_matrix_from_35mm(focal_35mm, image_width_px, image_height_px):
    """Pinhole K from the EXIF 35mm-equivalent focal length.

    Sensor-size independent: f_px = f35 * diag_px / diag_35mm, with the
    35mm 'full frame' diagonal of 43.267 mm. Verified against real phones
    to be within ~2% of the true focal (CARD_REPORT/real_card_report_v2.md);
    the focal_mm/sensor_width path was off by up to 58%.
    """
    f_px = float(focal_35mm) * np.hypot(float(image_width_px), float(image_height_px)) / 43.267
    return np.array([
        [f_px, 0.0, image_width_px / 2.0],
        [0.0, f_px, image_height_px / 2.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)


def pose_from_marker(corners_px, marker_mm, K):
    """Planar pose of a square marker.

    corners_px: (4,2) in OpenCV ArUco return order (marker frame, y-down,
    clockwise from marker-TL). Object points use that same marker frame so
    in-plane marker rotation is absorbed by the solve.

    Returns dict: rvec, tvec, tilt_deg, distance_cm, H (plane mm -> image px).
    """
    h = float(marker_mm) / 2.0
    obj = np.array([
        [-h,  h, 0.0],
        [ h,  h, 0.0],
        [ h, -h, 0.0],
        [-h, -h, 0.0],
    ], dtype=np.float64)
    img = np.asarray(corners_px, dtype=np.float64).reshape(4, 2)

    flags = getattr(cv2, "SOLVEPNP_IPPE_SQUARE", None)
    if flags is None:
        flags = cv2.SOLVEPNP_ITERATIVE
    ok, rvec, tvec = cv2.solvePnP(obj, img, K, None, flags=flags)
    if not ok:
        raise ValueError("solvePnP failed on marker corners")

    R, _ = cv2.Rodrigues(rvec)
    normal = R[:, 2]
    z_axis = np.array([0.0, 0.0, 1.0])
    tilt_deg = float(np.degrees(np.arccos(np.clip(np.dot(normal, z_axis), -1.0, 1.0))))
    if tilt_deg > 90.0:            # planar pose flip: use acute incidence angle
        tilt_deg = 180.0 - tilt_deg
    tvec = tvec.reshape(3)
    distance_cm = float(np.linalg.norm(tvec)) / 10.0
    proj, _ = cv2.projectPoints(obj, rvec, tvec, K, None)
    reproj_err_px = float(
        np.mean(np.linalg.norm(proj.reshape(4, 2) - img, axis=1))
    )
    return {
        "rvec": rvec,
        "tvec": tvec,
        "tilt_deg": tilt_deg,
        "distance_cm": distance_cm,
        "H": plane_to_image_homography(R, tvec, K),
        "reproj_err_px": reproj_err_px,
    }


def plane_to_image_homography(R, t, K):
    """Homography mapping plane coordinates (mm) -> image pixels, from R|t pose."""
    Rt = np.hstack([R[:, 0:1], R[:, 1:2], np.asarray(t, dtype=np.float64).reshape(3, 1)])
    return K @ Rt
