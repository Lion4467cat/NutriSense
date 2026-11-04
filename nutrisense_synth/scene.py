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
    return _h_max_from_volume(vol_ml, radius_mm, kappa)


def _h_max_from_volume(vol_ml, radius_mm, kappa):
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
    comps = food["components"]
    if len(comps) > 1 and all("center_mm" in component for component in comps):
        out = {}
        for component in comps:
            radius = float(component["radius_mm"])
            density = float(component.get("density_g_ml", food["density_g_ml"]))
            h_component, exponent = _h_max_from_grams(
                float(component["share_g"]), density, radius,
                float(component.get("kappa", food["kappa"])))
            xs = np.arange(-radius, radius + 1e-9, 1.0)
            X, Y = np.meshgrid(xs, xs)
            r = np.hypot(X, Y)
            height = _h_profile(r, radius, h_component, exponent)
            volume_mm3 = float(height.sum())
            out[component["name"]] = volume_mm3 * density / 1000.0
        return out
    R = food["radius_mm"]
    n = _kappa_n(food["kappa"])
    xs = np.arange(-R, R + 1e-9, 1.0)
    X, Y = np.meshgrid(xs, xs)
    r = np.hypot(X, Y)
    h = _h_profile(r, R, 1.0, n)          # unit h_max profile
    ang = (np.arctan2(Y, X) - start_angle) % (2 * np.pi)
    volumes = [float(c["share_g"]) / float(c.get("density_g_ml", food["density_g_ml"]))
               for c in comps]
    total_volume = sum(volumes)
    out, cum = {}, 0.0
    for c, component_volume in zip(comps, volumes):
        frac = component_volume / total_volume
        lo, hi = 2 * np.pi * cum, 2 * np.pi * (cum + frac)
        cum += frac
        zone = (ang >= lo) & (ang < hi) if len(comps) > 1 else (r <= R)
        vol_mm3 = float(h[zone].sum()) * h_max   # profile * dA(1mm^2)
        out[c["name"]] = vol_mm3 * float(c.get("density_g_ml", food["density_g_ml"])) / 1000.0
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
            "marker_id": 7,
            "dictionary": "DICT_4X4_50",
            "marker_side_mm": 60.0,
            "cm_per_px": 6.0 / float(sides.mean()),
            "marker_corners_px": corners_px,
            "marker_corners_world_mm": wp3,
            "card_center_world_mm": np.asarray([c0[0], c0[1], 0.6], dtype=np.float64),
            "card_angle_deg": float(cfg["anchor"]["card_angle_deg"]),
            "card_normal_world": np.asarray([0.0, 0.0, 1.0], dtype=np.float64),
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
    comps = food["components"]
    total_volume_ml = sum(float(c["share_g"]) / float(c.get("density_g_ml", rho))
                          for c in comps)
    separate_components = all("center_mm" in c for c in comps)
    if food["layout"] == "whole" and len(comps) > 1 and not separate_components:
        raise ValueError("layout='whole' requires exactly one component")
    rf = np.hypot(P0[..., 0], P0[..., 1])
    component_zones = np.zeros((H, W), dtype=np.uint8)
    class_surfaces = []
    if separate_components:
        component_lambdas = []
        component_params = []
        for component_index, component in enumerate(comps):
            radius = float(component["radius_mm"])
            center = np.asarray(component["center_mm"], dtype=float)
            density = float(component.get("density_g_ml", rho))
            if component.get("surface_model") == "class_surface_v1":
                from nutrisense_synth.food_models import generate_food_surface
                height_map, color_map, surface_metadata = generate_food_surface(
                    str(component["name"]), radius,
                    float(component["share_g"]) / density,
                    int(component.get("appearance_seed", cfg["seed"] + component_index)),
                    tuple(component["train_rgb"]) if component.get("train_rgb") else None)
                component_h, component_n = height_map, 0.0
                class_surfaces.append((height_map, color_map, surface_metadata))
            else:
                component_h, component_n = _h_max_from_grams(
                    float(component["share_g"]), density, radius,
                    float(component.get("kappa", food["kappa"])))
                class_surfaces.append(None)
            local_r = np.hypot(P0[..., 0] - center[0], P0[..., 1] - center[1])
            if component.get("surface_model") == "class_surface_v1":
                from nutrisense_synth.food_models import sample_surface
                ray_point = P0
                component_lambda = np.full((H, W), np.inf, dtype=np.float64)
                for _ in range(4):
                    dx_ray = ray_point[..., 0] - center[0]
                    dy_ray = ray_point[..., 1] - center[1]
                    radius_ray = np.hypot(dx_ray, dy_ray)
                    local_h, _ = sample_surface(component_h, class_surfaces[-1][1],
                                                dx_ray, dy_ray, radius)
                    candidate = lam_z(food.get("base_mm", ves["floor"]) + local_h)
                    visible_support = radius_ray <= radius
                    component_lambda = np.where(visible_support, candidate, np.inf)
                    finite_lambda = np.where(np.isfinite(component_lambda), component_lambda,
                                             lam["table"])
                    ray_point = C + finite_lambda[..., None] * dir_w
            else:
                local_h = _h_profile(local_r, radius, component_h, component_n)
                component_lambda = np.where(
                    local_r <= radius,
                    lam_z(food.get("base_mm", ves["floor"]) + local_h), np.inf)
            component_lambdas.append(component_lambda)
            component_params.append((center, radius, component_h, component_n,
                                     component.get("surface_model")))
        component_stack = np.stack(component_lambdas, axis=-1)
        nearest_component = np.argmin(component_stack, axis=-1)
        food_lam = np.min(component_stack, axis=-1)
        has_food = np.isfinite(food_lam)
        lam["food"] = food_lam
        component_zones[has_food] = nearest_component[has_food].astype(np.uint8) + 1
        h_max, n_prof = 0.0, _kappa_n(food["kappa"])
    else:
        h_max, n_prof = _h_max_from_volume(total_volume_ml, Rf, food["kappa"])
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
    illumination = cfg.get("illumination", {})
    light = np.asarray(illumination.get("direction", [0.35, -0.45, 0.82]), dtype=float)
    light /= max(float(np.linalg.norm(light)), 1e-9)
    light_intensity = float(illumination.get("intensity", 1.0))
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

    if food_sel.any() and separate_components:
        Xh, Yh = P_hit[..., 0], P_hit[..., 1]
        materials = {**MATERIALS, **cfg.get("materials", {})}
        for ci, component in enumerate(comps):
            m = food_sel & (component_zones == ci + 1)
            if not m.any():
                continue
            center, radius, component_h, component_n, surface_model = component_params[ci]
            dx, dy = Xh - center[0], Yh - center[1]
            local_r = np.hypot(dx, dy)
            r_safe = np.maximum(local_r, 1e-6)
            if surface_model == "class_surface_v1":
                from nutrisense_synth.food_models import sample_surface
                height_map, color_map, _ = class_surfaces[ci]
                height_sample, color_sample = sample_surface(height_map, color_map, dx, dy, radius)
                dh_dy, dh_dx = np.gradient(height_sample.astype(np.float32))
                nx, ny, nz = -dh_dx, -dh_dy, np.ones_like(dx)
            else:
                dh_dr = (-component_h * component_n / radius
                         * np.clip(local_r / radius, 0, 1) ** (component_n - 1))
                nx, ny, nz = -dh_dr * dx / r_safe, -dh_dr * dy / r_safe, np.ones_like(dx)
            nl = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
            diff = np.clip((nx * light[0] + ny * light[1] + nz * light[2]) / nl, 0, 1)
            shade = np.clip((0.45 + 0.55 * diff) * light_intensity, 0.2, 1.35)
            if surface_model == "class_surface_v1":
                col = color_sample.astype(float)
            else:
                mat = materials.get(component["material"], MATERIALS["rice"])
                tex = _fbm(Xh, Yh, cell=mat["scale"], octaves=3, seed=cfg["seed"] + 7 * ci)
                col = np.asarray(mat["base"], float) * (1.0 + mat["amp"] * (tex - 0.5) * 2)[..., None]
            img[m] = col[m] * shade[m, None]
        comp_ids = component_zones
    elif food_sel.any():
        Xh, Yh = P_hit[..., 0], P_hit[..., 1]
        r_safe = np.where(rf < 1e-6, 1e-6, rf)
        dh_dr = -h_max * n_prof / Rf * np.clip(rf / Rf, 0, 1) ** (n_prof - 1)
        nx = -dh_dr * (Xh / r_safe)
        ny = -dh_dr * (Yh / r_safe)
        nz = np.ones_like(nx)
        nl = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
        diff = np.clip((nx * light[0] + ny * light[1] + nz * light[2]) / nl, 0, 1)
        shade = np.clip((0.45 + 0.55 * diff) * light_intensity, 0.2, 1.35)

        ang = (np.arctan2(Yh, Xh) - 0.0) % (2 * np.pi)
        volumes = [float(c["share_g"]) / float(c.get("density_g_ml", rho)) for c in comps]
        total = sum(volumes)
        zone = np.zeros((H, W), dtype=np.int64)
        cum = 0.0
        for ci, (c, volume) in enumerate(zip(comps, volumes)):
            frac = volume / total
            if len(comps) == 1:
                m = food_sel
            else:
                m = food_sel & (ang >= 2 * np.pi * cum) & (ang < 2 * np.pi * (cum + frac))
            cum += frac
            zone[m] = ci + 1
            materials = {**MATERIALS, **cfg.get("materials", {})}
            mat = materials.get(c["material"], MATERIALS["rice"])
            tex = _fbm(Xh, Yh, cell=mat["scale"], octaves=3,
                       seed=cfg["seed"] + 7 * ci)
            col = np.asarray(mat["base"], float) * \
                (1.0 + mat["amp"] * (tex - 0.5) * 2)[..., None]
            img[m] = col[m] * shade[m, None]
        comp_ids = zone.astype(np.uint8)
    else:
        comp_ids = np.zeros((H, W), dtype=np.uint8)
    # Component IDs represent visible food pixels only; do not label food hidden
    # behind a vessel rim or card as if it were observed in the RGB image.
    comp_ids = np.asarray(comp_ids, dtype=np.uint8)
    comp_ids[~food_sel] = 0

    # post ------------------------------------------------------------------
    rng = np.random.default_rng(cfg["seed"] + 99)
    if any(c.get("surface_model") == "class_surface_v1" for c in comps):
        img = cv2.GaussianBlur(img, (3, 3), 0.22)
    else:
        img = cv2.GaussianBlur(img, (3, 3), 0.6)
    img = img + rng.normal(0.0, cfg["noise_sigma"], img.shape)
    img = np.clip(img, 0, 255).astype(np.uint8)
    image_rgb = img
    image_bgr = img[:, :, ::-1].copy()

    if separate_components and any(c.get("surface_model") == "class_surface_v1" for c in comps):
        grams_gt_list = {}
        for index, component in enumerate(comps):
            density = float(component.get("density_g_ml", rho))
            if component.get("surface_model") == "class_surface_v1":
                hmap = class_surfaces[index][0]
                grams_gt_list[str(component["name"])] = float(hmap.sum() * density / 1000.0)
            else:
                radius = float(component["radius_mm"])
                h_component, n_component = _h_max_from_grams(
                    float(component["share_g"]), density, radius,
                    float(component.get("kappa", food["kappa"])))
                xs = np.arange(-radius, radius + 1e-9, 1.0)
                X, Y = np.meshgrid(xs, xs)
                grams_gt_list[str(component["name"])] = float(
                    _h_profile(np.hypot(X, Y), radius, h_component, n_component).sum()
                    * density / 1000.0)
    else:
        grams_gt_list = _integrate_grams(food, h_max)
    grams_gt = {k: float(v) for k, v in grams_gt_list.items()}
    grams_gt_total = float(sum(grams_gt.values()))

    density_by_name = {
        str(component["name"]): float(component.get("density_g_ml", rho))
        for component in comps
    }
    volume_ml_gt = {
        name: grams / density_by_name[name] for name, grams in grams_gt.items()
    }
    surface_height_mm = np.full((H, W), np.nan, dtype=np.float32)
    surface_height_mm[food_sel] = P_hit[..., 2][food_sel].astype(np.float32)
    component_surface_metadata = {
        str(component["name"]): (class_surfaces[index][2] if class_surfaces[index] else {
            "model": "radial_v0", "archetype": "analytic_radial_mound"})
        for index, component in enumerate(comps)
    } if separate_components else {}
    return {
        "image_rgb": image_rgb,
        "image_bgr": image_bgr,
        "depth_m": depth_m,
        "obj_ids": obj_ids,
        "comp_ids": comp_ids,
        "mask_food": food_sel,
        "grams_gt": grams_gt,
        "grams_gt_total": grams_gt_total,
        "volume_ml_gt": volume_ml_gt,
        "volume_ml_gt_total": float(sum(volume_ml_gt.values())),
        "density_g_ml_by_component": density_by_name,
        "component_surface_metadata": component_surface_metadata,
        "surface_height_mm": surface_height_mm,
        "surface_xyz_world_mm": P_hit.astype(np.float32),
        "anchor_gt": marker_gt,
        "camera": {"K": K, "R_wc": R_wc, "C": C, "size": (W, H)},
        "cfg": cfg,
    }


def _shape_assumption(class_name: str) -> tuple[str, float, float]:
    """Return a coarse, explicit morphology prior for the analytic mound."""
    normalized = class_name.lower()
    if normalized in {"phulka", "papad"}:
        return "flat_disc_or_sheet", 0.88, 80.0
    if normalized in {"watermelon", "papaya", "banana", "muskmelon", "salad"}:
        return "cut_piece_or_loose_cluster", 0.43, 67.0
    if normalized in {"steamed-rice", "veg-pulao", "veg-dum-briyani",
                      "chicken-dum-biryani", "bisi-bele-bath", "boondi"}:
        return "loose_pile", 0.48, 72.0
    return "moist_or_compact_mound", 0.62, 65.0


def build_class_scene(class_id: int, class_name: str, grams: float,
                      density_g_ml: float, seed: int = 0,
                      card_present: bool = True,
                      size: tuple[int, int] = (640, 480),
                      appearance_profile: dict | None = None,
                      surface_model: str = "radial_v0") -> dict:
    """Build an isolated class scene with explicit mass and density inputs.

    The radial height field is an analytic shape assumption. This function
    does not imply that its pixels or volume were measured from the WED photo.
    """
    if class_id < 1 or not class_name or grams <= 0 or density_g_ml <= 0:
        raise ValueError("Class, positive net grams, and positive density are required")
    material = f"wed_class_{class_id:02d}"
    from nutrisense_synth.parameters import load_class_registry
    params = load_class_registry()[class_id]
    rng = np.random.default_rng(seed)
    shape_assumption, base_kappa, base_radius = _shape_assumption(class_name)
    if surface_model == "class_surface_v1":
        from nutrisense_synth.food_models import style_for
        shape_assumption = f"class_surface_v1:{style_for(class_name).model}"
    kappa = float(np.clip(base_kappa + rng.uniform(-0.035, 0.035), 0.35, 0.94))
    if surface_model == "class_surface_v1":
        from nutrisense_synth.food_models import target_mean_thickness_mm
        target_thickness = target_mean_thickness_mm(class_name)
        radius_mm = float(np.clip(np.sqrt((grams / density_g_ml) * 1000.0 /
                                          (np.pi * target_thickness)), 22.0, 90.0))
    else:
        radius_mm = float(np.clip(base_radius + rng.uniform(-7.0, 7.0), 48.0, 90.0))
    cx = float(rng.uniform(-35.0, 35.0))
    cy = float(rng.uniform(-285.0, -220.0))
    cz = float(rng.uniform(320.0, 410.0))
    target_x = float(rng.uniform(-12.0, 12.0))
    target_y = float(rng.uniform(20.0, 60.0))
    card_center = (float(rng.uniform(145.0, 190.0)), float(rng.uniform(-5.0, 30.0)))
    vessel = "plate" if int(rng.integers(0, 2)) == 0 else "bowl"
    light_direction = rng.normal(size=3)
    light_direction[2] = abs(light_direction[2]) + 0.5
    light_direction /= np.linalg.norm(light_direction)
    component = {"name": class_name, "material": material, "share_g": float(grams)}
    if surface_model == "class_surface_v1":
        component.update({
            "surface_model": surface_model,
            "center_mm": (0.0, 0.0),
            "radius_mm": radius_mm,
            "appearance_seed": int(seed),
            "train_rgb": appearance_profile.get("base_rgb") if appearance_profile else None,
            "shape_assumption": shape_assumption,
        })
    cfg = {
        "size": size,
        "camera": {"pos": (cx, cy, cz), "target": (target_x, target_y, 0.0),
                   "focal_mm": 5.0 if surface_model == "class_surface_v1" else 4.0},
        "vessel": vessel,
        "food": {
            "grams": float(grams), "density_g_ml": float(density_g_ml),
            "radius_mm": radius_mm, "kappa": kappa, "layout": "whole",
            "seed": seed, "components": [component],
        },
        "anchor": {"card": bool(card_present), "card_center": card_center,
                   "card_angle_deg": float(rng.uniform(-15.0, 15.0))},
        "table_color": tuple(int(v) for v in rng.integers(125, 205, 3)),
        "noise_sigma": float(rng.uniform(1.0, 5.0)),
        "illumination": {"profile": f"seeded_{seed % 7}",
                         "direction": tuple(float(v) for v in light_direction),
                         "intensity": float(rng.uniform(.8, 1.2))},
        "shape_assumption": shape_assumption,
        "materials": {material: {
            "base": (appearance_profile["base_rgb"] if appearance_profile else params.color_rgb[::-1]),
            "amp": (appearance_profile["texture_amplitude"] if appearance_profile else 0.22),
            "scale": 3.0 + (class_id % 5),
        }},
        "seed": int(seed),
    }
    return cfg


def build_thali_scene(components: list[dict], seed: int = 0,
                      card_present: bool = True,
                      size: tuple[int, int] = (640, 480),
                      appearance_profiles: dict[int, dict] | None = None,
                      surface_model: str = "radial_v0") -> dict:
    """Compose physically separate, labeled food regions in one plate scene."""
    if len(components) < 2:
        raise ValueError("A composed thali requires at least two components")
    from nutrisense_synth.parameters import load_class_registry
    registry = load_class_registry()
    normalized, materials = [], {}
    total_mass, total_volume = 0.0, 0.0
    for component_index, item in enumerate(components):
        class_id = int(item["class_id"])
        if class_id not in registry:
            raise ValueError(f"Unsupported WED class id: {class_id}")
        params = registry[class_id]
        grams = float(item["grams"])
        if grams <= 0:
            raise ValueError("Thali component masses must be positive net grams")
        material = params.material
        shape_assumption, base_kappa, _ = _shape_assumption(params.class_name)
        if surface_model == "class_surface_v1":
            from nutrisense_synth.food_models import style_for
            shape_assumption = f"class_surface_v1:{style_for(params.class_name).model}"
        component_rng = np.random.default_rng(seed + class_id)
        kappa = float(np.clip(base_kappa + component_rng.uniform(-0.035, 0.035),
                              0.35, 0.94))
        density = float(item.get("density_g_ml", params.density_g_ml))
        volume_ml = grams / density
        if surface_model == "class_surface_v1":
            from nutrisense_synth.food_models import target_mean_thickness_mm
            target_thickness = target_mean_thickness_mm(params.class_name)
            radius = float(np.clip(np.sqrt(volume_ml * 1000.0 /
                                           (np.pi * target_thickness)), 18.0, 42.0))
        else:
            radius = float(np.clip(np.sqrt(volume_ml * 1000.0 / (np.pi * 7.0)), 18.0, 35.0))
        positions = [(-43.0, -40.0), (43.0, -40.0), (0.0, 0.0),
                     (-43.0, 40.0), (43.0, 40.0), (0.0, 49.0)]
        center = positions[component_index % len(positions)]
        component_cfg = {"name": params.class_name, "material": material,
                           "share_g": grams, "density_g_ml": density,
                           "kappa": kappa, "shape_assumption": shape_assumption}
        profile = (appearance_profiles or {}).get(class_id)
        if surface_model == "class_surface_v1":
            component_cfg.update({
                "surface_model": surface_model,
                "center_mm": center,
                "radius_mm": radius,
                "appearance_seed": int(seed + class_id),
                "train_rgb": profile.get("base_rgb") if profile else None,
            })
        normalized.append(component_cfg)
        materials[material] = {"base": profile["base_rgb"] if profile else params.color_rgb[::-1],
                               "amp": profile["texture_amplitude"] if profile else .22,
                               "scale": 3.0 + class_id % 5}
        total_mass += grams
        total_volume += grams / density
    effective_density = total_mass / total_volume
    effective_kappa = sum(float(item["share_g"]) / float(item["density_g_ml"])
                          * float(item["kappa"]) for item in normalized) / total_volume
    base = build_class_scene(int(components[0]["class_id"]),
                             registry[int(components[0]["class_id"])].class_name,
                             float(components[0]["grams"]),
                             registry[int(components[0]["class_id"])].density_g_ml,
                             seed=seed, card_present=card_present, size=size,
                             surface_model="radial_v0")
    base["vessel"] = "plate"
    if surface_model == "class_surface_v1":
        base["camera"]["focal_mm"] = 5.0
    base["food"].update({"grams": total_mass, "density_g_ml": effective_density,
                         "kappa": effective_kappa, "components": normalized,
                         "layout": "whole" if surface_model == "class_surface_v1" else "sectors",
                         "shape_assumption": "separate_class_surface_heightfields" if surface_model == "class_surface_v1" else "shared_radial_surface_with_volume_proportional_sectors"})
    base["materials"] = materials
    return base


def render_card_pair(cfg: dict) -> tuple[dict, dict]:
    """Render identical scene conditions with only card presence changed."""
    import copy
    from nutrisense_synth.quality import check_card_pair

    present_cfg, absent_cfg = copy.deepcopy(cfg), copy.deepcopy(cfg)
    present_cfg.setdefault("anchor", {})["card"] = True
    absent_cfg.setdefault("anchor", {})["card"] = False
    present, absent = render_scene(present_cfg), render_scene(absent_cfg)
    findings = check_card_pair(present, absent)
    failures = [finding for finding in findings if not finding.passed]
    if failures:
        details = "; ".join(item.message for item in failures)
        raise ValueError(f"Card/no-card scene pair failed validation: {details}")
    return present, absent
