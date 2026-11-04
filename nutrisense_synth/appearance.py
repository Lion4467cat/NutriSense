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
