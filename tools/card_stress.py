"""Frozen, seeded card-path stress suite on the synthetic renderer.

Measures how the reference-card detector (`models/scale_anchor.py`) and the
card-path portion estimator degrade under controlled perturbations of the
S0 synthetic scenes (`tests/synth/scene.py`). Measurement only: this tool
changes no model, threshold or config — it renders, detects, measures.

For every perturbation LEVEL it reports:
  detection rate            — fraction of scenes where the card tier returned
                              a scale (method == "card_aruco")
  cm_per_px relative error  — |est/gt - 1| against the renderer's planted
                              marker ground truth
  tilt estimation error     — |est_tilt - gt_tilt| in degrees
  FALSE-ACCEPT rate         — detections that returned a scale more than
                              5% from the truth, divided by all scenes

Every number is labelled "synthetic, not real-world": these are rendered
scenes, not canteen photographs.

Levels (ordered benign -> severe) and their construction:
  card_tilt_deg        0,15,30,45,60            camera elevation on the card
  card_distance_px     170,106,78                camera distance (marker px)
  marker_occlusion_pct 0,10,25,40                marker pixels painted over
  glare                none,mild,strong          soft specular patches
  dim_light            none,mild,strong          exposure x gamma
  gaussian_blur        0,1.5,3,5                 sigma px
  jpeg                 none,q30                  recompress at quality 30
  low_resolution       1.0,0.5,0.25,0.125        downscale/upscale factors
  plate_food           none,plate_only,plate+food scene content

Runs are fully seeded (scene variation, perturbation jitter, bootstrap),
so the same --seed reproduces the report byte-for-byte.

Run:
  .venv/bin/python -m tools.card_stress                     # full baseline
  .venv/bin/python -m tools.card_stress --scenes 3 --reps 32 --groups gaussian_blur
Exit: 0 = report written · 2 = bad arguments
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import cv2
import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import load_menu  # noqa: E402
from models.portion_estimator import estimate_portion  # noqa: E402
from models.scale_anchor import estimate_anchor  # noqa: E402
from tests.synth.scene import VESSELS, default_scene, render_scene  # noqa: E402

LABEL = "synthetic, not real-world"
FALSE_ACCEPT_REL = 0.05
DEFAULT_SCENES = 30
DEFAULT_SEED = 42
DEFAULT_REPS = 2000
DEFAULT_OUT = _ROOT / "data" / "reports" / "card_stress_baseline.json"
DETECT_LEVEL = 0.95                 # "first falls below 95%" threshold

# group -> (levels in benign->severe order, kind, params)
GROUPS: dict[str, dict] = {
    "card_tilt_deg":        {"levels": [0, 15, 30, 45, 60],        "kind": "render"},
    "card_distance_px":     {"levels": [170, 106, 78],             "kind": "render"},
    "marker_occlusion_pct": {"levels": [0, 10, 25, 40],            "kind": "post"},
    "glare":                {"levels": ["none", "mild", "strong"], "kind": "post"},
    "dim_light":            {"levels": ["none", "mild", "strong"], "kind": "post"},
    "gaussian_blur":        {"levels": [0.0, 1.5, 3.0, 5.0],       "kind": "post"},
    "jpeg":                 {"levels": ["none", "q30"],            "kind": "post"},
    "low_resolution":       {"levels": [1.0, 0.5, 0.25, 0.125],    "kind": "post"},
    "plate_food":           {"levels": ["none", "plate_only", "plate+food"], "kind": "render"},
}

# card_distance_px levels: camera distance (mm) chosen so the 60 mm marker
# projects near the nominal px at tilt 30 (calibrated on this tree).
DIST_MM_BY_PX = {170: 300.0, 106: 480.0, 78: 650.0}
DIST_TILT_DEG = 30.0
DIM_LIGHT = {"none": (1.0, 1.0), "mild": (0.65, 1.25), "strong": (0.40, 1.60)}
GLARE_SPEC = {"mild": (1, 0.45, 0.75), "strong": (2, 0.70, 0.95)}


# --------------------------------------------------------------- rendering --
def camera_for(tilt_deg: float, az_deg: float, dist_mm: float,
               center: tuple[float, float]) -> dict:
    """Camera looking at the card centre with a given card-plane incidence.

    tilt_deg is the angle between the optical axis and the card normal
    (0 = straight down onto the card). A sub-mm lateral epsilon keeps the
    exact-vertical look-at non-degenerate (renderer cross product).
    """
    t, az = np.radians(tilt_deg), np.radians(az_deg)
    u = np.array([np.cos(az), np.sin(az), 0.0])
    c0 = np.array([center[0], center[1], 0.6])
    pos = c0 + dist_mm * (np.sin(t) * u + np.cos(t) * np.array([0.0, 0.0, 1.0]))
    pos = pos + np.array([1e-3 * dist_mm, 0.0, 0.0])   # avoid vertical degeneracy
    return {"pos": tuple(float(x) for x in pos),
            "target": (center[0], center[1], 0.0),
            "focal_mm": 4.0, "sensor_width_mm": 6.17}


def scene_variation(scene_idx: int, seed: int) -> dict:
    """Per-scene geometry variation, seeded and identical across groups.

    Azimuth is held near due -y (255..275 deg): that keeps the plate and the
    card at similar camera depth and incidence, matching the renderer's own
    default scene framing (the condition under which the +/-7% volume claim
    was measured). Card-centred azimuths put the plate 15-20 deg more
    oblique than the card and swamp the tilt effect with a scale-transfer
    error the pipeline never claims to correct.
    """
    rng = np.random.default_rng(np.random.SeedSequence([seed, scene_idx]))
    return {
        "card_center": (170.0 + float(rng.uniform(-25, 25)),
                        15.0 + float(rng.uniform(-25, 25))),
        "card_angle_deg": float(rng.uniform(-40, 40)),
        "az_deg": float(rng.uniform(255, 275)),
        "tilt_deg": float(rng.uniform(30, 45)),
        "dist_mm": float(460.0 * rng.uniform(0.94, 1.06)),
        "scene_seed": int(rng.integers(1, 10**6)),
    }


def _vessel(kind: str) -> dict:
    """plate / bowl / an effectively-invisible vessel (card on empty table)."""
    if kind == "none":
        return dict(kind="plate", r_in=1e-6, r_out=1e-6, floor=0.0, rim=0.0,
                    color=(166, 161, 154))
    return dict(VESSELS[kind])


def render_group_scene(group: str, level, scene_idx: int, seed: int) -> dict:
    """Render one scene for a render-level group (GT comes from the render)."""
    var = scene_variation(scene_idx, seed)
    cfg: dict = default_scene()
    cfg["seed"] = var["scene_seed"]
    cfg["food"]["seed"] = var["scene_seed"]
    cfg["anchor"]["card_center"] = var["card_center"]
    cfg["anchor"]["card_angle_deg"] = var["card_angle_deg"]

    tilt, dist = var["tilt_deg"], var["dist_mm"]
    if group == "card_tilt_deg":
        tilt = float(level)
    elif group == "card_distance_px":
        tilt, dist = DIST_TILT_DEG, DIST_MM_BY_PX[int(level)]
    elif group == "plate_food":
        if level == "none":
            cfg["vessel"] = _vessel("none")
            cfg["food"]["radius_mm"] = 1e-6
        elif level == "plate_only":
            cfg["vessel"] = _vessel("plate")
            cfg["food"]["radius_mm"] = 1e-6
    cfg["camera"] = camera_for(tilt, var["az_deg"], dist, var["card_center"])
    return render_scene(cfg)


_BASE_CACHE: dict[tuple[int, int], dict] = {}


def base_scene(scene_idx: int, seed: int) -> dict:
    """Shared plate+food scene used by every post-processing group."""
    key = (seed, scene_idx)
    if key not in _BASE_CACHE:
        _BASE_CACHE.clear() if len(_BASE_CACHE) > 512 else None
        _BASE_CACHE[key] = render_group_scene("plate_food", "plate+food",
                                               scene_idx, seed)
    return _BASE_CACHE[key]


# ------------------------------------------------------------ perturbations --
def _marker_mask(shape, quad: np.ndarray) -> np.ndarray:
    m = np.zeros(shape, dtype=np.uint8)
    poly = np.round(np.asarray(quad)).astype(np.int32)
    cv2.fillPoly(m, [poly], 1)
    return m > 0


def _occlusion(img: np.ndarray, gt: dict, pct: int, rng) -> np.ndarray:
    """Paint table-coloured pixels over exactly `pct`% of the marker area."""
    if pct <= 0:
        return img
    quad = np.asarray(gt["marker_corners_px"], dtype=np.float64)
    m = _marker_mask(img.shape[:2], quad)
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        return img
    ang = float(rng.uniform(0.0, 2.0 * np.pi))
    d = np.array([np.cos(ang), np.sin(ang)])
    order = np.argsort(xs * d[0] + ys * d[1])
    k = int(round(pct / 100.0 * len(order)))
    dil = cv2.dilate(m.astype(np.uint8), np.ones((9, 9), np.uint8))
    ring = (dil > 0) & ~m
    col = (np.median(img[ring], axis=0) if ring.any()
           else np.array([166.0, 161.0, 154.0]))
    out = img.copy()
    out[ys[order[:k]], xs[order[:k]]] = col.astype(np.uint8)
    return out


def _glare(img: np.ndarray, gt: dict, level: str, rng) -> np.ndarray:
    if level == "none":
        return img
    n, r_frac, amp = GLARE_SPEC[level]
    quad = np.asarray(gt["marker_corners_px"], dtype=np.float64)
    centre = quad.mean(axis=0)
    span = quad.max(axis=0) - quad.min(axis=0)
    side = float(gt["marker_side_px"])
    out = img.astype(np.float32)
    for _ in range(n):
        cx = float(np.clip(centre[0] + rng.uniform(-0.9, 0.9) * span[0],
                           0, img.shape[1] - 1))
        cy = float(np.clip(centre[1] + rng.uniform(-0.9, 0.9) * span[1],
                           0, img.shape[0] - 1))
        r = max(6.0, side * r_frac * float(rng.uniform(0.8, 1.2)))
        axes = (int(r), int(r * float(rng.uniform(0.5, 1.0))))
        ang = float(rng.uniform(0, 180))
        m = np.zeros(img.shape[:2], np.float32)
        cv2.ellipse(m, (int(cx), int(cy)), axes, ang, 0, 360, 1.0, -1)
        m = cv2.GaussianBlur(m, (0, 0), max(3.0, 0.45 * r))
        out += (amp * 255.0) * m[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def _dim_light(img: np.ndarray, level: str) -> np.ndarray:
    exposure, gamma = DIM_LIGHT[level]
    x = np.clip(img.astype(np.float32) / 255.0, 0.0, 1.0) ** gamma * exposure
    return np.clip(x * 255.0, 0, 255).astype(np.uint8)


def _blur(img: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return img
    return cv2.GaussianBlur(img, (0, 0), sigma)


def _jpeg(img: np.ndarray, level: str) -> np.ndarray:
    if level == "none":
        return img
    q = 30 if level == "q30" else 95
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), q])
    dec = cv2.imdecode(buf, cv2.IMREAD_COLOR) if ok else None
    return dec if isinstance(dec, np.ndarray) else img


def _low_res(img: np.ndarray, scale: float) -> np.ndarray:
    if scale >= 1.0:
        return img
    h, w = img.shape[:2]
    small = cv2.resize(img, (max(8, int(w * scale)), max(8, int(h * scale))),
                       interpolation=cv2.INTER_AREA)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)


def perturb(group: str, level, scene_idx: int, seed: int,
            img: np.ndarray, gt: dict) -> np.ndarray:
    """Post-processing perturbation (GT is unchanged by construction)."""
    # stable per-group index: str hash() is process-randomised (breaks determinism)
    g_idx = list(GROUPS).index(group)
    rng = np.random.default_rng(np.random.SeedSequence([seed, scene_idx, g_idx]))
    if group == "marker_occlusion_pct":
        return _occlusion(img, gt, int(level), rng)
    if group == "glare":
        return _glare(img, gt, str(level), rng)
    if group == "dim_light":
        return _dim_light(img, str(level))
    if group == "gaussian_blur":
        return _blur(img, float(level))
    if group == "jpeg":
        return _jpeg(img, str(level))
    if group == "low_resolution":
        return _low_res(img, float(level))
    raise ValueError(f"unknown perturbation group: {group}")


# ----------------------------------------------------------------- scoring --
def score_detection(gt: dict, est: dict) -> dict:
    """Pure per-scene score: detection, errors, and the false-accept flag.

    A FALSE ACCEPT is a detection that returned a scale more than 5% away
    from the renderer's planted cm_per_px. Misses are not false accepts.
    """
    gt_cm = float(gt["cm_per_px"])
    gt_tilt = gt.get("tilt_deg")
    detected = est.get("method") == "card_aruco" and est.get("cm_per_px")
    detected = bool(detected)
    rel_err = None
    tilt_err = None
    tilt_nan = False
    false_accept = False
    if detected:
        rel_err = abs(float(est["cm_per_px"]) / gt_cm - 1.0)
        false_accept = bool(rel_err > FALSE_ACCEPT_REL)
        est_tilt = est.get("tilt_deg")
        if est_tilt is not None and gt_tilt is not None:
            if np.isfinite(float(est_tilt)) and np.isfinite(float(gt_tilt)):
                tilt_err = abs(float(est_tilt) - float(gt_tilt))
            else:
                tilt_nan = True   # pose returned a non-finite tilt (counted, not imputed)
    return {"detected": detected, "cm_rel_err": rel_err,
            "tilt_err_deg": tilt_err, "tilt_nan": tilt_nan,
            "false_accept": false_accept}


def _percentile_ci(values: list[float]) -> list[float | None]:
    if not values:
        return [None, None]
    arr = np.sort(np.asarray(values, dtype=np.float64))
    return [float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))]


def _point(records: list[dict]) -> dict:
    n = len(records)
    det = [r for r in records if r["detected"]]
    rel = [r["cm_rel_err"] for r in det if r["cm_rel_err"] is not None]
    tilt = [r["tilt_err_deg"] for r in det if r["tilt_err_deg"] is not None]
    return {
        "detection_rate": (len(det) / n) if n else None,
        "false_accept_rate": (sum(r["false_accept"] for r in records) / n) if n else None,
        "cm_rel_err_median": float(np.median(rel)) if rel else None,
        "cm_rel_err_mean": float(np.mean(rel)) if rel else None,
        "tilt_err_deg_median": float(np.median(tilt)) if tilt else None,
        "n_detected": len(det),
        "n_false_accept": int(sum(r["false_accept"] for r in records)),
        "n_tilt_nan": int(sum(1 for r in records if r.get("tilt_nan"))),
    }


def summarize_level(group: str, level, records: list[dict], reps: int,
                    seed: int) -> dict:
    """Point estimates + scene-bootstrap 95% CIs for one perturbation level."""
    n = len(records)
    point = _point(records)
    rng = np.random.default_rng(
        np.random.SeedSequence([seed, 7, list(GROUPS).index(group)]))
    keys = ["detection_rate", "false_accept_rate", "cm_rel_err_median",
            "cm_rel_err_mean", "tilt_err_deg_median"]
    draws: dict[str, list[float]] = {k: [] for k in keys}
    for _ in range(reps):
        idx = rng.integers(0, n, size=n) if n else np.array([], dtype=int)
        sample = [records[int(j)] for j in idx]
        p = _point(sample)
        for k in keys:
            if p[k] is not None:
                draws[k].append(float(p[k]))
    summary = {
        "group": group,
        "level": level if isinstance(level, (int, float)) else str(level),
        "label": LABEL,
        "n_scenes": n,
        **point,
    }
    for k in keys:
        summary[f"{k}_ci95"] = _percentile_ci(draws[k])
    return summary


# ------------------------------------------------------- group orchestration --
def _scene_records(group: str, level, scenes: int, seed: int,
                   with_portion: bool) -> tuple[list[dict], list[dict]]:
    """Render/perturb + detect for one level. Returns (records, portion rows)."""
    records: list[dict] = []
    portion_rows: list[dict] = []
    kind = GROUPS[group]["kind"]
    for i in range(scenes):
        if kind == "render":
            scene = render_group_scene(group, level, i, seed)
            img, gt = scene["image_bgr"], scene["anchor_gt"]
        else:
            scene = base_scene(i, seed)
            gt = scene["anchor_gt"]
            img = perturb(group, level, i, seed, scene["image_bgr"], gt)
        est = estimate_anchor(img)
        rec = score_detection(gt, est)
        rec["gt_tilt_deg"] = float(gt["tilt_deg"])
        rec["marker_side_px"] = float(gt["marker_side_px"])
        records.append(rec)
        if with_portion and group == "card_tilt_deg" and rec["detected"]:
            portion_rows.append(_portion_row(img, scene, est, i))
    return records, portion_rows


def _portion_row(img, scene, est, scene_idx: int) -> dict:
    dish = load_menu()["dishes"]["rice_sambar"]
    res = estimate_portion(img, scene["mask_food"], scene["depth_m"], est,
                           {"K": scene["camera"]["K"]}, dish)
    gt_g = float(scene["grams_gt_total"])
    density = float(scene["cfg"]["food"]["density_g_ml"])
    gt_ml = gt_g / density if density else None
    g = float(res["grams"])
    ml = float(res.get("volume_ml") or float("nan"))
    gram_err = (g - gt_g) / gt_g if (np.isfinite(g) and gt_g > 0) else None
    vol_err = ((ml - gt_ml) / gt_ml
               if (np.isfinite(ml) and gt_ml is not None and gt_ml > 0)
               else None)
    return {"scene_idx": scene_idx,
            "grams": g if gram_err is not None else None, "grams_gt": gt_g,
            "rel_err": gram_err,
            "volume_ml": ml if vol_err is not None else None,
            "volume_gt_ml": gt_ml,
            "vol_rel_err": vol_err,
            "base_method": res.get("base_method")}


def _dist(vals: np.ndarray, signed: np.ndarray, rows: list[dict],
          reps: int, rng) -> dict:
    """Bootstrap median/p90/worst CIs over |rel err| for one metric."""
    if vals.size == 0:
        return {"n": 0}
    med, p90, worst = [], [], []
    for _ in range(reps):
        s = vals[rng.integers(0, vals.size, size=vals.size)]
        med.append(float(np.median(s)))
        p90.append(float(np.percentile(s, 90)))
        worst.append(float(np.max(s)))
    worst_i = int(np.argmax(vals))
    return {
        "n": int(vals.size),
        "median_abs_rel_err": float(np.median(vals)),
        "median_ci95": _percentile_ci(med),
        "p90_abs_rel_err": float(np.percentile(vals, 90)),
        "p90_ci95": _percentile_ci(p90),
        "worst_abs_rel_err": float(np.max(vals)),
        "worst_ci95": _percentile_ci(worst),
        "worst_scene_idx": int(rows[worst_i]["scene_idx"]),
        "signed_median": float(np.median(signed)),
    }


def _portion_summary(rows: list[dict], reps: int, seed: int) -> dict:
    """Two distributions: volume (the +/-7% claim) and grams (product).

    Non-finite estimates are excluded from the distributions and counted
    in n_nan rather than imputed or zero-filled.
    """
    rng = np.random.default_rng(np.random.SeedSequence([seed, 11]))
    v_rows = [r for r in rows if r["vol_rel_err"] is not None]
    g_rows = [r for r in rows if r["rel_err"] is not None]
    n_nan = len(rows) - max(len(v_rows), len(g_rows))
    if not v_rows and not g_rows:
        return {"n": 0, "n_nan": int(n_nan), "label": LABEL}
    return {
        "n_scenes": int(len(rows)),
        "n_nan": int(n_nan),
        "volume": _dist(
            np.array([abs(r["vol_rel_err"]) for r in v_rows]),
            np.array([r["vol_rel_err"] for r in v_rows]), v_rows,
            reps, rng),
        "grams": _dist(
            np.array([abs(r["rel_err"]) for r in g_rows]),
            np.array([r["rel_err"] for r in g_rows]), g_rows,
            reps, rng),
        "note": ("volume is the +/-7% claim metric; grams includes the "
                 "constant dish-density convention bias (rho_eff vs render "
                 "density), so grams are systematically lower"),
        "label": LABEL,
    }


def _first_below_95(level_summaries: list[dict]) -> dict:
    out: dict = {}
    for g in GROUPS:
        rows = [s for s in level_summaries if s["group"] == g]
        out[g] = None
        for s in rows:
            rate = s["detection_rate"]
            if rate is not None and rate < DETECT_LEVEL:
                out[g] = {"level": s["level"], "detection_rate": rate}
                break
    return out


def _weakest(level_summaries: list[dict], k: int = 3) -> list[dict]:
    ordered = sorted(level_summaries,
                     key=lambda s: (s["detection_rate"] if s["detection_rate"] is not None else 1.0,
                                   -(s["false_accept_rate"] or 0.0)))
    return [{"group": s["group"], "level": s["level"],
             "detection_rate": s["detection_rate"],
             "false_accept_rate": s["false_accept_rate"],
             "cm_rel_err_median": s["cm_rel_err_median"]} for s in ordered[:k]]


def run_suite(scenes: int = DEFAULT_SCENES, seed: int = DEFAULT_SEED,
              reps: int = DEFAULT_REPS, groups: list[str] | None = None,
              include_portion: bool = True) -> dict:
    """Run the whole suite. Same (scenes, seed, reps, groups) -> same output."""
    groups = list(groups) if groups else list(GROUPS)
    for g in groups:
        if g not in GROUPS:
            raise ValueError(f"unknown group {g!r}; known: {sorted(GROUPS)}")
    t0 = time.time()
    level_summaries: list[dict] = []
    portion_by_level: list[dict] = []
    for g in groups:
        for level in GROUPS[g]["levels"]:
            records, portion_rows = _scene_records(
                g, level, scenes, seed, include_portion and g == "card_tilt_deg")
            summary = summarize_level(g, level, records, reps, seed)
            summary["mean_gt_tilt_deg"] = float(
                np.mean([r["gt_tilt_deg"] for r in records]))
            summary["mean_marker_side_px"] = float(
                np.mean([r["marker_side_px"] for r in records]))
            level_summaries.append(summary)
            if portion_rows:
                portion_by_level.append({
                    "group": g, "level": level,
                    **_portion_summary(portion_rows, reps, seed)})
            print(f"[{g}] level={level} n={len(records)} "
                  f"det={summary['detection_rate']} "
                  f"fa={summary['false_accept_rate']}", flush=True)
    report = {
        "label": LABEL,
        "note": "All numbers below are " + LABEL + ".",
        "tool": "tools/card_stress.py",
        "created": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git": _git("rev-parse", "--short", "HEAD"),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "config": {"scenes_per_level": scenes, "seed": seed,
                   "bootstrap_reps": reps, "false_accept_threshold": 0.05,
                   "detect_threshold": DETECT_LEVEL,
                   "groups": groups, "portion_by_tilt": bool(include_portion)},
        "levels": level_summaries,
        "first_below_95": _first_below_95(level_summaries),
        "weakest_three": _weakest(level_summaries),
        "portion_by_tilt": portion_by_level,
        "wall_s": round(time.time() - t0, 2),
    }
    return report


def _git(*args: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=_ROOT, text=True,
                                       timeout=10).strip()
    except Exception:
        return "unknown"


def _jsonable(obj):
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenes", type=int, default=DEFAULT_SCENES,
                    help=f"seeded scenes per level (default {DEFAULT_SCENES})")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--reps", type=int, default=DEFAULT_REPS,
                    help="bootstrap replicates (default 2000)")
    ap.add_argument("--groups", default=None,
                    help="comma-separated group subset (default all)")
    ap.add_argument("--no-portion", action="store_true",
                    help="skip the card-path portion-error stats")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)
    groups = [g.strip() for g in args.groups.split(",")] if args.groups else None
    try:
        report = run_suite(scenes=args.scenes, seed=args.seed, reps=args.reps,
                           groups=groups,
                           include_portion=not args.no_portion)
    except ValueError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(_jsonable(report), indent=1, sort_keys=True) + "\n")
    print(f"wrote {args.out} ({len(report['levels'])} levels, "
          f"wall_s={report['wall_s']})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
