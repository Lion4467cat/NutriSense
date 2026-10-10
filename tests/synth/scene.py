"""Full synthetic scene renderer (S0): pinhole camera over a table with a
vessel, a food height-field, and the reference card.

Produces image + ground truth for M-level tests:
  image_rgb / image_bgr   uint8 render
  depth_m                 metric camera-z depth (float32, metres)
  obj_ids                 0 table, 1 vessel, 2 card, 3 food
  comp_ids                0 none, 1..k food component zones
  grams_gt                true grams per component (integrated height field)
  anchor_gt               planted cm/px, marker corners, tilt (or None)
  camera                  K, R_wc, C, lookat (independent re-projection source)

World frame: X right, Y away, Z up (mm); table = Z 0 plane.
Camera: OpenCV (x right, y down, z forward), zero distortion.
Vessel lateral walls are not rendered (rim ring only) — v0 documented limit.
"""
import numpy as np
import cv2

from geo import camera_matrix
from tools.make_reference_card import build_card, card_layout

MATERIALS = {
    "rice":           {"base": (240, 236, 226), "amp": 0.16, "scale": 3.5},
    "sambar":         {"base": (176, 104, 46),  "amp": 0.22, "scale": 6.0},
    "vegetable_rice": {"base": (224, 186, 96),  "amp": 0.25, "scale": 4.0},
    "bisibelebath":   {"base": (168, 88, 44),   "amp": 0.24, "scale": 5.0},
    "curd":           {"base": (246, 246, 248), "amp": 0.06, "scale": 4.0},
    "veg_gravy":      {"base": (122, 134, 64),  "amp": 0.25, "scale": 5.0},
    "plain_rice":     {"base": (240, 236, 226), "amp": 0.16, "scale": 3.5},
}

VESSELS = {
    "plate": dict(kind="plate", r_in=95.0, r_out=106.0, floor=4.0, rim=12.0,
                  color=(244, 244, 246)),
    "bowl":  dict(kind="bowl",  r_in=78.0, r_out=86.0, floor=26.0, rim=45.0,
                  color=(198, 200, 205)),
}

CARD_MM = (105.0, 148.0)


def default_scene():
    return dict(
        size=(1400, 1100),
        camera=dict(pos=(0.0, -250.0, 360.0), target=(0.0, 40.0, 0.0),
                    focal_mm=4.0, sensor_width_mm=6.17),
        vessel="plate",
        food=dict(radius_mm=88.0, grams=450.0, density_g_ml=0.95, kappa=0.55,
                  layout="sectors", seed=11,
                  components=[{"name": "rice", "material": "rice", "share_g": 270.0},
                              {"name": "sambar", "material": "sambar", "share_g": 180.0}]),
        anchor=dict(card=True, card_center=(170.0, 15.0), card_angle_deg=10.0),
        table_color=(166, 161, 154),
        noise_sigma=2.5,
        seed=5,
    )


def _merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _lookat_R(pos, target):
    f = np.asarray(target, float) - np.asarray(pos, float)
    f /= np.linalg.norm(f)
    r = np.cross(f, [0.0, 0.0, 1.0])
    r /= np.linalg.norm(r)
    y = np.cross(f, r)
    return np.vstack([r, y, f])          # rows: cam x, cam y (down), cam z (fwd)


def _fbm(X, Y, cell=8.0, octaves=3, seed=0, extent=450.0):
    """Multi-octave value noise in world XY, returns [0,1]."""
    acc = np.zeros_like(X, dtype=np.float64)
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        rng = np.random.default_rng(seed + 101 * o)
        c = cell / (2 ** o)
        n = int(2 * extent / c) + 3
        G = rng.random((n, n))
        gx = (X + extent) / c
        gy = (Y + extent) / c
        i = np.clip(gx.astype(np.int64), 0, n - 2)
        j = np.clip(gy.astype(np.int64), 0, n - 2)
        fx = np.clip(gx - i, 0.0, 1.0)
        fy = np.clip(gy - j, 0.0, 1.0)
        fx = fx * fx * (3 - 2 * fx)
        fy = fy * fy * (3 - 2 * fy)
        v = (G[j, i] * (1 - fx) * (1 - fy) + G[j, i + 1] * fx * (1 - fy)
             + G[j + 1, i] * (1 - fx) * fy + G[j + 1, i + 1] * fx * fy)
        acc += amp * v
        norm += amp
        amp *= 0.5
    return acc / norm


def _kappa_n(kappa):
    """Profile exponent n for target fill factor kappa = n/(n+2)."""
    k = float(np.clip(kappa, 0.05, 0.97))
    return 2.0 * k / (1.0 - k)


def _h_profile(r, R, h_max, n):
    with np.errstate(invalid="ignore", divide="ignore"):
        t = np.clip(r / R, 0.0, 1.0)
        h = h_max * (1.0 - t ** n)
    return np.where(r <= R, h, 0.0)


def _h_max_from_grams(grams, density, radius_mm, kappa):
    vol_ml = grams / density
    area = np.pi * radius_mm ** 2
    h_avg = vol_ml * 1000.0 / area
    return h_avg / kappa, _kappa_n(kappa)


def _world_from_local(lx, ly, center, angle_rad):
    # Texture-down (+ly) must map to -Y: a face-up printed page seen from
    # +Z has R x D = -N. Mapping +ly to +Y mirrors the marker (aruco rejects).
    ca, sa = np.cos(angle_rad), np.sin(angle_rad)
    return center[0] + lx * ca + ly * sa, center[1] + lx * sa - ly * ca


def _local_from_world(X, Y, center, angle_rad):
    ca, sa = np.cos(angle_rad), np.sin(angle_rad)
    dx, dy = X - center[0], Y - center[1]
    return dx * ca + dy * sa, dx * sa - dy * ca


def _project(P, R_wc, C, K):
    Pc = (np.atleast_2d(P) - C) @ R_wc.T
    fx, cx, cy = K[0, 0], K[0, 2], K[1, 2]
    u = fx * Pc[:, 0] / Pc[:, 2] + cx
    v = fx * Pc[:, 1] / Pc[:, 2] + cy
    return np.stack([u, v], axis=1), Pc


def _integrate_grams(food, h_max, start_angle=0.0):
    """True grams per component from the analytic height field (1 mm grid)."""
    R = food["radius_mm"]
    n = _kappa_n(food["kappa"])
    xs = np.arange(-R, R + 1e-9, 1.0)
    X, Y = np.meshgrid(xs, xs)
    r = np.hypot(X, Y)
    h = _h_profile(r, R, 1.0, n)          # unit h_max profile
    comps = food["components"]
    ang = (np.arctan2(Y, X) - start_angle) % (2 * np.pi)
    total_shares = sum(c["share_g"] for c in comps)
    out, cum = {}, 0.0
    for c in comps:
        frac = c["share_g"] / total_shares
        lo, hi = 2 * np.pi * cum, 2 * np.pi * (cum + frac)
        cum += frac
        zone = (ang >= lo) & (ang < hi) if len(comps) > 1 else (r <= R)
        vol_mm3 = float(h[zone].sum()) * h_max   # profile * dA(1mm^2)
        out[c["name"]] = vol_mm3 * food["density_g_ml"] / 1000.0
    return out


def render_scene(cfg=None):
    cfg = _merge(default_scene(), cfg or {})
    W, H = cfg["size"]
    C = np.asarray(cfg["camera"]["pos"], dtype=np.float64)
    K = camera_matrix(cfg["camera"]["focal_mm"], cfg["camera"]["sensor_width_mm"], W, H)
    R_wc = _lookat_R(cfg["camera"]["pos"], cfg["camera"]["target"])
    fx, cx, cy = K[0, 0], K[0, 2], K[1, 2]

    # rays in world frame ---------------------------------------------------
    u, v = np.meshgrid(np.arange(W, dtype=np.float64), np.arange(H, dtype=np.float64))
    dir_cam = np.stack([(u - cx) / fx, (v - cy) / fx, np.ones_like(u)], axis=-1)
    dir_w = dir_cam @ R_wc                       # R^T applied per pixel
    dz = dir_w[..., 2]

    def lam_z(Z):
        return (np.asarray(Z, dtype=np.float64) - C[2]) / dz

    lam = {"table": lam_z(0.0)}
    obj_of = {}

    # card ------------------------------------------------------------------
    card_img = None
    card_ang = np.radians(cfg["anchor"]["card_angle_deg"])
    marker_gt = None
    if cfg["anchor"]["card"]:
        card_img = build_card(300).astype(np.float64)
        cw, ch = card_img.shape[1], card_img.shape[0]
        Lm = card_layout(300)
        ppm = 300.0 / 25.4
        c0 = cfg["anchor"]["card_center"]
        lx, ly = _local_from_world(dir_w * 0 + 0, 0, c0, card_ang)  # placeholder
        # local coords of hit points on table plane: use unit-lambda table hits
        P0 = C + lam["table"][..., None] * dir_w                    # table XY
        lxc, lyc = _local_from_world(P0[..., 0], P0[..., 1], c0, card_ang)
        half_w, half_h = CARD_MM[0] / 2.0, CARD_MM[1] / 2.0
        in_card = (np.abs(lxc) <= half_w) & (np.abs(lyc) <= half_h)
        lam["card"] = np.where(in_card, lam_z(0.6), np.inf)

        ui = np.clip(((lxc + half_w) / CARD_MM[0] * cw).astype(np.int64), 0, cw - 1)
        vi = np.clip(((lyc + half_h) / CARD_MM[1] * ch).astype(np.int64), 0, ch - 1)
        card_rgb = np.repeat(card_img[vi, ui][..., None], 3, axis=2)

        # planted marker GT
        mx0, my0, mx1, my1 = Lm["marker"]
        local = [(mx0 / ppm - half_w, my0 / ppm - half_h),
                 (mx1 / ppm - half_w, my0 / ppm - half_h),
                 (mx1 / ppm - half_w, my1 / ppm - half_h),
                 (mx0 / ppm - half_w, my1 / ppm - half_h)]
        wp = np.array([_world_from_local(lx_, ly_, c0, card_ang) for lx_, ly_ in local])
        wp3 = np.column_stack([wp, np.full(4, 0.6)])
        corners_px, Pc = _project(wp3, R_wc, C, K)
        sides = np.linalg.norm(np.roll(corners_px, -1, axis=0) - corners_px, axis=1)
        n_cam = R_wc @ np.array([0.0, 0.0, 1.0])
        tilt = float(np.degrees(np.arccos(np.clip(n_cam[2], -1.0, 1.0))))
        if tilt > 90:
            tilt = 180.0 - tilt
        marker_gt = {
            "cm_per_px": 6.0 / float(sides.mean()),
            "marker_corners_px": corners_px,
            "tilt_deg": tilt,
            "marker_side_px": float(sides.mean()),
        }
    else:
        card_rgb = None

    # vessel ----------------------------------------------------------------
    ves = VESSELS[cfg["vessel"]] if isinstance(cfg["vessel"], str) else cfg["vessel"]
    P0 = C + lam["table"][..., None] * dir_w
    rv = np.hypot(P0[..., 0], P0[..., 1])
    lam["floor"] = np.where(rv <= ves["r_in"], lam_z(ves["floor"]), np.inf)
    lam["rim"] = np.where((rv > ves["r_in"]) & (rv <= ves["r_out"]),
                          lam_z(ves["rim"]), np.inf)

    # food height field -----------------------------------------------------
    food = cfg["food"]
    Rf, rho = food["radius_mm"], food["density_g_ml"]
    grams_total = sum(c["share_g"] for c in food["components"])
    h_max, n_prof = _h_max_from_grams(grams_total, rho, Rf, food["kappa"])
    comps = food["components"]
    if food["layout"] == "whole" and len(comps) > 1:
        raise ValueError("layout='whole' requires exactly one component")
    rf = np.hypot(P0[..., 0], P0[..., 1])
    h_food = _h_profile(rf, Rf, h_max, n_prof)
    lam["food"] = np.where(rf <= Rf, lam_z(food.get("base_mm", ves["floor"]) + h_food),
                           np.inf)

    # occlusion pick --------------------------------------------------------
    names = ["table", "card", "floor", "rim", "food"] if cfg["anchor"]["card"] \
        else ["table", "floor", "rim", "food"]
    stack = np.stack([lam[k] for k in names], axis=-1)
    idx = np.argmin(stack, axis=-1)
    lam_min = np.take_along_axis(stack, idx[..., None], axis=-1)[..., 0]
    P_hit = C + lam_min[..., None] * dir_w
    depth_m = (lam_min / 1000.0).astype(np.float32)

    obj_names = {"table": 0, "floor": 1, "rim": 1, "card": 2, "food": 3}
    obj_ids = np.zeros((H, W), dtype=np.uint8)
    for i, nm in enumerate(names):
        obj_ids[idx == i] = obj_names[nm]
    food_sel = idx == names.index("food") if "food" in names else np.zeros((H, W), bool)

    # shading + materials ---------------------------------------------------
    light = np.array([0.35, -0.45, 0.82])
    light /= np.linalg.norm(light)
    img = np.empty((H, W, 3), dtype=np.float64)

    shade_table = 0.45 + 0.55 * float(light[2])
    tab_noise = _fbm(P_hit[..., 0], P_hit[..., 1], cell=45, octaves=2, seed=cfg["seed"])
    img[...] = np.asarray(cfg["table_color"], float) * shade_table * \
        (1.0 + 0.06 * (tab_noise[..., None] - 0.5) * 2)

    if card_rgb is not None:
        sel = idx == names.index("card")
        img[sel] = card_rgb[sel]

    for side in ("floor", "rim"):
        if side in names:
            sel = idx == names.index(side)
            img[sel] = np.asarray(ves["color"], float) * shade_table

    if food_sel.any():
        Xh, Yh = P_hit[..., 0], P_hit[..., 1]
        r_safe = np.where(rf < 1e-6, 1e-6, rf)
        dh_dr = -h_max * n_prof / Rf * np.clip(rf / Rf, 0, 1) ** (n_prof - 1)
        nx = -dh_dr * (Xh / r_safe)
        ny = -dh_dr * (Yh / r_safe)
        nz = np.ones_like(nx)
        nl = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
        diff = np.clip((nx * light[0] + ny * light[1] + nz * light[2]) / nl, 0, 1)
        shade = 0.45 + 0.55 * diff

        ang = (np.arctan2(Yh, Xh) - 0.0) % (2 * np.pi)
        total = sum(c["share_g"] for c in comps)
        zone = np.zeros((H, W), dtype=np.int64)
        cum = 0.0
        for ci, c in enumerate(comps):
            frac = c["share_g"] / total
            if len(comps) == 1:
                m = food_sel
            else:
                m = food_sel & (ang >= 2 * np.pi * cum) & (ang < 2 * np.pi * (cum + frac))
            cum += frac
            zone[m] = ci + 1
            mat = MATERIALS.get(c["material"], MATERIALS["rice"])
            tex = _fbm(Xh, Yh, cell=mat["scale"], octaves=3,
                       seed=cfg["seed"] + 7 * ci)
            col = np.asarray(mat["base"], float) * \
                (1.0 + mat["amp"] * (tex - 0.5) * 2)[..., None]
            img[m] = col[m] * shade[m, None]
        comp_ids = zone.astype(np.uint8)
    else:
        comp_ids = np.zeros((H, W), dtype=np.uint8)

    # post ------------------------------------------------------------------
    rng = np.random.default_rng(cfg["seed"] + 99)
    img = cv2.GaussianBlur(img, (3, 3), 0.6)
    img = img + rng.normal(0.0, cfg["noise_sigma"], img.shape)
    img = np.clip(img, 0, 255).astype(np.uint8)
    image_rgb = img
    image_bgr = img[:, :, ::-1].copy()

    grams_gt_list = _integrate_grams(food, h_max)
    grams_gt = {k: float(v) for k, v in grams_gt_list.items()}
    grams_gt_total = float(sum(grams_gt.values()))

    return {
        "image_rgb": image_rgb,
        "image_bgr": image_bgr,
        "depth_m": depth_m,
        "obj_ids": obj_ids,
        "comp_ids": comp_ids,
        "mask_food": food_sel,
        "grams_gt": grams_gt,
        "grams_gt_total": grams_gt_total,
        "anchor_gt": marker_gt,
        "camera": {"K": K, "R_wc": R_wc, "C": C, "size": (W, H)},
        "cfg": cfg,
    }
