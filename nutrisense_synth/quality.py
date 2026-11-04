"""Automated task-specific checks for renderer and appearance outputs."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import cv2


@dataclass(frozen=True)
class QualityFinding:
    check: str
    passed: bool
    message: str
    task: str | None = None


def check_scene(scene: dict[str, Any]) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    image = scene.get("image_rgb")
    depth = scene.get("depth_m")
    mask = scene.get("mask_food")
    if not isinstance(image, np.ndarray) or image.ndim != 3 or image.shape[-1] != 3:
        findings.append(QualityFinding("rgb_shape", False, "Expected HxWx3 RGB image"))
    else:
        findings.append(QualityFinding("rgb_shape", image.dtype == np.uint8,
                                       "RGB image must use uint8 pixels"))
    if not isinstance(depth, np.ndarray) or depth.ndim != 2:
        findings.append(QualityFinding("depth_shape", False, "Expected 2D metric depth", "depth"))
    else:
        ok = np.isfinite(depth).all() and bool(np.all(depth > 0))
        findings.append(QualityFinding("depth_finite_nonnegative", ok,
                                       "Metric camera-Z depth must be finite and positive", "depth"))
    if isinstance(image, np.ndarray) and isinstance(mask, np.ndarray):
        findings.append(QualityFinding("food_mask_shape", mask.shape == image.shape[:2],
                                       "Food mask must align with RGB pixels", "segmentation"))
        comp_ids = np.asarray(scene.get("comp_ids"))
        obj_ids = np.asarray(scene.get("obj_ids"))
        aligned = (comp_ids.shape == image.shape[:2] and obj_ids.shape == image.shape[:2]
                   and np.array_equal(mask.astype(bool), comp_ids > 0)
                   and np.array_equal(mask.astype(bool), obj_ids == 3))
        findings.append(QualityFinding("food_component_object_alignment", bool(aligned),
                                       "Food mask, component IDs and food object IDs must agree",
                                       "segmentation"))
        component_values = {int(value) for value in np.unique(comp_ids) if int(value) > 0}
        expected_components = set(range(1, len(scene.get("grams_gt", {})) + 1))
        component_coverage = component_values == expected_components
        findings.append(QualityFinding("all_component_regions_visible", component_coverage,
                                       "Every geometry component must have a visible renderer region",
                                       "segmentation"))
    grams = scene.get("grams_gt", {})
    mass_ok = isinstance(grams, dict) and all(float(v) >= 0 for v in grams.values())
    findings.append(QualityFinding("mass_nonnegative", mass_ok,
                                   "Component mass values must be nonnegative", "mass"))
    volume = scene.get("volume_ml_gt", {})
    density = scene.get("density_g_ml_by_component", {})
    physical_ok = (set(grams) == set(volume) == set(density)
                   and all(np.isfinite(float(volume[name])) and float(volume[name]) > 0
                           and np.isfinite(float(density[name])) and float(density[name]) > 0
                           and abs(float(grams[name]) - float(volume[name]) * float(density[name]))
                           <= max(1e-3, float(grams[name]) * 1e-6)
                           for name in grams))
    findings.append(QualityFinding("mass_volume_density", bool(physical_ok),
                                   "Physical mass must equal renderer volume × recorded density",
                                   "mass"))
    points = scene.get("surface_xyz_world_mm")
    points_ok = (isinstance(points, np.ndarray) and image is not None
                 and points.shape == (*image.shape[:2], 3)
                 and np.isfinite(points).all())
    findings.append(QualityFinding("world_geometry_shape", bool(points_ok),
                                   "World-coordinate surface points must be finite and image-aligned",
                                   "depth"))
    anchor = scene.get("anchor_gt")
    if anchor is not None:
        corners = np.asarray(anchor.get("marker_corners_px"))
        ok = (corners.shape == (4, 2) and np.isfinite(corners).all()
              and float(anchor.get("marker_side_mm", 0)) == 60.0
              and int(anchor.get("marker_id", -1)) == 7
              and bool(np.all(corners[:, 0] >= 0) and np.all(corners[:, 0] < image.shape[1])
                       and np.all(corners[:, 1] >= 0) and np.all(corners[:, 1] < image.shape[0])))
        findings.append(QualityFinding("marker_corners", bool(ok),
                                       "ID 7 / 60 mm marker requires four finite in-frame corners",
                                       "marker"))
    return findings


def check_card_pair(present: dict[str, Any], absent: dict[str, Any]) -> list[QualityFinding]:
    """Check that scene state matches and only marker/card pixels changed."""
    findings: list[QualityFinding] = []
    same_food = (np.array_equal(present.get("mask_food"), absent.get("mask_food"))
                 and np.array_equal(present.get("comp_ids"), absent.get("comp_ids")))
    findings.append(QualityFinding("pair_food_geometry", same_food,
                                   "Food masks/components must match exactly", "segmentation"))
    same_mass = present.get("grams_gt") == absent.get("grams_gt")
    findings.append(QualityFinding("pair_physical_mass", same_mass,
                                   "Physical component masses must match exactly", "mass"))
    same_camera = all(np.array_equal(present["camera"][key], absent["camera"][key])
                      for key in ("K", "R_wc", "C", "size"))
    findings.append(QualityFinding("pair_camera", same_camera,
                                   "Camera intrinsics, pose, and resolution must match"))
    p_obj, a_obj = np.asarray(present.get("obj_ids")), np.asarray(absent.get("obj_ids"))
    card_mask = ((p_obj == 2) | (a_obj == 2)) if p_obj.ndim == 2 and a_obj.shape == p_obj.shape \
        else np.zeros((0, 0), dtype=bool)
    p_depth, a_depth = np.asarray(present.get("depth_m")), np.asarray(absent.get("depth_m"))
    same_depth_outside_card = (card_mask.ndim == 2 and p_depth.shape == card_mask.shape
                               and a_depth.shape == card_mask.shape
                               and np.array_equal(p_depth[~card_mask], a_depth[~card_mask]))
    findings.append(QualityFinding("pair_depth_outside_card", bool(same_depth_outside_card),
                                   "Depth must match outside the physical card footprint", "depth"))
    p_xyz, a_xyz = present.get("surface_xyz_world_mm"), absent.get("surface_xyz_world_mm")
    same_xyz_outside_card = (isinstance(p_xyz, np.ndarray) and isinstance(a_xyz, np.ndarray)
                             and p_xyz.shape[:2] == card_mask.shape
                             and a_xyz.shape[:2] == card_mask.shape
                             and np.array_equal(p_xyz[~card_mask], a_xyz[~card_mask]))
    findings.append(QualityFinding("pair_geometry_outside_card", bool(same_xyz_outside_card),
                                   "3D scene points must match outside the physical card footprint"))
    present_cfg, absent_cfg = dict(present.get("cfg", {})), dict(absent.get("cfg", {}))
    p_anchor, a_anchor = dict(present_cfg.pop("anchor", {})), dict(absent_cfg.pop("anchor", {}))
    p_card, a_card = p_anchor.pop("card", None), a_anchor.pop("card", None)
    same_settings = present_cfg == absent_cfg and p_anchor == a_anchor and p_card is True and a_card is False
    findings.append(QualityFinding("pair_config", same_settings,
                                   "Only anchor.card may differ between pair configurations"))
    p_image, a_image = present.get("image_rgb"), absent.get("image_rgb")
    if isinstance(p_image, np.ndarray) and isinstance(a_image, np.ndarray) and p_image.shape == a_image.shape:
        changed = np.any(p_image != a_image, axis=2)
        card_ids = (np.asarray(present.get("obj_ids")) == 2) | (np.asarray(absent.get("obj_ids")) == 2)
        allowed = cv2.dilate(card_ids.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        local_only = bool(np.all(~changed | allowed))
    else:
        local_only = False
    findings.append(QualityFinding("pair_pixels", local_only,
                                   "RGB differences must be confined to card pixels"))
    return findings


def findings_to_dict(findings: list[QualityFinding]) -> list[dict[str, Any]]:
    return [asdict(item) for item in findings]
