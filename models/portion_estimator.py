"""S3: portion estimation.

Plan v5 geometry: grams = footprint_area (scale from the anchor tier)
    x mean_height_above_base (from metric depth), then x effective density.

Footprint area uses the S1 anchor scale (card/coin) with a cos(tilt)
de-foreshortening; with no anchor it falls back to an assumed food-diameter
size prior (label= prior -> never PASS/FAIL upstream).

Base plane:
  ring path       — fit to a narrow band just INSIDE the food mask edge
                    (food surface meets its base at the boundary); robust
                    two-pass plane fit (lower residual quantile). Preferred.
  table_prior path — fit background pixels to the table plane, then lift by
                    the vessel-floor prior (base_prior_height_mm). Flagged
                    vessel_shape_uncertain, lowers coverage in S5.

Returns point estimates plus `sigma_rel` (named relative sigmas) — ALL
intervals are owned by the MC engine (S4), never drawn here.
"""
from pathlib import Path

import cv2
import numpy as np
import yaml

from geo.plane import fit_plane, plane_residuals

_PARAMS_PATH = Path(__file__).resolve().parents[1] / "data" / "params_status.yaml"
_PARAMS_CACHE = None

_Z = 1.645  # 90% two-sided


def load_params(path=None):
    global _PARAMS_CACHE
    if path is None and _PARAMS_CACHE is not None:
        return _PARAMS_CACHE["params"]
    with open(path or _PARAMS_PATH) as f:
        data = yaml.safe_load(f)
    params = data["params"]
    if path is None:
        _PARAMS_CACHE = {"params": params}
    return params


def _p(params, key, field="value"):
    return params[key][field]


def _fill_depth(z):
    z = np.asarray(z, dtype=np.float64)
    bad = ~np.isfinite(z) | (z <= 0)
    if bad.all():
        raise ValueError("no valid depth under region")
    if bad.any():
        z = z.copy()
        z[bad] = np.median(z[~bad])
    return z


def _unproject(us, vs, z, K):
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    return np.stack([(us - cx) / fx * z, (vs - cy) / fy * z, z], axis=1)


def _fit_base_ring(depth, mask, K, params, cfg):
    """Two-pass robust plane fit to the band just inside the mask edge."""
    H, W = mask.shape
    band = max(3, int(round(cfg.get("ring_band_pct", 1.5) / 100.0 * min(H, W))))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * band + 1, 2 * band + 1))
    core = cv2.erode(mask.astype(np.uint8), kernel) > 0
    ring = mask & ~core
    if int(ring.sum()) < 300:
        return None, 0.0, "ring band too thin"
    rv, ru = np.nonzero(ring)
    rz = _fill_depth(depth[rv, ru])
    rpts = _unproject(ru, rv, rz, K)
    a, b, c, _ = fit_plane(rpts)
    res = plane_residuals(rpts, a, b, c)
    # camera-z decreases with food height, so LOWEST h = LARGEST residual
    keep = res >= np.quantile(res, 1.0 - cfg.get("ring_quantile", 0.15))
    if int(keep.sum()) < 200:
        return None, 0.0, "ring band too thin after robust pass"
    a, b, c, rms = fit_plane(rpts[keep])
    rms_mm = rms * 1000.0
    if rms_mm > cfg.get("ring_max_rms_mm", 5.0):
        return None, rms_mm, f"ring fit rms {rms_mm:.1f}mm > {cfg.get('ring_max_rms_mm', 5.0)}mm"
    sigma_mm = float(_p(params, "base_ring_sigma_mm"))
    return (float(a), float(b), float(c)), sigma_mm, "ring"


def _fit_base_table(depth, mask, K, params, cfg):
    """Table plane from an outside band (top residual quantile = far surface),
    then lift by the vessel-floor height prior."""
    H, W = mask.shape
    near = max(4, int(round(0.01 * min(H, W))))
    far = max(near + 4, int(round(0.06 * min(H, W))))
    k_near = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * near + 1, 2 * near + 1))
    k_far = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * far + 1, 2 * far + 1))
    band = (cv2.dilate(mask.astype(np.uint8), k_far) > 0) & \
           ~(cv2.dilate(mask.astype(np.uint8), k_near) > 0)
    if int(band.sum()) < 300:
        return None, 0.0, "background band too thin"
    bv, bu = np.nonzero(band)
    bz = _fill_depth(depth[bv, bu])
    bpts = _unproject(bu, bv, bz, K)
    a, b, c, _ = fit_plane(bpts)
    res = plane_residuals(bpts, a, b, c)
    q = np.quantile(res, 0.75)
    win = (res >= q - 0.010) & (res <= q)  # farthest surface within 10mm window
    if int(win.sum()) < 200:
        return None, 0.0, "background band too thin after robust pass"
    a, b, c, rms = fit_plane(bpts[win])
    nrm = float(np.sqrt(a * a + b * b + 1.0))
    delta_m = _p(params, "base_prior_height_mm") / 1000.0
    c = float(c) - delta_m * nrm  # food base sits ABOVE the table -> closer to camera
    sigma_mm = float(_p(params, "base_prior_sigma_mm"))
    return (float(a), float(b), float(c)), sigma_mm, f"table_prior (rms {rms * 1000:.1f}mm)"


def _footprint_scale(mask, anchor, params):
    """(cm_per_px, relative sigma, tilt_deg, tilt sigma deg) for the anchor tier."""
    tier = anchor.get("label", "prior")
    if tier == "measured" and anchor.get("cm_per_px"):
        cm_px = float(anchor["cm_per_px"])
        iv = anchor.get("interval")
        rel = (iv[1] - iv[0]) / (2.0 * _Z) / cm_px if iv else 0.01
        tilt = anchor.get("tilt_deg")
        if tilt is None:
            tilt = float(_p(params, "prior_tilt_deg"))
            tilt_sigma_deg = 8.66  # uniform [15, 45]
        else:
            tilt = float(tilt)
            tilt_sigma_deg = float(_p(params, "pose_tilt_residue_pct"))
        return cm_px, rel, tilt, tilt_sigma_deg, tier

    # prior tier: assumed food-diameter size prior on the mask minor axis
    diam_mm = float(_p(params, "size_prior_food_diameter_mm"))
    lo, hi = params["size_prior_food_diameter_mm"]["interval"]
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    diam_px = None
    if contours:
        cnt = max(contours, key=cv2.contourArea)
        if len(cnt) >= 5:
            try:
                (_, _), (ma, mb), _ = cv2.fitEllipse(cnt)
                diam_px = float(min(ma, mb))
            except cv2.error:
                diam_px = None
    if not diam_px or diam_px <= 1:
        diam_px = float(np.sqrt(4.0 * mask.sum() / np.pi))
    tilt_deg = float(_p(params, "prior_tilt_deg"))
    # minor axis is foreshortened by the (assumed) tilt
    cm_px = (diam_mm / 10.0) * np.cos(np.radians(tilt_deg)) / diam_px
    rel = (hi - lo) / 2.0 / np.sqrt(3.0) / diam_mm  # uniform interval sigma
    return cm_px, rel, tilt_deg, 8.66, tier


def _components(dish):
    if dish is None:
        raise ValueError("dish components required")
    comps = dish["components"] if "components" in dish else dish
    shares = {}
    for name, spec in comps.items():
        shares[name] = float(spec.get("share", 1.0))
    total = sum(shares.values())
    shares = {k: v / total for k, v in shares.items()}
    dens = {}
    for name, spec in comps.items():
        if "density_g_ml" not in spec:
            raise ValueError(f"component {name} missing density_g_ml")
        dens[name] = float(spec["density_g_ml"])
    rho_eff = 1.0 / sum(shares[n] / dens[n] for n in shares)
    return shares, dens, rho_eff


def estimate_portion(image_bgr, mask, depth_m, anchor, camera, dish,
                     params=None, cfg=None):
    """Estimate cooked-plate grams for one food region.

    mask: bool (H, W) food region.  depth_m: metric camera-z depth (H, W) in
    meters.  anchor: S1 estimate_anchor() dict.  camera: {"K": 3x3} or 3x3.
    dish: menu dish dict (components with share + density_g_ml).
    """
    params = params if params is not None else load_params()
    cfg = cfg or {}
    mask = np.asarray(mask, dtype=bool)
    depth = np.asarray(depth_m, dtype=np.float64)
    if mask.shape != depth.shape:
        raise ValueError(f"mask {mask.shape} / depth {depth.shape} shape mismatch")
    if int(mask.sum()) < 64:
        raise ValueError("food mask too small")
    K = camera["K"] if isinstance(camera, dict) else np.asarray(camera, dtype=np.float64)

    flags = []
    vs, us = np.nonzero(mask)
    z_all = depth[vs, us]
    invalid_frac = float(np.mean(~np.isfinite(z_all) | (z_all <= 0)))
    if invalid_frac > 0.05:
        flags.append("depth_partial")
    z = _fill_depth(z_all)
    pts = _unproject(us, vs, z, K)

    # --- base plane -------------------------------------------------------
    base, sigma_base_mm, method = None, 0.0, "table_prior"
    if cfg.get("base_method", "auto") in ("auto", "ring"):
        base, sigma_base_mm, method = _fit_base_ring(depth, mask, K, params, cfg)
    if base is None and cfg.get("base_method", "auto") in ("auto", "table_prior"):
        base, sigma_base_mm, why = _fit_base_table(depth, mask, K, params, cfg)
        if base is None:
            raise ValueError(f"base plane fit failed: {why}")
        method = "table_prior"
        flags.append("vessel_shape_uncertain")
    elif method == "ring":
        pass
    else:
        raise ValueError(f"ring base fit failed: {method}")

    a, b, c = base
    nrm = float(np.sqrt(a * a + b * b + 1.0))
    h_cam = (a * pts[:, 0] + b * pts[:, 1] + c) - pts[:, 2]  # base minus food (camera looks down)
    if float(np.median(h_cam)) < 0:
        h_cam = -h_cam
        flags.append("base_sign_flip")
    h_mm = np.clip(h_cam, 0.0, None) / nrm * 1000.0
    mean_h_mm = float(h_mm.mean())
    if mean_h_mm < 3.0:
        flags.append("thin_layer")

    # --- footprint area ---------------------------------------------------
    cm_px, scale_rel, tilt, tilt_sigma_deg, tier = _footprint_scale(mask, anchor, params)
    tilt_rad = np.radians(tilt)
    tilt_rel = np.tan(tilt_rad) * np.radians(tilt_sigma_deg)
    seg_rel = _p(params, "seg_area_sigma_pct") / 100.0
    area_rel = float(np.hypot(scale_rel, np.hypot(seg_rel, tilt_rel)))
    # mean-side cm/px under-foreshortens: p = L(1+cos)/(2M); A_tab = A_img/p^2/cos
    de_foreshorten = ((1.0 + np.cos(tilt_rad)) / 2.0) ** 2 / np.cos(tilt_rad)
    area_cm2 = float(mask.sum()) * cm_px * cm_px * de_foreshorten
    if tier == "prior":
        flags.append("size_prior_scale")

    # --- volume -> grams --------------------------------------------------
    volume_ml = area_cm2 * mean_h_mm / 10.0  # cm^2 * mm / 10 = cm^3 = ml
    shares, dens, rho_eff = _components(dish)
    grams = volume_ml * rho_eff
    components_g = {name: shares[name] * grams for name in shares}

    sigma_rel = {
        "depth": float(np.hypot(_p(params, "depth_scale_sigma_pct"),
                                _p(params, "thickness_depth_sigma_pct"))) / 100.0,
        "area": area_rel,
        "base": min(1.0, sigma_base_mm / max(mean_h_mm, 1.0)),
        "density": _p(params, "density_sigma_pct") / 100.0,
    }
    sigma_grams_rel = float(np.sqrt(sum(v * v for v in sigma_rel.values())))

    return {
        "grams": float(grams),
        "volume_ml": float(volume_ml),
        "density_eff": float(rho_eff),
        "components_g": components_g,
        "mean_h_mm": mean_h_mm,
        "area_cm2": area_cm2,
        "cm_per_px": float(cm_px),
        "tilt_deg": float(tilt),
        "base_method": method,
        "base_sigma_mm": float(sigma_base_mm),
        "scale_tier": tier,
        "sigma_rel": sigma_rel,
        "sigma_grams_rel": sigma_grams_rel,
        "depth_invalid_frac": invalid_frac,
        "flags": flags,
    }
