"""Scale anchor detection: ArUco card -> bimetallic coin -> prior.

Implements the three-tier anchor ladder from the plan:
  measured  - printed card (ArUco 4x4_50 id 7, 60.0 mm marker) beside the vessel
  measured  - bimetallic ₹10 coin (27.0 mm)
  prior     - no anchor in frame; scale must come from size priors (S3 owns it)

The anchor NEVER uses vessel/plate diameter for scale.

Return schema (estimate_anchor):
  method, label, cm_per_px, interval (lo, hi | None), H (3x3 | None),
  tilt_deg, plane_height_interval_mm, exif_distance_cm, reason, extras
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from geo import camera_matrix, mean_side_px, pose_from_marker

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "anchor_config.json"

_REL_Z = 1.645          # one-sided 90% normal quantile
_EXIF_FOCAL = 37386     # FocalLength
_EXIF_SUBJ_DIST = 41486 # SubjectDistance
_EXIF_DIGI_ZOOM = 41540 # DigitalZoomRatio


def load_config(path=None):
    with open(path or _CONFIG_PATH) as f:
        return json.load(f)


def read_exif(path):
    """Best-effort EXIF: focal_mm, subject_distance_cm, digital_zoom, camera."""
    out = {"focal_mm": None, "subject_distance_cm": None, "digital_zoom": None, "camera": None}
    try:
        with Image.open(path) as im:
            ex = im.getexif()
    except Exception:
        return out

    def _rational(v):
        try:
            f = float(v)
            return f if np.isfinite(f) and f > 0 else None
        except Exception:
            return None

    focal = _rational(ex.get(_EXIF_FOCAL))
    if focal:
        out["focal_mm"] = focal
    dz = _rational(ex.get(_EXIF_DIGI_ZOOM))
    if dz and dz != 1.0:
        out["digital_zoom"] = dz
    sd = ex.get(_EXIF_SUBJ_DIST)
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
        det = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
        corners, ids, _ = det.detectMarkers(gray)
    else:
        corners, ids, _ = cv2.aruco.detectMarkers(gray, dictionary)
    return _detect_marker(corners, ids, marker_id)


def _quiet_zone_ok(corners, gray):
    """A true marker has white quiet zone just outside its black border.

    Samples points 0.35 module beyond each edge; >=60% must be white.
    Rejects decoy quads locked onto a surrounding black frame.
    """
    h, w = gray.shape
    c = np.asarray(corners, dtype=np.float64).reshape(4, 2)
    centre = c.mean(axis=0)
    side = mean_side_px(c)
    d = max(3.0, 0.35 * side / 6.0)
    samples = []
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
            p = a + t * edge + d * n
            xi, yi = int(round(p[0])), int(round(p[1]))
            if 0 <= xi < w and 0 <= yi < h:
                samples.append(gray[yi, xi])
    if len(samples) < 12:
        return False
    return float(np.mean(np.asarray(samples) > 170)) >= 0.6


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
    try:
        focal = exif.get("focal_mm") or cfg["camera"]["focal_length_fallback_mm"]
        K = camera_matrix(focal, cfg["camera"].get("sensor_width_mm", 6.17),
                          img_bgr.shape[1], img_bgr.shape[0])
        pose = pose_from_marker(corners, cfg["card"]["marker_mm"], K)
        H, tilt_deg, distance_cm = pose["H"], pose["tilt_deg"], pose["distance_cm"]
    except Exception as e:  # pose is optional; scale still valid
        notes.append(f"card pose failed: {e}")

    return {
        "method": "card_aruco",
        "label": "measured",
        "cm_per_px": float(cm_per_px),
        "interval": (float(interval[0]), float(interval[1])),
        "H": H,
        "tilt_deg": tilt_deg,
        "plane_height_interval_mm": tuple(cfg["plane_height_interval_mm"]),
        "exif_distance_cm": exif.get("subject_distance_cm"),
        "reason": "ArUco card detected (measured)",
        "extras": {"marker_side_px": float(side), "distance_cm": distance_cm,
                   "focal_mm": exif.get("focal_mm"),
                   "marker_corners_px": np.asarray(corners, dtype=np.float64)
                                        .reshape(4, 2).tolist()},
    }


def _golden(hsv):
    """Boolean mask of gold-ish bimetallic-coin outer metal."""
    h, s, _ = cv2.split(hsv)
    return (h >= 12) & (h <= 40) & (s >= 60)


def _validate_coin(x, y, r, gold, h, w, min_diam_px):
    """Ring must be mostly gold, centre must NOT be gold (bimetallic check)."""
    if 2 * r < min_diam_px:
        return None
    angles = np.linspace(0, 2 * np.pi, 72, endpoint=False)
    rr = 0.82 * r
    ring = gold[np.clip((y + rr * np.sin(angles)).astype(int), 0, h - 1),
                np.clip((x + rr * np.cos(angles)).astype(int), 0, w - 1)]
    ys, xs = np.ogrid[-r:r + 1, -r:r + 1]
    inner = (xs * xs + ys * ys) <= (0.45 * r) ** 2
    cy0, cy1 = max(0, y - r), min(h, y + r + 1)
    cx0, cx1 = max(0, x - r), min(w, x + r + 1)
    patch_g = gold[cy0:cy1, cx0:cx1]
    patch_i = inner[:cy1 - cy0, :cx1 - cx0]
    if patch_i.sum() == 0:
        return None
    ring_frac = float(ring.mean())
    center_frac = float(patch_g[patch_i].mean())
    if ring_frac >= 0.6 and center_frac <= 0.3:
        return ring_frac, center_frac
    return None


def _coin_candidates(gray, hsv, gold, cfg):
    """Candidates from HSV gold-mask contours (primary) + Hough (secondary)."""
    coin = cfg["coin"]
    h, w = gray.shape
    min_r = max(10, coin["min_diameter_px"] // 2)
    out = []

    blur = cv2.GaussianBlur(gold.astype(np.uint8) * 255, (7, 7), 0)
    mask = cv2.morphologyEx(blur, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts:
        if cv2.contourArea(c) < np.pi * min_r * min_r * 0.5:
            continue
        (x, y), r = cv2.minEnclosingCircle(c)
        circ = cv2.contourArea(c) / (np.pi * r * r + 1e-9)
        if 0.35 <= circ <= 1.05:
            out.append((int(x), int(y), int(round(r))))

    try:
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2,
                                   minDist=max(60, min_r), param1=60, param2=24,
                                   minRadius=min_r, maxRadius=max(min_r + 1, min(h, w) // 3))
        if circles is not None:
            out.extend((int(x), int(y), int(r)) for x, y, r in circles[0])
    except cv2.error:
        pass
    return out


def _try_coin(img_bgr, cfg, notes):
    coin = cfg["coin"]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(cv2.GaussianBlur(img_bgr, (5, 5), 0), cv2.COLOR_BGR2HSV)
    gold = _golden(hsv)
    h, w = gray.shape

    best = None
    for x, y, r in _coin_candidates(gray, hsv, gold, cfg):
        ok = _validate_coin(x, y, r, gold, h, w, coin["min_diameter_px"])
        if ok is None:
            continue
        if best is None or r > best[2]:
            best = (x, y, r, ok[0], ok[1])
    if best is None:
        return None

    x, y, r, ring_frac, center_frac = best
    diam_px = 2.0 * r
    diam_cm = coin["diameter_mm"] / 10.0
    cm_per_px = diam_cm / diam_px
    sigma_d = 2.0 * cfg.get("_coin_sigma_px", 2.0)
    rel = _REL_Z * sigma_d / diam_px
    interval = (cm_per_px * (1.0 - rel), cm_per_px * (1.0 + rel))

    return {
        "method": "coin_bimetallic",
        "label": "measured",
        "cm_per_px": float(cm_per_px),
        "interval": (float(interval[0]), float(interval[1])),
        "H": None,
        "tilt_deg": None,
        "plane_height_interval_mm": tuple(cfg["plane_height_interval_mm"]),
        "exif_distance_cm": None,
        "reason": "bimetallic coin detected (measured)",
        "extras": {"diam_px": float(diam_px), "center": [x, y],
                   "ring_gold_frac": ring_frac, "center_gold_frac": center_frac},
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


def estimate_anchor(image, config=None, exif=None):
    """Run the tier ladder on a BGR ndarray (or file path if str/Path).

    exif: dict from read_exif(image_path) — pass explicitly when image is ndarray.
    """
    cfg = dict(config or load_config())
    cfg.setdefault("_coin_sigma_px", 2.0)

    path = None
    if isinstance(image, (str, Path)):
        path = str(image)
        img = cv2.imread(path)
        if img is None:
            raise FileNotFoundError(image)
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

    result = _try_coin(img, cfg, notes)
    if result:
        result["reason"] = "; ".join(notes + [result["reason"]]) if notes else result["reason"]
        return result

    if not notes:
        notes.append("no card or coin anchor in frame")
    return _prior("; ".join(notes), cfg)
