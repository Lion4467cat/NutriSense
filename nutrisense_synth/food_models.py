"""Deterministic class-conditioned procedural food surfaces for renderer pilots.

The geometry and albedo are generated together from a recipe, but labels are
derived from the height support and its numeric integral. No source pixels or
model-predicted masses enter the scene.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class FoodStyle:
    model: str
    palette: tuple[tuple[int, int, int], ...]
    detail: str


# Explicit recipes cover the complete WED taxonomy. Colors are procedural
# priors; eligible TRAIN statistics modulate their luminance/chroma only.
_STYLES: dict[str, FoodStyle] = {
    "Bottle-gourd-curry": FoodStyle("curry_chunks", ((170, 132, 61), (141, 177, 98), (217, 190, 126)), "pale green gourd cubes in yellow-green gravy"),
    "aloo-capsicum": FoodStyle("dry_pieces", ((178, 133, 63), (82, 137, 73), (218, 177, 93)), "potato cubes and green capsicum"),
    "aloo-curry": FoodStyle("curry_chunks", ((174, 119, 55), (224, 181, 97), (131, 91, 45)), "potato chunks in spiced gravy"),
    "aloo-fry": FoodStyle("dry_pieces", ((191, 145, 75), (121, 78, 42), (220, 184, 111)), "browned potato pieces"),
    "beans-curry": FoodStyle("curry_chunks", ((124, 133, 67), (67, 127, 66), (194, 159, 77)), "short green-bean pieces in gravy"),
    "beetroot-kobari": FoodStyle("dry_pieces", ((143, 52, 75), (238, 233, 209), (94, 129, 64)), "beetroot and coconut flecks"),
    "beetroot-poriyal": FoodStyle("dry_pieces", ((146, 49, 74), (196, 92, 104), (229, 206, 164)), "small beetroot dice with coconut"),
    "bisi-bele-bath": FoodStyle("grain_mixed", ((174, 94, 49), (214, 166, 84), (88, 133, 68), (231, 205, 151)), "soft rice grains, lentils and vegetables"),
    "boondi": FoodStyle("small_rounds", ((195, 143, 63), (224, 177, 91), (161, 102, 45)), "small fried gram droplets"),
    "cabbage-dry": FoodStyle("shreds", ((153, 169, 115), (208, 195, 151), (104, 126, 76)), "short curled cabbage ribbons"),
    "channa-brinjal": FoodStyle("curry_chunks", ((116, 79, 47), (181, 133, 76), (98, 83, 58)), "chickpeas and aubergine pieces"),
    "chicken-dum-biryani": FoodStyle("grain_mixed", ((223, 204, 158), (184, 113, 56), (224, 174, 80), (121, 146, 69), (148, 70, 58)), "long rice grains, chicken pieces and herbs"),
    "chutney": FoodStyle("thick_paste", ((111, 139, 82), (193, 181, 135), (84, 101, 55)), "ground chutney with herb and coconut flecks"),
    "curd": FoodStyle("smooth_dairy", ((245, 241, 227), (231, 226, 210), (205, 209, 187)), "white cultured dairy with subtle curds"),
    "dondakaya-fry": FoodStyle("dry_pieces", ((91, 125, 58), (157, 123, 60), (210, 171, 95)), "small ivy-gourd slices"),
    "kakarakaya-fry": FoodStyle("dry_pieces", ((94, 128, 66), (160, 120, 55), (203, 163, 82)), "ridged bitter-gourd slices"),
    "kofta-curry": FoodStyle("curry_chunks", ((148, 94, 53), (196, 144, 81), (205, 165, 99)), "round kofta pieces in orange gravy"),
    "leaf-dal": FoodStyle("dal_leaf", ((119, 119, 53), (76, 113, 61), (204, 160, 82)), "lentil base with dark leafy greens"),
    "mango-pickle": FoodStyle("oily_chunks", ((174, 67, 42), (219, 145, 55), (114, 57, 34)), "oiled mango chunks with red spice"),
    "masoor-dal": FoodStyle("dal", ((190, 133, 62), (224, 175, 91), (151, 91, 42)), "orange lentils with tempering flecks"),
    "mirchi-ka-salan": FoodStyle("curry_chunks", ((112, 91, 57), (55, 111, 61), (161, 124, 72)), "whole green chillies in nutty gravy"),
    "muddha-pappu": FoodStyle("dal", ((203, 173, 103), (232, 210, 152), (157, 117, 59)), "thick pale lentil mash"),
    "non-spicy-curry": FoodStyle("curry_chunks", ((192, 153, 87), (103, 139, 74), (225, 194, 128)), "mild vegetable curry with visible pieces"),
    "non-spicy-dal": FoodStyle("dal", ((215, 184, 111), (240, 217, 157), (176, 139, 73)), "mild yellow lentil stew"),
    "pachi-pulusu": FoodStyle("thin_sauce", ((141, 113, 66), (198, 157, 89), (91, 124, 67)), "thin tamarind broth with onion and herb"),
    "papad": FoodStyle("papad", ((224, 192, 133), (153, 98, 57), (241, 219, 171)), "thin bubbled crisp with toasted blisters"),
    "payasam": FoodStyle("liquid_dairy", ((235, 219, 178), (186, 135, 77), (128, 91, 53)), "pale sweet milk with vermicelli or nut flecks"),
    "phulka": FoodStyle("flatbread", ((223, 191, 132), (128, 77, 46), (238, 216, 173)), "thin irregular wheat flatbread with brown spots"),
    "raita": FoodStyle("dairy_chunks", ((239, 235, 216), (136, 88, 62), (101, 139, 80), (214, 115, 93)), "yogurt with cucumber and tomato pieces"),
    "rajma": FoodStyle("curry_chunks", ((132, 76, 48), (179, 109, 61), (208, 152, 87)), "red kidney beans in thick gravy"),
    "rasam": FoodStyle("thin_sauce", ((183, 105, 48), (215, 152, 66), (101, 129, 67)), "thin tomato broth with spice particles"),
    "salad": FoodStyle("salad_chunks", ((206, 61, 54), (91, 151, 76), (234, 191, 76), (222, 215, 189)), "separate tomato, cucumber, carrot and onion pieces"),
    "sambar": FoodStyle("curry_chunks", ((182, 112, 47), (91, 138, 72), (221, 172, 69), (163, 68, 47)), "lentil gravy with vegetable chunks"),
    "steamed-rice": FoodStyle("rice_grains", ((243, 239, 224), (230, 225, 208), (252, 248, 235)), "distinct elongated cooked rice grains"),
    "tomato-pappu": FoodStyle("dal_leaf", ((194, 105, 67), (228, 154, 90), (75, 126, 66)), "tomato lentil mash with herb flecks"),
    "veg-dum-briyani": FoodStyle("grain_mixed", ((228, 212, 170), (197, 147, 82), (94, 141, 73), (211, 164, 77)), "long rice grains with visible vegetables"),
    "veg-pulao": FoodStyle("grain_mixed", ((226, 215, 179), (104, 149, 77), (218, 164, 78), (194, 109, 65)), "separate rice grains with peas and vegetables"),
    "Watermelon": FoodStyle("fruit_chunks", ((218, 67, 75), (53, 116, 67), (245, 231, 211)), "red fruit cubes with occasional rind"),
    "Papaya": FoodStyle("fruit_chunks", ((235, 155, 69), (241, 190, 91), (218, 227, 181)), "orange papaya chunks"),
    "Banana": FoodStyle("fruit_chunks", ((242, 220, 132), (224, 192, 99), (251, 236, 173)), "pale curved banana slices"),
    "Muskmelon": FoodStyle("fruit_chunks", ((228, 188, 110), (239, 211, 151), (218, 230, 181)), "pale orange melon chunks"),
}


def style_for(class_name: str) -> FoodStyle:
    try:
        return _STYLES[class_name]
    except KeyError as exc:
        raise ValueError(f"No class-specific food recipe for {class_name!r}") from exc


def target_mean_thickness_mm(class_name: str) -> float:
    """Explicit geometric prior used to set portion footprint from its volume."""
    archetype = style_for(class_name).model
    if archetype in {"flatbread", "papad"}:
        return 1.8 if archetype == "flatbread" else 1.25
    if archetype in {"salad_chunks", "fruit_chunks", "small_rounds", "dry_pieces", "shreds"}:
        return 7.0
    if archetype in {"rice_grains", "grain_mixed"}:
        return 10.0
    if archetype in {"thin_sauce", "liquid_dairy"}:
        return 10.0
    return 13.0


def _smooth_noise(rng: np.random.Generator, n: int, sigma: float) -> np.ndarray:
    low = rng.normal(size=(max(4, n // 12), max(4, n // 12))).astype(np.float32)
    return cv2.resize(low, (n, n), interpolation=cv2.INTER_CUBIC) * sigma


def _put_ellipsoid(height: np.ndarray, rgb: np.ndarray, cx: float, cy: float,
                   rx: float, ry: float, z: float, color: tuple[int, int, int],
                   angle: float = 0.0) -> None:
    n = height.shape[0]
    radius = int(np.ceil(max(rx, ry) * 1.5))
    x0, x1 = max(0, int(cx) - radius), min(n, int(cx) + radius + 1)
    y0, y1 = max(0, int(cy) - radius), min(n, int(cy) + radius + 1)
    if x1 <= x0 or y1 <= y0:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    ca, sa = np.cos(angle), np.sin(angle)
    dx, dy = xx - cx, yy - cy
    u, v = ca * dx + sa * dy, -sa * dx + ca * dy
    q = (u / max(rx, 0.5)) ** 2 + (v / max(ry, 0.5)) ** 2
    dome = z * np.sqrt(np.clip(1.0 - q, 0.0, 1.0))
    roi = height[y0:y1, x0:x1]
    take = (q <= 1.0) & (dome > roi)
    roi[take] = dome[take]
    rgb[y0:y1, x0:x1][take] = color


def generate_food_surface(class_name: str, radius_mm: float, volume_ml: float,
                          seed: int, train_rgb: tuple[float, float, float] | None = None
                          ) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Create a 1 mm height/albedo grid, normalize height to volume_ml.

    The integral of returned height over its 1 mm² cells is the authoritative
    volume (within the documented raster discretization). RGB is not used to
    infer geometry or mass.
    """
    style = style_for(class_name)
    n = int(np.ceil(radius_mm)) * 2 + 1
    c = n // 2
    yy, xx = np.mgrid[:n, :n].astype(np.float32)
    dx, dy = xx - c, yy - c
    rng = np.random.default_rng(seed)
    radial_noise = _smooth_noise(rng, n, 0.035)
    edge = radius_mm * (1.0 + radial_noise)
    disk = np.hypot(dx, dy) <= edge
    palette = np.asarray(style.palette, dtype=np.float32)
    if train_rgb is not None:
        measured = np.asarray(train_rgb, dtype=np.float32)
        # TRAIN pixels guide broad tone while class recipe retains chromatic identity.
        recipe_mean = palette.mean(axis=0)
        ratio = np.clip(measured / np.maximum(recipe_mean, 1), 0.78, 1.22)
        palette = np.clip(palette * ratio[None, :], 0, 255)
    rgb = np.zeros((n, n, 3), dtype=np.float32)
    height = np.zeros((n, n), dtype=np.float32)
    name = style.model
    target_mean = float(volume_ml * 1000.0 / (np.pi * radius_mm * radius_mm))
    unit_r = np.hypot(dx, dy) / max(radius_mm, 1)
    if name in {"rice_grains", "grain_mixed", "small_rounds", "shreds", "salad_chunks", "fruit_chunks", "dry_pieces"}:
        base_color = palette[0]
        rgb[disk] = base_color
        if name in {"rice_grains", "grain_mixed"}:
            height[disk] = target_mean * (0.78 + 0.22 * (1 - unit_r[disk] ** 2))
        else:
            height[disk] = target_mean * 0.12
        divisor = {"rice_grains": 11, "grain_mixed": 48,
                   "salad_chunks": 82, "fruit_chunks": 72,
                   "dry_pieces": 76, "small_rounds": 36, "shreds": 28}[name]
        count = int(np.pi * radius_mm * radius_mm / divisor)
        for _ in range(count):
            rr = radius_mm * np.sqrt(rng.random()) * 0.94
            ang = rng.uniform(-np.pi, np.pi)
            px, py = c + rr * np.cos(ang), c + rr * np.sin(ang)
            if name == "rice_grains":
                rx, ry = rng.uniform(2.6, 4.6), rng.uniform(0.75, 1.35)
                z = target_mean * rng.uniform(1.08, 1.28)
            elif name == "grain_mixed":
                rx, ry = rng.uniform(3.6, 6.0), rng.uniform(1.5, 3.0)
                z = target_mean * rng.uniform(1.10, 1.55)
            elif name == "small_rounds":
                rx, ry, z = rng.uniform(1.7, 2.8), rng.uniform(1.7, 2.8), rng.uniform(1.0, 2.1)
            elif name == "shreds":
                rx, ry, z = rng.uniform(2.4, 6), rng.uniform(.6, 1.4), rng.uniform(.6, 1.4)
            elif name in {"salad_chunks", "fruit_chunks", "dry_pieces"}:
                rx, ry = rng.uniform(4.2, 7.0), rng.uniform(3.0, 5.8)
                z = target_mean * rng.uniform(1.25, 2.2)
            else:
                rx, ry, z = rng.uniform(2.5, 5.8), rng.uniform(1.8, 4.5), rng.uniform(1.4, 3.0)
            color = tuple(int(v) for v in palette[int(rng.integers(0, len(palette)))])
            _put_ellipsoid(height, rgb, px, py, rx, ry, z, color, float(rng.uniform(-np.pi, np.pi)))
    elif name in {"flatbread", "papad"}:
        rgb[disk] = palette[0]
        edge_factor = np.clip(1.0 - unit_r ** 2, 0, 1)
        height[disk] = target_mean * (0.9 + 0.1 * edge_factor[disk])
        # Low frequency warping creates irregular outlines and a thin, sheet-like profile.
        spots = int(radius_mm * .28 if name == "flatbread" else radius_mm * .42)
        for _ in range(spots):
            rr = radius_mm * np.sqrt(rng.random()) * .88
            ang = rng.uniform(-np.pi, np.pi)
            px, py = c + rr * np.cos(ang), c + rr * np.sin(ang)
            rx, ry = rng.uniform(1.5, 4.5), rng.uniform(1.5, 4.5)
            if name == "papad":
                bump = rng.uniform(.7, 1.6)
                _put_ellipsoid(height, rgb, px, py, rx, ry, bump, tuple(palette[1]), 0)
            else:
                yy0, xx0 = np.mgrid[:n, :n]
                patch = ((xx0 - px) / rx) ** 2 + ((yy0 - py) / ry) ** 2 < 1
                rgb[patch & disk] = palette[1]
                height[patch & disk] += rng.uniform(.15, .45)
    else:
        # Curries/dals/pastes: a shallow irregular bed, plus class-specific chunks.
        base = target_mean * (0.88 if name in {"thin_sauce", "liquid_dairy"} else 0.52)
        waviness = np.maximum(0, 1 - unit_r ** 2) * rng.uniform(1.5, 3.5)
        height[disk] = (base + waviness[disk] + radial_noise[disk] * 2).clip(.5)
        rgb[disk] = palette[0]
        chunk_count = int(radius_mm * (0.12 if name in {"thin_sauce", "liquid_dairy"} else .45))
        if name in {"smooth_dairy", "thick_paste"}:
            chunk_count = int(radius_mm * .18)
        for _ in range(chunk_count):
            rr = radius_mm * np.sqrt(rng.random()) * .85
            ang = rng.uniform(-np.pi, np.pi)
            px, py = c + rr * np.cos(ang), c + rr * np.sin(ang)
            rx, ry = rng.uniform(4.5, 8.0), rng.uniform(3.8, 7.0)
            z = target_mean * rng.uniform(1.10, 1.85)
            color = tuple(int(v) for v in palette[int(rng.integers(1, len(palette)))])
            _put_ellipsoid(height, rgb, px, py, rx, ry, z, color, float(rng.uniform(-np.pi, np.pi)))
    texture = _smooth_noise(rng, n, 4.0)
    rgb = np.clip(rgb + texture[..., None], 0, 255)
    height[~disk] = 0
    raw_volume_mm3 = float(height.sum())
    if raw_volume_mm3 <= 0 or volume_ml <= 0:
        raise ValueError("Food recipe produced empty geometry or invalid volume")
    scale = float(volume_ml * 1000.0 / raw_volume_mm3)
    height *= scale
    if not np.isfinite(height).all() or float(height.max()) > 65.0:
        raise ValueError(f"Class geometry requires implausible height scaling ({height.max():.1f} mm)")
    metadata: dict[str, object] = {
        "model": "class_surface_v1", "archetype": style.model,
        "detail": style.detail, "grid_mm": 1.0,
        "target_mean_thickness_mm": target_mean,
        "volume_scale_factor": scale,
        "raster_volume_ml": float(height.sum() / 1000.0),
        "rasterization_note": "1 mm height-field cells; volume is numeric integral; ingredient geometry shares component class mask",
    }
    return height, rgb.astype(np.uint8), metadata


def sample_surface(height: np.ndarray, rgb: np.ndarray, dx: np.ndarray, dy: np.ndarray,
                   radius_mm: float) -> tuple[np.ndarray, np.ndarray]:
    """Bilinearly sample a centered local surface map; outside support is zero."""
    c = (height.shape[0] - 1) / 2
    map_x = (dx + c).astype(np.float32)
    map_y = (dy + c).astype(np.float32)
    h = cv2.remap(height, map_x, map_y, cv2.INTER_LINEAR,
                  borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    color = cv2.remap(rgb, map_x, map_y, cv2.INTER_LINEAR,
                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    support = np.hypot(dx, dy) <= radius_mm
    h[~support] = 0
    color[~support] = 0
    return h, color
