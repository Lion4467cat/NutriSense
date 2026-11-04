"""Scale anchor detection: ArUco card -> prior.

Implements the two-tier anchor ladder:
  measured  - printed card (ArUco 4x4_50 id 7, 60.0 mm marker) beside the vessel
  prior     - no reference card in frame; scale must come from size priors (S3 owns it)

The anchor NEVER uses vessel/plate diameter for scale.

Return schema (estimate_anchor):
  method, label, cm_per_px, interval (lo, hi | None), H (3x3 | None),
  tilt_deg, plane_height_interval_mm, exif_distance_cm, reason, extras
"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from config import load_anchor_config as load_config
from geo import camera_matrix, camera_matrix_from_35mm, mean_side_px, pose_from_marker

_REL_Z = 1.645          # one-sided 90% normal quantile
_EXIF_FOCAL = 37386     # FocalLength (Exif sub-IFD)
_EXIF_SUBJ_DIST = 37382 # SubjectDistance (Exif sub-IFD)
_EXIF_DIGI_ZOOM = 41988 # DigitalZoomRatio (Exif sub-IFD)
_EXIF_FOCAL_35 = 41989  # FocalLengthIn35mmFilm (Exif sub-IFD)
_EXIF_IFD = 0x8769      # pointer to the Exif sub-IFD


def read_exif(path):
    """Best-effort EXIF: focal_mm, subject_distance_cm, digital_zoom, camera."""
    out: dict[str, float | str | None] = {
        "focal_mm": None, "subject_distance_cm": None, "digital_zoom": None,
        "focal_length_35mm": None, "camera": None,
    }
    try:
        with Image.open(path) as im:
            ex = im.getexif()
            exif_ifd = ex.get_ifd(_EXIF_IFD)
    except Exception:
        return out

    def _get(tag):
        # these tags live in the Exif sub-IFD; some writers put them in IFD0
        v = exif_ifd.get(tag)
        return ex.get(tag) if v is None else v

    def _rational(v):
        try:
            f = float(v)
            return f if np.isfinite(f) and f > 0 else None
        except Exception:
            return None

    focal = _rational(_get(_EXIF_FOCAL))
    if focal:
        out["focal_mm"] = focal
    f35 = _rational(_get(_EXIF_FOCAL_35))
    if f35:
        out["focal_length_35mm"] = f35
    dz = _get(_EXIF_DIGI_ZOOM)
    if dz is not None:
        # EXIF spec: DigitalZoomRatio 0/0 (undefined) means digital zoom was
        # not used — Samsung phones write exactly that. PIL surfaces it as a
        # NaN float and some writers emit the literal string "0/0". Map both
        # to 1.0 (verified unzoomed) instead of swallowing them as absent.
        try:
            f = float(dz)
        except (TypeError, ValueError):
            f = None
        if ((f is not None and (not np.isfinite(f) or f == 0))
                or (isinstance(dz, str) and dz.strip() == "0/0")):
            out["digital_zoom"] = 1.0
        else:
            v = _rational(dz)
            if v:
                out["digital_zoom"] = v
    sd = _get(_EXIF_SUBJ_DIST)
    if sd is not None:
        try:
            if isinstance(sd, str) and "/" in sd:
                n, d = sd.split("/")
                v = float(n) / float(d)
            else:
                v = float(sd)
            if np.isfinite(v) and v > 0:
                out["subject_distance_cm"] = v if v < 100 else v / 10.0
        except Exception:
            pass
    make = ex.get(271)
    model = ex.get(272)
    if make or model:
        out["camera"] = " ".join(str(x) for x in (make, model) if x)
    return out


def _detect_marker(corners_all, ids, marker_id):
    """Return list of (4,2) corner arrays for marker_id, in ArUco marker order."""
    if ids is None:
        return []
    found = []
    for c, i in zip(corners_all, np.asarray(ids).flatten()):
        if int(i) == int(marker_id):
            found.append(np.asarray(c, dtype=np.float64).reshape(4, 2))
    return found


def _aruco_detect(gray, marker_id, dict_name):
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dict_name))
    if hasattr(cv2.aruco, "ArucoDetector"):
        params = cv2.aruco.DetectorParameters()
        # On 12 MP (4032x3024) smartphone captures at 35 cm, a 60 mm 6x6-module
        # marker spans ~320-700 px (1 module ~ 53-116 px). OpenCV's default max
        # window (23 px) is narrower than half a module, hollowing interior bits.
        params.adaptiveThreshWinSizeMax = 53
        # Allow up to 5% perimeter deviation (~3 mm bow on a 60 mm paper card).
        params.polygonalApproxAccuracyRate = 0.05
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        det = cv2.aruco.ArucoDetector(dictionary, params)
        corners, ids, _ = det.detectMarkers(gray)
        found = _detect_marker(corners, ids, marker_id)
        if not found:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
            corners, ids, _ = det.detectMarkers(clahe)
            found = _detect_marker(corners, ids, marker_id)
        if not found:
            # When the paper card is near the camera frame boundary so a black
            # marker corner lies within <3 px of the image edge, OpenCV's
            # border-distance check discards the outer contour unless a narrow
            # white border completes the quiet zone.
            pad = 16
            padded = cv2.copyMakeBorder(
                gray, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)
            corners, ids, _ = det.detectMarkers(padded)
            found = [c - float(pad) for c in _detect_marker(corners, ids, marker_id)]
        return found
    corners, ids, _ = cv2.aruco.detectMarkers(gray, dictionary)
    return _detect_marker(corners, ids, marker_id)


def _quiet_zone_ok(corners, gray):
    """A true marker has white quiet zone just outside its black border.

    In DICT_4X4 (6x6 modules = 20 black border modules + 16 payload modules),
    ~78-81% of the marker interior is black ink, so median(inside) measures local
    black-ink reflectance I_black under ambient illumination. A valid paper quiet
    zone must exceed max(95, min(170, I_black + 65)) — requiring >= 65/255 (25.5%
    ISO/IEC 15415 symbol contrast) above black ink and an absolute floor of 95/255
    to reject underexposed backlit frames while admitting shadowed indoor cards.
    """
    h, w = gray.shape
    c = np.asarray(corners, dtype=np.float64).reshape(4, 2)
    centre = c.mean(axis=0)
    side = mean_side_px(c)
    d_ext = max(3.0, 0.35 * side / 6.0)
    d_blk = max(3.0, 0.50 * side / 6.0)
    ext_samples = []
    blk_samples = []
    for i in range(4):
        a, b = c[i], c[(i + 1) % 4]
        edge = b - a
        length = np.linalg.norm(edge)
        if length < 1e-6:
            continue
        n = np.array([edge[1], -edge[0]]) / length
        mid = (a + b) / 2.0
        if np.dot(n, mid - centre) < 0:
            n = -n
        for t in np.linspace(0.2, 0.8, 9):
            p_ext = a + t * edge + d_ext * n
            xi_e, yi_e = int(round(p_ext[0])), int(round(p_ext[1]))
            if 0 <= xi_e < w and 0 <= yi_e < h:
                ext_samples.append(gray[yi_e, xi_e])
            p_blk = a + t * edge - d_blk * n
            xi_b, yi_b = int(round(p_blk[0])), int(round(p_blk[1]))
            if 0 <= xi_b < w and 0 <= yi_b < h:
                blk_samples.append(gray[yi_b, xi_b])
    if len(ext_samples) < 12:
        return False

    ext = np.asarray(ext_samples, dtype=np.float64)
    blk = np.asarray(blk_samples, dtype=np.float64)

    # 1. Contrast check against interior black border
    if len(ext) >= 18 and len(blk) >= 18:
        mean_ext = float(np.mean(ext))
        mean_blk = float(np.mean(blk))
        michelson = (mean_ext - mean_blk) / (mean_ext + mean_blk + 1e-5)
        contrast_thresh = max(85.0, float(np.percentile(blk, 75)) * 2.0 + 25.0)
        frac_above = float(np.mean(ext > contrast_thresh))
        if michelson >= 0.42 and frac_above >= 0.55:
            return True

    # 2. High brightness rule
    if float(np.mean(ext > 170.0)) >= 0.6:
        return True

    x0, y0 = np.maximum(0, np.floor(c.min(axis=0)).astype(int))
    x1, y1 = np.minimum([w, h], np.ceil(c.max(axis=0)).astype(int) + 1)
    patch = gray[y0:y1, x0:x1]
    poly = np.zeros_like(patch)
    cv2.fillConvexPoly(poly, (c - [x0, y0]).astype(np.int32), 255)
    inside = patch[poly > 0]
    inside_med = float(np.median(inside)) if inside.size else 128.0
    thresh = max(95.0, min(170.0, inside_med + 65.0))
    return float(np.mean(ext > thresh)) >= 0.55 and float(np.median(ext)) >= thresh


def _try_card(img_bgr, cfg, exif, notes):
    tier = cfg["tier"]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    marks = _aruco_detect(gray, cfg["card"]["marker_id"], cfg["card"]["dictionary"])
    marks = [m for m in marks if _quiet_zone_ok(m, gray)]
    if not marks:
        return None
    corners = max(marks, key=mean_side_px)
    side = mean_side_px(corners)
    if side < tier["min_marker_side_px"]:
        notes.append(f"card marker found but too small ({side:.0f} px < {tier['min_marker_side_px']})")
        return None

    marker_cm = cfg["card"]["marker_mm"] / 10.0
    cm_per_px = marker_cm / side
    sigma_side = np.sqrt(2.0) * 0.5
    rel = _REL_Z * sigma_side / side
    interval = (cm_per_px * (1.0 - rel), cm_per_px * (1.0 + rel))

    H = None
    tilt_deg = None
    distance_cm = None
    pose_method = None
    try:
        # Camera matrix priority: EXIF 35mm-equivalent focal (sensor-size
        # independent, verified within ~2% on real phones) > EXIF focal plus
        # assumed sensor width > fallback focal. See CARD_REPORT v2, Item 2.
        f35 = exif.get("focal_length_35mm")
        if f35:
            K = camera_matrix_from_35mm(f35, img_bgr.shape[1], img_bgr.shape[0])
            pose_method = "exif_focal_35mm"
        else:
            focal = exif.get("focal_mm") or cfg["camera"]["focal_length_fallback_mm"]
            K = camera_matrix(focal, cfg["camera"].get("sensor_width_mm", 6.17),
                              img_bgr.shape[1], img_bgr.shape[0])
            pose_method = "exif_focal_sensor_width" if exif.get("focal_mm") else "fallback_focal"
        pose = pose_from_marker(corners, cfg["card"]["marker_mm"], K)
        max_reproj = float(cfg["camera"].get("max_pose_reproj_err_px", 3.0))
        max_tilt = float(cfg["camera"].get("max_pose_tilt_deg", 65.0))
        reproj = pose["reproj_err_px"]
        if reproj > max_reproj:
            # Degenerate pose (heavy tilt, occlusion artefacts): drop the pose,
            # keep the 2D scale, which does not depend on K.
            notes.append(f"card pose rejected: reproj err {reproj:.2f} px > {max_reproj:.1f} px")
        elif float(pose["tilt_deg"]) > max_tilt:
            notes.append(f"card pose rejected: grazing tilt {pose['tilt_deg']:.1f} deg > {max_tilt:.1f} deg")
        else:
            H, tilt_deg, distance_cm = pose["H"], pose["tilt_deg"], pose["distance_cm"]
    except Exception as e:  # pose is optional; scale still valid
        notes.append(f"card pose failed: {e}")

    return {
        "method": "card_aruco",
        "label": "measured",
        "cm_per_px": float(cm_per_px),
        "marker_mm": float(cfg["card"]["marker_mm"]),
        "interval": (float(interval[0]), float(interval[1])),
        "H": H,
        "tilt_deg": tilt_deg,
        "plane_height_interval_mm": tuple(cfg["plane_height_interval_mm"]),
        "exif_distance_cm": exif.get("subject_distance_cm"),
        "reason": "ArUco card detected (measured)",
        "extras": {"marker_side_px": float(side), "distance_cm": distance_cm,
                   "focal_mm": exif.get("focal_mm"),
                   "pose_method": pose_method,
                   "marker_corners_px": np.asarray(corners, dtype=np.float64)
                                          .reshape(4, 2).tolist()},
    }


def _prior(reason, cfg):
    return {
        "method": "prior",
        "label": "prior",
        "cm_per_px": None,
        "interval": None,
        "H": None,
        "tilt_deg": None,
        "plane_height_interval_mm": tuple(cfg["plane_height_interval_mm"]),
        "exif_distance_cm": None,
        "reason": reason,
        "extras": {},
    }


def refine_anchor_pose(anchor, K, max_reproj_err_px=3.0, max_tilt_deg=65.0):
    """Re-solve a measured marker pose in the depth provider's camera frame.

    The 2D marker scale is independent of K; pose/tilt is not. If the depth
    provider supplies its own intrinsics, callers use this adapter so later
    footprint geometry does not mix the detector's fallback K with depth K.
    A failed solve drops pose/tilt while retaining measured 2D scale.
    """
    if not anchor or anchor.get("label") != "measured":
        return anchor
    extras = dict(anchor.get("extras") or {})
    corners = extras.get("marker_corners_px")
    marker_mm = anchor.get("marker_mm")
    if corners is None or marker_mm is None:
        return anchor
    refined = dict(anchor)
    try:
        pose = pose_from_marker(corners, float(marker_mm), K)
        reproj = float(pose["reproj_err_px"])
        tilt = float(pose["tilt_deg"])
        extras["depth_pose_reproj_err_px"] = reproj
        if (not np.isfinite(reproj) or reproj > float(max_reproj_err_px)
                or not np.isfinite(tilt) or tilt > float(max_tilt_deg)):
            refined.update(H=None, tilt_deg=None)
            extras["depth_pose_method"] = "rejected"
        else:
            refined.update(H=pose["H"], tilt_deg=pose["tilt_deg"])
            extras["depth_pose_distance_cm"] = pose["distance_cm"]
            extras["depth_pose_method"] = "moge_intrinsics"
    except Exception as exc:
        refined.update(H=None, tilt_deg=None)
        extras["depth_pose_method"] = "failed"
        extras["depth_pose_error"] = type(exc).__name__
    refined["extras"] = extras
    return refined


def prior_anchor(reason, cfg=None):
    """Public prior-tier anchor (the anchor stage's degrade fallback)."""
    return _prior(reason, cfg if cfg is not None else load_config())


def estimate_anchor(image, config=None, exif=None):
    """Run the tier ladder on a BGR ndarray (or file path if str/Path).

    exif: dict from read_exif(image_path) — pass explicitly when image is ndarray.
    """
    cfg = dict(config or load_config())

    path = None
    if isinstance(image, (str, Path)):
        path = str(image)
        img = cv2.imread(path)
        if img is None:
            raise FileNotFoundError("anchor image failed to decode")
    else:
        img = image
    if exif is None:
        exif = read_exif(path) if path else {"focal_mm": None, "subject_distance_cm": None,
                                             "digital_zoom": None, "camera": None}

    notes = []
    result = _try_card(img, cfg, exif, notes)
    if result:
        result["reason"] = "; ".join(notes + [result["reason"]]) if notes else result["reason"]
        return result

    if not notes:
        notes.append("no reference card in frame — scale from size priors")
    return _prior("; ".join(notes), cfg)
