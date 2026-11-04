"""TRAIN-only, label-preserving material statistics for renderer conditioning."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from nutrisense_synth.manifest import sha256_file
from nutrisense_synth.parameters import (eligible_wed_train_rows, load_class_registry,
                                         read_wed_train_manifest, wed_group_id)


def build_train_appearance_profiles(manifest: Path, dataset_root: Path,
                                    max_groups_per_class: int = 8,
                                    max_pixels_per_group: int = 12000) -> dict[int, dict[str, Any]]:
    """Estimate class material summaries from eligible TRAIN masks and images.

    Only RGB quantiles and within-group color spread are transferred; no WED
    pixels are copied into generated scenes. The DEV physical groups are
    removed before any image or annotation path is opened.
    """
    if max_groups_per_class < 1 or max_pixels_per_group < 100:
        raise ValueError("Appearance profile sample limits are too small")
    rows = eligible_wed_train_rows(read_wed_train_manifest(manifest))
    registry = load_class_registry()
    examples: dict[int, dict[str, tuple[Path, Path, str]]] = {key: {} for key in registry}
    for row in rows:
        image_path = dataset_root / str(row["image"])
        mask_name = row.get("mask")
        if not mask_name:
            continue
        mask_path = dataset_root / str(mask_name)
        for dish in row.get("dishes", []):
            class_id = int(dish.get("class_id", 0))
            if class_id not in registry:
                continue
            group = wed_group_id(row)
            examples[class_id].setdefault(group, (image_path, mask_path, str(row["image"])))

    profiles: dict[int, dict[str, Any]] = {}
    for class_id, params in registry.items():
        group_rows = sorted(examples[class_id].items())[:max_groups_per_class]
        group_profiles: list[dict[str, Any]] = []
        for group, (image_path, mask_path, source_record) in group_rows:
            image_bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            mask = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
            if image_bgr is None or mask is None:
                continue
            if mask.ndim == 3:
                if mask.shape[2] == 4:
                    mask = cv2.cvtColor(mask, cv2.COLOR_BGRA2GRAY)
                else:
                    mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)
            if mask.shape != image_bgr.shape[:2]:
                mask = cv2.resize(mask, (image_bgr.shape[1], image_bgr.shape[0]),
                                  interpolation=cv2.INTER_NEAREST)
            pixels_bgr = image_bgr[mask == class_id]
            if len(pixels_bgr) < 100:
                continue
            pixels = pixels_bgr[:, ::-1].astype(np.float32)
            if len(pixels) > max_pixels_per_group:
                stride = max(1, len(pixels) // max_pixels_per_group)
                pixels = pixels[::stride][:max_pixels_per_group]
            q10, median, q90 = np.quantile(pixels, [0.10, 0.50, 0.90], axis=0)
            luminance = pixels @ np.array([0.2126, 0.7152, 0.0722], np.float32)
            q25, q75 = np.quantile(luminance, [0.25, 0.75])
            group_profiles.append({
                "group_id": group,
                "source_record": source_record,
                "source_image_sha256": sha256_file(image_path),
                "source_mask_sha256": sha256_file(mask_path),
                "sampled_pixels": int(len(pixels)),
                "rgb_q10": q10.tolist(),
                "rgb_median": median.tolist(),
                "rgb_q90": q90.tolist(),
                "luminance_iqr": float(q75 - q25),
            })
        if not group_profiles:
            raise ValueError(f"No eligible WED TRAIN appearance pixels for class {params.class_name}")
        rgb = np.asarray([item["rgb_median"] for item in group_profiles], dtype=float)
        spread = np.asarray([item["luminance_iqr"] for item in group_profiles], dtype=float)
        profile = {
            "class_id": class_id,
            "class_name": params.class_name,
            "source_split": "eligible_train_only",
            "source_group_count": len(group_profiles),
            "base_rgb": np.median(rgb, axis=0).round(3).tolist(),
            "between_group_rgb_q10": np.quantile(rgb, 0.10, axis=0).round(3).tolist(),
            "between_group_rgb_q90": np.quantile(rgb, 0.90, axis=0).round(3).tolist(),
            "luminance_iqr_median": float(np.median(spread)),
            "texture_amplitude": float(np.clip(np.median(spread) / 255.0, 0.04, 0.32)),
            "statistics": group_profiles,
            "appearance_note": "TRAIN mask-conditioned color statistics only; no source pixels are copied.",
        }
        payload = repr((class_id, profile["source_group_count"], profile["base_rgb"],
                        profile["between_group_rgb_q10"], profile["between_group_rgb_q90"],
                        [item["source_image_sha256"] for item in group_profiles]))
        profile["profile_sha256"] = hashlib.sha256(payload.encode()).hexdigest()
        profiles[class_id] = profile
    return profiles


def _kelvin_to_rgb_gains(temp_k: float) -> tuple[float, float, float]:
    """Approximate Planckian color temperature gains normalized to D65 (6500K)."""
    t = float(np.clip(temp_k, 2000.0, 10000.0)) / 100.0
    # Red
    if t <= 66.0:
        r = 255.0
    else:
        r = 329.698727446 * ((t - 60.0) ** -0.1332047592)
    # Green
    if t <= 66.0:
        g = 99.4708025861 * np.log(t) - 161.1195681661
    else:
        g = 288.1221695283 * ((t - 60.0) ** -0.0755148492)
    # Blue
    if t >= 66.0:
        b = 255.0
    elif t <= 19.0:
        b = 0.0
    else:
        b = 138.5177312231 * np.log(t - 10.0) - 305.0447927307
    r = float(np.clip(r, 0.0, 255.0))
    g = float(np.clip(g, 0.0, 255.0))
    b = float(np.clip(b, 0.0, 255.0))
    # Reference D65 (~6500K)
    r65, g65, b65 = 255.0, 254.3, 250.0
    gain_r = float(np.clip(r / r65, 0.6, 1.4))
    gain_g = float(np.clip(g / g65, 0.8, 1.2))
    gain_b = float(np.clip(b / b65, 0.5, 1.3))
    return gain_r, gain_g, gain_b


def randomize_isp_lighting(
    image_bgr: np.ndarray,
    *,
    temperature_k: float | None = None,
    clahe_clip_limit: float | None = None,
    specular_strength: float | None = None,
    seed: int | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Apply ISP domain randomization: color temperature (2800K-6500K), CLAHE, and specular highlights."""
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError(f"Expected BGR image with shape (H, W, 3), got {image_bgr.shape}")
    rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState()
    temp_k = float(rng.uniform(2800.0, 6500.0) if temperature_k is None else temperature_k)
    clip_lim = float(rng.uniform(1.0, 3.0) if clahe_clip_limit is None else clahe_clip_limit)
    spec_str = float(rng.uniform(0.0, 0.35) if specular_strength is None else specular_strength)

    # 1. White-balance color temperature shift
    gain_r, gain_g, gain_b = _kelvin_to_rgb_gains(temp_k)
    bgr_gains = np.array([gain_b, gain_g, gain_r], dtype=np.float32)
    img_wb = np.clip(image_bgr.astype(np.float32) * bgr_gains, 0.0, 255.0).astype(np.uint8)

    # 2. CLAHE on L-channel in LAB
    lab = cv2.cvtColor(img_wb, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_lim, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l)
    lab_clahe = cv2.merge([l_clahe, a, b])
    img_clahe = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)

    # 3. Metallic specular reflection simulation
    h, w = image_bgr.shape[:2]
    if spec_str > 0.02 and h > 8 and w > 8:
        cx = float(rng.uniform(0.2 * w, 0.8 * w))
        cy = float(rng.uniform(0.2 * h, 0.8 * h))
        sx = float(rng.uniform(0.10 * w, 0.30 * w))
        sy = float(rng.uniform(0.10 * h, 0.30 * h))
        y_grid, x_grid = np.ogrid[:h, :w]
        dist_sq = ((x_grid - cx) / max(1.0, sx)) ** 2 + ((y_grid - cy) / max(1.0, sy)) ** 2
        specular_blob = np.exp(-0.5 * dist_sq).astype(np.float32)
        specular_addition = (specular_blob[:, :, None] * (spec_str * 255.0)).astype(np.float32)
        out_bgr = np.clip(img_clahe.astype(np.float32) + specular_addition, 0.0, 255.0).astype(np.uint8)
    else:
        out_bgr = img_clahe

    metadata = {
        "temperature_k": round(temp_k, 1),
        "clahe_clip_limit": round(clip_lim, 3),
        "specular_strength": round(spec_str, 3),
        "wb_gains_rgb": [round(gain_r, 4), round(gain_g, 4), round(gain_b, 4)],
    }
    return out_bgr, metadata


def compute_plate_relative_geometry(
    item_mask: np.ndarray,
    plate_mask: np.ndarray | None = None,
) -> dict[str, float]:
    """Compute vessel-relative geometry conditioning for WeightHead: area share, hull fill, aspect ratio."""
    item_bool = item_mask > 0
    item_area = int(np.count_nonzero(item_bool))
    if plate_mask is not None:
        plate_area = max(1, int(np.count_nonzero(plate_mask > 0)))
        area_share = float(item_area / plate_area)
    else:
        total_px = max(1, item_mask.shape[0] * item_mask.shape[1])
        plate_area = total_px
        area_share = float(item_area / total_px)

    if item_area == 0:
        return {
            "area_share_of_plate": 0.0,
            "hull_fill_ratio": 1.0,
            "aspect_ratio": 1.0,
            "item_area_px": 0.0,
            "plate_area_px": float(plate_area),
        }

    contours, _ = cv2.findContours(item_bool.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        all_pts = np.vstack(contours)
        hull = cv2.convexHull(all_pts)
        hull_area = float(cv2.contourArea(hull))
        hull_fill = float(item_area / max(float(item_area), hull_area)) if hull_area > 0 else 1.0

        if len(all_pts) >= 5:
            rect = cv2.minAreaRect(all_pts)
            w_box, h_box = rect[1]
            maj = max(w_box, h_box)
            min_dim = min(w_box, h_box)
            aspect = float(maj / max(1e-2, min_dim))
        else:
            x, y, w_box, h_box = cv2.boundingRect(all_pts)
            maj = max(w_box, h_box)
            min_dim = min(w_box, h_box)
            aspect = float(maj / max(1.0, min_dim))
    else:
        hull_fill = 1.0
        aspect = 1.0

    return {
        "area_share_of_plate": float(np.clip(area_share, 0.0, 1.0)),
        "hull_fill_ratio": float(np.clip(hull_fill, 0.0, 1.0)),
        "aspect_ratio": float(max(1.0, aspect)),
        "item_area_px": float(item_area),
        "plate_area_px": float(plate_area),
    }

