"""S3: portion estimation.

Plan v5 geometry: grams = footprint_area (scale from the anchor tier)
    x mean_height_above_base (from metric depth), then x effective density.

Footprint area uses the S1 anchor scale (card) with a cos(tilt)
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
import cv2
import numpy as np

from config import load_params
from geo.plane import fit_plane, plane_residuals

_Z = 1.645  # 90% two-sided


def _p(params, key, field="value"):
    return params[key][field]


def _fill_depth(z):
    z = np.asarray(z, dtype=np.float64)
    bad = ~np.isfinite(z) | (z <= 0)
    if bad.all():
        raise ValueError("no valid depth under region")
    if float(bad.mean()) > 0.05:
        raise ValueError("more than 5% of geometry samples have invalid depth")
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
    exclude_mask = cfg.get("exclude_mask")
    if exclude_mask is not None:
        filtered = band & ~np.asarray(exclude_mask, dtype=bool)
        if int(filtered.sum()) >= 300:
            band = filtered
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


def _fit_base_tabletop_annulus(depth, plate_mask, K, cfg):
    """Fit a robust plane to the tabletop surface in an annular zone 1.5 - 5.5 cm outside the plate boundary."""
    cm_px = float(cfg.get("cm_per_px") or 0.05)
    near = max(6, int(round(1.5 / cm_px)))
    far = max(near + 10, int(round(5.5 / cm_px)))
    k_near = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * near + 1, 2 * near + 1))
    k_far = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * far + 1, 2 * far + 1))
    plate_u8 = np.asarray(plate_mask, dtype=np.uint8)
    annulus = (cv2.dilate(plate_u8, k_far) > 0) & ~(cv2.dilate(plate_u8, k_near) > 0)
    annulus = annulus & ~np.asarray(plate_mask, dtype=bool)
    exclude_mask = cfg.get("exclude_mask")
    if exclude_mask is not None:
        annulus = annulus & ~np.asarray(exclude_mask, dtype=bool)

    border = 10
    annulus[:border, :] = False
    annulus[-border:, :] = False
    annulus[:, :border] = False
    annulus[:, -border:] = False

    bv, bu = np.nonzero(annulus)
    if len(bu) < 150:
        return None, 0.0, "tabletop annulus too small"
    bz = depth[bv, bu]
    valid = np.isfinite(bz) & (bz > 0.05) & (bz < 3.0)
    if int(valid.sum()) < 100:
        return None, 0.0, "invalid depth in tabletop annulus"
    bv, bu, bz = bv[valid], bu[valid], bz[valid]

    p15, p85 = np.percentile(bz, [15, 85])
    in_range = (bz >= p15) & (bz <= p85)
    if int(in_range.sum()) >= 60:
        bv, bu, bz = bv[in_range], bu[in_range], bz[in_range]

    if len(bu) > 3000:
        step = len(bu) // 3000
        bu, bv, bz = bu[::step], bv[::step], bz[::step]

    bpts = _unproject(bu, bv, bz, K)
    a, b, c, rms = fit_plane(bpts)
    res = plane_residuals(bpts, a, b, c)
    q = np.quantile(res, 0.70)
    win = (res >= q - 0.015) & (res <= q)
    if int(win.sum()) >= 40:
        a, b, c, rms = fit_plane(bpts[win])

    nrm = float(np.sqrt(a * a + b * b + 1.0))
    # Plate tare thickness: standard stainless steel / ceramic thali bottom is ~3.5 mm thick
    tare_thickness_m = 0.0035
    c_plate = float(c) - tare_thickness_m * nrm
    sigma_mm = float(rms * 1000.0)
    return (float(a), float(b), float(c_plate)), sigma_mm, f"tabletop_annulus (rms {rms * 1000:.1f}mm)"


def _fit_base_card(depth, anchor, K, params):
    """Fit base plane directly to the measured ArUco card on the table."""
    if (anchor or {}).get("label") != "measured":
        return None, 0.0, "anchor not measured"
    corners = (anchor.get("extras") or {}).get("marker_corners_px")
    if corners is None or len(corners) < 4:
        return None, 0.0, "no marker corners"
    corners_arr = np.asarray(corners, dtype=np.float64).reshape(4, 2)
    H, W = depth.shape[:2]
    centroid = np.mean(corners_arr, axis=0)
    expanded_corners = centroid + 1.15 * (corners_arr - centroid)
    poly = np.zeros((H, W), dtype=np.uint8)
    cv2.fillConvexPoly(poly, np.round(expanded_corners).astype(np.int32), 1)
    v, u = np.nonzero(poly)
    if len(u) < 30:
        poly = np.zeros((H, W), dtype=np.uint8)
        cv2.fillConvexPoly(poly, np.round(corners_arr).astype(np.int32), 1)
        v, u = np.nonzero(poly)
    if len(u) < 30:
        return None, 0.0, "marker mask too small"
    step = max(1, len(u) // 5000)
    v, u = v[::step], u[::step]
    z = depth[v, u]
    valid = np.isfinite(z) & (z > 0.05) & (z < 3.0)
    if int(valid.sum()) < 20:
        return None, 0.0, "marker depth points invalid"
    v, u, z = v[valid], u[valid], z[valid]
    cpts = _unproject(u, v, z, K)
    a, b, c, rms = fit_plane(cpts)
    rms_mm = rms * 1000.0
    if rms_mm > 20.0:
        return None, rms_mm, f"marker plane rms {rms_mm:.1f}mm too high"
    nrm = float(np.sqrt(a * a + b * b + 1.0))
    delta_m = _p(params, "base_prior_height_mm") / 1000.0
    c = float(c) - delta_m * nrm
    sigma_mm = max(float(rms_mm), float(_p(params, "base_prior_sigma_mm")))
    return (float(a), float(b), float(c)), sigma_mm, f"table_card (rms {rms_mm:.1f}mm)"


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


def _homography_footprint_area_cm2(mask, H, fallback_area):
    """Integrate local planar area under H^-1 (mm^2 -> cm^2) across mask pixels."""
    try:
        H_arr = np.asarray(H, dtype=np.float64)
        if H_arr.shape != (3, 3):
            return fallback_area
        inv_H = np.linalg.inv(H_arr)
        det = abs(float(np.linalg.det(inv_H)))
    except np.linalg.LinAlgError:
        return fallback_area
    if not np.isfinite(det) or det <= 0.0:
        return fallback_area
    vs, us = np.nonzero(mask)
    w = inv_H[2, 0] * us + inv_H[2, 1] * vs + inv_H[2, 2]
    if np.any(w <= 1e-4):
        return fallback_area
    area_cm2 = float(np.sum(det / (w ** 3))) / 100.0
    if not np.isfinite(area_cm2) or not (0.25 * fallback_area <= area_cm2 <= 4.0 * fallback_area):
        return fallback_area
    return area_cm2


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
        raise ValueError(
            f"food-region depth invalid fraction {invalid_frac:.1%} exceeds 5%")
    if invalid_frac > 0:
        flags.append("depth_partial")
    z = _fill_depth(z_all)
    pts = _unproject(us, vs, z, K)

    # --- base plane -------------------------------------------------------
    base, sigma_base_mm, method = None, 0.0, "table_prior"
    card_fitted = False
    if cfg.get("base_method", "auto") in ("auto", "ring"):
        base, sigma_base_mm, method = _fit_base_ring(depth, mask, K, params, cfg)
    if base is None and cfg.get("base_method", "auto") in ("auto", "table_prior"):
        if (anchor or {}).get("label") == "measured" and (anchor.get("extras") or {}).get("marker_corners_px"):
            base, sigma_base_mm, _ = _fit_base_card(depth, anchor, K, params)
            if base is not None:
                card_fitted = True
        if base is None and cfg.get("parent_mask") is not None:
            base, sigma_base_mm, _ = _fit_base_tabletop_annulus(depth, cfg["parent_mask"], K, cfg)
            if base is not None:
                card_fitted = True
        if base is None:
            base, sigma_base_mm, why = _fit_base_table(depth, mask, K, params, cfg)
            if base is None:
                raise ValueError(f"base plane fit failed: {why}")
        method = "table_prior"
        flags.append("vessel_shape_uncertain")
    elif method == "ring":
        pass
    else:
        raise ValueError(f"ring base fit failed: {method}")

    if base is None:
        raise ValueError("base plane could not be determined")

    a, b, c = base
    nrm = float(np.sqrt(a * a + b * b + 1.0))
    h_cam = (a * pts[:, 0] + b * pts[:, 1] + c) - pts[:, 2]  # base minus food (camera looks down)
    if method == "table_prior":
        delta_m = _p(params, "base_prior_height_mm") / 1000.0
        h_raw = h_cam + delta_m * nrm
        raw_med = float(np.median(h_raw))
        if card_fitted:
            # Table plane anchored to ArUco card on table; deduct steel-plate floor thickness
            # Clamped so at least 65% of the food mound's median height above tabletop is preserved
            deduct = min(delta_m * nrm, 0.35 * max(raw_med, 0.0))
            if raw_med > 0.0:
                h_cam = h_raw - deduct
            else:
                h_cam = np.maximum(h_cam, 0.002 * nrm)
        else:
            if raw_med > 0.0:
                h_cam = h_raw - min(delta_m * nrm, 0.4 * raw_med)
            else:
                h_cam = np.maximum(h_cam, 0.002 * nrm)
    if float(np.median(h_cam)) < 0:
        h_cam = np.maximum(h_cam, 0.002 * nrm)
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
    if tier == "measured" and anchor.get("H") is not None:
        area_cm2 = _homography_footprint_area_cm2(mask, anchor["H"], area_cm2)
    if tier == "prior":
        flags.append("size_prior_scale")

    # --- volume -> grams --------------------------------------------------
    volume_ml = area_cm2 * mean_h_mm / 10.0  # cm^2 * mm / 10 = cm^3 = ml

    # Check for Indian liquid katori frustum (sambar, dal, rasam, curd, kootu)
    is_liquid_bowl = False
    dish_id = str(dish.get("id") or "").lower()
    dish_name = str(dish.get("display_name") or dish.get("name") or "").lower()
    if any(k in dish_id or k in dish_name for k in ["sambar", "dal", "rasam", "curd", "katori", "kootu", "liquid"]):
        is_liquid_bowl = True

    equiv_diam_cm = 2.0 * float(np.sqrt(max(area_cm2, 1e-4) / np.pi))
    if 6.0 <= equiv_diam_cm <= 13.5 and (is_liquid_bowl or mean_h_mm < 12.0):
        d_rim = equiv_diam_cm
        d_base = 0.72 * d_rim
        h_fill = 0.36 * d_rim
        v_frustum = (np.pi * h_fill / 12.0) * (d_rim * d_rim + d_rim * d_base + d_base * d_base)
        if v_frustum > volume_ml:
            volume_ml = float(v_frustum)
            mean_h_mm = max(mean_h_mm, float(h_fill * 10.0))
            flags.append("katori_frustum_inferred")

    shares, dens, rho_eff = _components(dish)
    grams = volume_ml * rho_eff

    # Scale-modulated prior fusion & downward clamping for Mode B
    implicit_mass = (anchor.get("extras") or {}).get("implicit_mass_g")
    if anchor.get("method") == "implicit_scale" and implicit_mass is not None:
        item_share = 1.0
        if cfg.get("parent_mask") is not None:
            parent_area = float(np.asarray(cfg["parent_mask"], dtype=bool).sum())
            if parent_area > 0:
                item_share = min(1.0, max(0.18, float(mask.sum()) / parent_area))
        target_item_mass = float(implicit_mass) * item_share
        if grams < 0.55 * target_item_mass:
            grams = 0.50 * grams + 0.50 * target_item_mass
            grams = max(grams, 0.60 * target_item_mass)
            volume_ml = grams / rho_eff
            flags.append("implicit_mass_fused")

    components_g = {name: shares[name] * grams for name in shares}

    sigma_rel = {
        "depth": float(np.hypot(_p(params, "depth_scale_sigma_pct"),
                                _p(params, "thickness_depth_sigma_pct"))) / 100.0,
        "area": area_rel,
        "base": min(1.0, sigma_base_mm / max(mean_h_mm, 1.0)),
        "density": _p(params, "density_sigma_pct") / 100.0,
    }
    sigma_rel["depth"] = float(np.hypot(sigma_rel["depth"], invalid_frac))
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
