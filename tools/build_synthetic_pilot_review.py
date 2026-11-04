"""Build a visual gallery and separate human-review package from an existing pilot."""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
from pathlib import Path
import sys
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nutrisense_synth.evaluation import require_frozen_baseline
from nutrisense_synth.manifest import sha256_file
from nutrisense_synth.parameters import load_class_registry

STATUS_VALUES = ("PASS", "FAIL", "REVIEW_REQUIRED")
DEFAULT_PILOT = ROOT / "datasets/processed/synthetic_food_pilot_20261103"
DEFAULT_OUTPUT = ROOT / "experiments/synthetic_food/pilot_review_20261103"


def _rgb(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGB"))


def _save_rgb(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(image, dtype=np.uint8)).save(path)


def _class_color(class_id: int) -> tuple[int, int, int]:
    hue = (int(class_id) * 47) % 180
    values = cv2.cvtColor(np.uint8([[[hue, 190, 240]]]), cv2.COLOR_HSV2RGB)[0, 0]
    return tuple(int(value) for value in values)


def _class_mask_view(path: Path) -> np.ndarray:
    labels = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    output = np.zeros((*labels.shape, 3), dtype=np.uint8)
    for class_id in load_class_registry():
        output[labels == class_id] = _class_color(class_id)
    return output


def _component_mask_view(path: Path) -> np.ndarray:
    labels = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    output = np.zeros((*labels.shape, 3), dtype=np.uint8)
    for component_id in np.unique(labels):
        if component_id == 0:
            continue
        hue = (int(component_id) * 37) % 180
        color = cv2.cvtColor(np.uint8([[[hue, 210, 240]]]), cv2.COLOR_HSV2RGB)[0, 0]
        output[labels == component_id] = color
    return output


def _object_mask_view(path: Path) -> np.ndarray:
    labels = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    colors = {
        0: (82, 86, 92),      # table
        1: (112, 146, 190),   # vessel floor/rim
        2: (250, 205, 74),    # marker/card
        3: (229, 119, 90),    # food
    }
    output = np.zeros((*labels.shape, 3), dtype=np.uint8)
    for value, color in colors.items():
        output[labels == value] = color
    return output


def _depth_view(path: Path) -> np.ndarray:
    depth = np.load(path, allow_pickle=False).astype(np.float32)
    valid = np.isfinite(depth) & (depth > 0)
    low_m, high_m = 0.15, 1.20
    scaled = np.clip((depth - low_m) / (high_m - low_m), 0, 1)
    grey = np.asarray(np.round(scaled * 255), dtype=np.uint8)
    colored = cv2.cvtColor(cv2.applyColorMap(grey, cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB)
    colored[~valid] = (0, 0, 0)
    return colored


def _geometry_view(path: Path, output_size: tuple[int, int] = (640, 480)) -> np.ndarray:
    with np.load(path, allow_pickle=False) as data:
        xyz = data["surface_xyz_world_mm"]
        obj = data["object_ids"]
        comp = data["component_ids"]
    sample_step = 3
    points = xyz[::sample_step, ::sample_step].reshape(-1, 3).astype(np.float64)
    obj_ids = obj[::sample_step, ::sample_step].reshape(-1)
    comp_ids = comp[::sample_step, ::sample_step].reshape(-1)
    # Deterministic isometric-style orthographic projection of stored world XYZ.
    sx = (points[:, 0] - points[:, 1]) / np.sqrt(2.0)
    sy = (points[:, 0] + points[:, 1]) / np.sqrt(6.0) - points[:, 2] * 0.82
    finite = np.isfinite(sx) & np.isfinite(sy)
    sx, sy, obj_ids, comp_ids = sx[finite], sy[finite], obj_ids[finite], comp_ids[finite]
    width, height = output_size
    margin = 22
    span_x = max(float(np.ptp(sx)), 1.0)
    span_y = max(float(np.ptp(sy)), 1.0)
    scale = min((width - 2 * margin) / span_x, (height - 2 * margin) / span_y)
    px = np.round((sx - float(sx.min())) * scale + margin).astype(int)
    py = np.round((float(sy.max()) - sy) * scale + margin).astype(int)
    inside = (px >= 0) & (px < width) & (py >= 0) & (py < height)
    px, py, obj_ids, comp_ids = px[inside], py[inside], obj_ids[inside], comp_ids[inside]
    canvas = np.full((height, width, 3), (248, 248, 246), dtype=np.uint8)
    palette = {
        0: (118, 122, 128),
        1: (100, 141, 190),
        2: (248, 191, 48),
    }
    colors = np.empty((len(px), 3), dtype=np.uint8)
    for index, (obj_id, comp_id) in enumerate(zip(obj_ids, comp_ids)):
        if int(obj_id) == 3 and int(comp_id) > 0:
            hue = (int(comp_id) * 37) % 180
            colors[index] = cv2.cvtColor(np.uint8([[[hue, 210, 240]]]),
                                         cv2.COLOR_HSV2RGB)[0, 0]
        else:
            colors[index] = palette.get(int(obj_id), (30, 30, 30))
    canvas[py, px] = colors
    return canvas


def _relative(path: Path, output_root: Path) -> str:
    return Path(os.path.relpath(path, output_root)).as_posix()


def _pair_inputs(manifest_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    pairs: dict[str, list[dict[str, Any]]] = {}
    for row in manifest_rows:
        pairs.setdefault(str(row["card_pair_id"]), []).append(row)
    return pairs


def _verify_pair(pilot_root: Path, pair_id: str,
                 members: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"pair_id": pair_id}
    if len(members) != 2 or {bool(row["card_present"]) for row in members} != {True, False}:
        return {**result, "passed": False, "error": "Expected one card-present and one card-absent scene"}
    present = next(row for row in members if row["card_present"])
    absent = next(row for row in members if not row["card_present"])
    p_cfg, a_cfg = dict(present["scene_parameters"]), dict(absent["scene_parameters"])
    p_anchor, a_anchor = dict(p_cfg.pop("anchor", {})), dict(a_cfg.pop("anchor", {}))
    p_flag, a_flag = p_anchor.pop("card", None), a_anchor.pop("card", None)
    scene_config_equal = p_cfg == a_cfg and p_anchor == a_anchor and (p_flag, a_flag) == (True, False)
    camera_equal = p_cfg.get("camera") == a_cfg.get("camera")
    lighting_equal = p_cfg.get("illumination") == a_cfg.get("illumination")
    background_equal = (p_cfg.get("table_color") == a_cfg.get("table_color")
                        and p_cfg.get("noise_sigma") == a_cfg.get("noise_sigma")
                        and p_cfg.get("vessel") == a_cfg.get("vessel")
                        and p_cfg.get("seed") == a_cfg.get("seed"))
    p_bundle = pilot_root / present["artifact_hashes"]["geometry_npz"]["path"]
    a_bundle = pilot_root / absent["artifact_hashes"]["geometry_npz"]["path"]
    with np.load(p_bundle, allow_pickle=False) as p, np.load(a_bundle, allow_pickle=False) as a:
        exact_arrays = ("food_class_mask", "component_ids", "component_mass_g",
                        "component_volume_ml", "component_density_g_ml", "camera_K",
                        "camera_R_wc", "camera_C_mm")
        food_geometry_equal = all(np.array_equal(p[name], a[name]) for name in exact_arrays)
        p_card = p["object_ids"] == 2
        a_card = a["object_ids"] == 2
        only_card_mask = p_card | a_card
        depth_same_outside = np.array_equal(p["depth_m"][~only_card_mask], a["depth_m"][~only_card_mask])
        xyz_same_outside = np.array_equal(
            p["surface_xyz_world_mm"][~only_card_mask], a["surface_xyz_world_mm"][~only_card_mask])
        card_label_valid = (np.any(p_card) and not np.any(a_card)
                            and present.get("marker", {}).get("marker_id") == 7
                            and present.get("marker", {}).get("marker_side_mm") == 60.0
                            and absent.get("marker") is None
                            and np.asarray(present.get("marker", {}).get("marker_corners_px", [])).shape == (4, 2)
                            and np.isfinite(np.asarray(
                                present.get("marker", {}).get("marker_corners_px", []), dtype=float)).all())
        image_p = _rgb(pilot_root / present["rgb_path"])
        image_a = _rgb(pilot_root / absent["rgb_path"])
    changed = np.any(image_p != image_a, axis=2)
    card_area = only_card_mask
    allowed = cv2.dilate(card_area.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    rgb_difference_confined_to_marker = not bool(np.any(changed & ~allowed))
    checks = {
        "scene_config_equal_except_anchor_card": bool(scene_config_equal),
        "camera_identical": bool(camera_equal),
        "lighting_identical": bool(lighting_equal),
        "background_vessel_noise_identical": bool(background_equal),
        "food_masks_geometry_mass_volume_density_identical": bool(food_geometry_equal),
        "metric_depth_identical_outside_card": bool(depth_same_outside),
        "world_geometry_identical_outside_card": bool(xyz_same_outside),
        "rgb_differences_confined_to_card_edge_tolerance": bool(rgb_difference_confined_to_marker),
        "ID7_60mm_only_present": bool(card_label_valid),
    }
    result.update({"passed": all(checks.values()), "checks": checks,
                   "card_present_sample_id": present["sample_id"],
                   "card_absent_sample_id": absent["sample_id"]})
    return result


def _write_review_csv(path: Path, pairs: list[dict[str, Any]],
                      verification: dict[str, dict[str, Any]]) -> None:
    fieldnames = [
        "review_id", "pair_id", "scene_kind", "card_present_scene_id", "card_absent_scene_id",
        "food_classes", "source_group_id", "automated_pair_check_status",
        "visual_quality_card_present", "visual_quality_card_absent", "pair_consistency_human",
        "shape_portion_plausibility_card_present", "shape_portion_plausibility_card_absent",
        "texture_color_specificity_card_present", "texture_color_specificity_card_absent",
        "food_distinguishability_card_present", "food_distinguishability_card_absent",
        "thali_believability_card_present", "thali_believability_card_absent",
        "artifacts_detected", "class_identity_card_present", "class_identity_card_absent",
        "segmentation_mask_card_present", "segmentation_mask_card_absent",
        "metric_depth_card_present", "metric_depth_card_absent",
        "geometry_volume_card_present", "geometry_volume_card_absent",
        "mass_density_provenance_card_present", "mass_density_provenance_card_absent",
        "mass_density_evidence_card_present", "mass_density_evidence_card_absent",
        "marker_detection_pose_card_present", "marker_detection_pose_card_absent",
        "rejection_reasons", "reviewer_comments", "retention_decision",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for index, pair in enumerate(pairs, 1):
            present = next(row for row in pair["members"] if row["card_present"])
            absent = next(row for row in pair["members"] if not row["card_present"])
            classes = sorted({annotation["class_name"] for row in pair["members"]
                              for annotation in row["annotations"]})
            row = {
                "review_id": f"review-{index:03d}",
                "pair_id": pair["pair_id"],
                "scene_kind": present["scene_kind"],
                "card_present_scene_id": present["scene_id"],
                "card_absent_scene_id": absent["scene_id"],
                "food_classes": "; ".join(classes),
                "source_group_id": present["source"]["source_group_id"],
                "automated_pair_check_status": ("PASS" if verification[pair["pair_id"]]["passed"] else "FAIL"),
                "visual_quality_card_present": "REVIEW_REQUIRED",
                "visual_quality_card_absent": "REVIEW_REQUIRED",
                "pair_consistency_human": "REVIEW_REQUIRED",
                "shape_portion_plausibility_card_present": "REVIEW_REQUIRED",
                "shape_portion_plausibility_card_absent": "REVIEW_REQUIRED",
                "texture_color_specificity_card_present": "REVIEW_REQUIRED",
                "texture_color_specificity_card_absent": "REVIEW_REQUIRED",
                "food_distinguishability_card_present": "REVIEW_REQUIRED",
                "food_distinguishability_card_absent": "REVIEW_REQUIRED",
                "thali_believability_card_present": ("REVIEW_REQUIRED" if present["scene_kind"] == "composed_thali" else "NOT_APPLICABLE"),
                "thali_believability_card_absent": ("REVIEW_REQUIRED" if absent["scene_kind"] == "composed_thali" else "NOT_APPLICABLE"),
                "artifacts_detected": "",
                "class_identity_card_present": "REVIEW_REQUIRED",
                "class_identity_card_absent": "REVIEW_REQUIRED",
                "segmentation_mask_card_present": "REVIEW_REQUIRED",
                "segmentation_mask_card_absent": "REVIEW_REQUIRED",
                "metric_depth_card_present": "REVIEW_REQUIRED",
                "metric_depth_card_absent": "REVIEW_REQUIRED",
                "geometry_volume_card_present": "REVIEW_REQUIRED",
                "geometry_volume_card_absent": "REVIEW_REQUIRED",
                "mass_density_provenance_card_present": "REVIEW_REQUIRED",
                "mass_density_provenance_card_absent": "REVIEW_REQUIRED",
                "mass_density_evidence_card_present": "; ".join(
                    f"{a['class_name']}: {a['mass_provenance'].get('density_g_ml')} g/ml; "
                    f"{a['mass_provenance'].get('density_source')}; "
                    f"range={a['mass_provenance'].get('sampled_from_range')}"
                    for a in present["annotations"]),
                "mass_density_evidence_card_absent": "; ".join(
                    f"{a['class_name']}: {a['mass_provenance'].get('density_g_ml')} g/ml; "
                    f"{a['mass_provenance'].get('density_source')}; "
                    f"range={a['mass_provenance'].get('sampled_from_range')}"
                    for a in absent["annotations"]),
                "marker_detection_pose_card_present": "REVIEW_REQUIRED",
                "marker_detection_pose_card_absent": "NOT_APPLICABLE",
                "rejection_reasons": "",
                "reviewer_comments": "",
                "retention_decision": "REVIEW_REQUIRED",
            }
            writer.writerow(row)


def _side_html(row: dict[str, Any], pilot_root: Path, output_root: Path,
               diagnostic_paths: dict[str, str]) -> str:
    image = pilot_root / row["rgb_path"]
    kind = "Card present — ID 7 / 60 mm" if row["card_present"] else "Card absent"
    panels = [("Original RGB", _relative(image, output_root))]
    panels.extend((title, diagnostic_paths[key]) for key, title in (
        ("class_mask", "Food-class mask"),
        ("component_mask", "Component IDs"),
        ("object_mask", "Object IDs"),
        ("depth", "Metric depth, 0.15–1.20 m"),
        ("geometry", "World-space geometry projection"),
    ))
    figures = "".join(
        f'<figure><img loading="lazy" src="{html.escape(src)}" alt="{html.escape(title)}">'
        f"<figcaption>{html.escape(title)}</figcaption></figure>"
        for title, src in panels
    )
    return (f'<section class="side"><h4>{html.escape(kind)}</h4>'
            f'<div class="diagnostics">{figures}</div>'
            f'<p class="idline">Scene: <code>{html.escape(row["scene_id"])}</code></p></section>')


def _build_html(path: Path, output_root: Path, pilot_root: Path,
                grouped_pairs: dict[str, list[dict[str, Any]]],
                diagnostic_paths: dict[str, dict[str, str]],
                verification: dict[str, dict[str, Any]], review_csv: Path) -> None:
    registry = load_class_registry()
    isolated: list[tuple[int, str, list[dict[str, Any]]]] = []
    thalis: list[tuple[int, str, list[dict[str, Any]]]] = []
    for members in grouped_pairs.values():
        card_row = next(row for row in members if row["card_present"])
        classes = [int(item["class_id"]) for item in card_row["annotations"]]
        target = isolated if card_row["scene_kind"] == "isolated_dish" else thalis
        class_id = classes[0] if card_row["scene_kind"] == "isolated_dish" else 999
        label = (registry[class_id].class_name if class_id in registry else
                 f"Thali {card_row['source']['source_group_id']}: {len(classes)} food classes")
        target.append((class_id, label, members))
    isolated.sort(key=lambda value: value[0])
    thalis.sort(key=lambda value: value[1])

    def section(title: str, anchor: str,
                pairs: list[tuple[int, str, list[dict[str, Any]]]]) -> str:
        blocks = []
        for _class_id, label, members in pairs:
            card = next(row for row in members if row["card_present"])
            no_card = next(row for row in members if not row["card_present"])
            pair_id = str(card["card_pair_id"])
            classes = sorted({annotation["class_name"] for row in members
                              for annotation in row["annotations"]})
            report = verification[pair_id]
            badge = "PASS" if report["passed"] else "FAIL"
            checks = "".join(f'<li><b>{"PASS" if value else "FAIL"}</b> {html.escape(key.replace("_", " "))}</li>'
                              for key, value in report["checks"].items())
            sides = (_side_html(card, pilot_root, output_root, diagnostic_paths[card["sample_id"]])
                     + _side_html(no_card, pilot_root, output_root,
                                  diagnostic_paths[no_card["sample_id"]]))
            classes_text = ", ".join(classes)
            physical_rows = []
            for annotation in card["annotations"]:
                provenance = annotation["mass_provenance"]
                physical_rows.append(
                    f'<li>component {int(annotation["labels"]["component_id"])} — '
                    f'<strong>{html.escape(annotation["class_name"])}</strong>: '
                    f'{float(annotation["mass_g"]):.2f} g · '
                    f'{float(annotation["labels"]["volume_ml"]):.2f} ml · '
                    f'{float(provenance["density_g_ml"]):.3f} g/ml; '
                    f'{html.escape(str(provenance.get("density_source")))}; '
                    f'{html.escape(str(provenance.get("sampled_from_range")))} '
                    f'({html.escape(str(provenance.get("sampled_from_range_kind")))})</li>')
            physical_details = (
                '<details><summary>Physical labels and density provenance</summary><ul>'
                + "".join(physical_rows) + "</ul></details>")
            marker = card.get("marker")
            marker_details = (f'<p>Marker label: {html.escape(str(marker.get("dictionary")))} '
                              f'id {int(marker.get("marker_id", -1))}, '
                              f'{float(marker.get("marker_side_mm", 0)):.1f} mm; '
                              f'tilt={float(marker.get("tilt_deg", 0)):.1f}°; '
                              f'cm/px={float(marker.get("cm_per_px", 0)):.6f}; '
                              f'corners={html.escape(str(marker.get("marker_corners_px")))}</p>'
                              if marker else '<p>Marker label: not present in this no-card scene.</p>')
            blocks.append(
                f'<article class="pair" id="{html.escape(pair_id)}">'
                f'<header><div><span class="kind">{html.escape(card["scene_kind"])}</span>'
                f'<h3>{html.escape(label)}</h3><p>{html.escape(classes_text)}</p>'
                f'<code>{html.escape(pair_id)}</code></div>'
                f'<span class="badge {badge.lower()}">Automated pair: {badge}</span></header>'
                f'<div class="pair-sides">{sides}</div>'
                f'<details><summary>Matched-pair checks</summary><ul>{checks}</ul></details>'
                f'{physical_details}'
                f'<details><summary>Marker geometry label</summary>{marker_details}</details>'
                f'<p class="review-prompt">Human review: <strong>REVIEW_REQUIRED</strong>. '
                f'Enter decisions in <code>{html.escape(review_csv.name)}</code>.</p>'
                f'</article>')
        return f'<section id="{anchor}"><h2>{title} <small>({len(pairs)})</small></h2>{"".join(blocks)}</section>'

    relative_csv = _relative(review_csv, output_root)
    legend = "".join(
        f'<span><i style="background:#{"".join(f"{value:02x}" for value in _class_color(class_id))}"></i>'
        f'{class_id}: {html.escape(params.class_name)}</span>'
        for class_id, params in registry.items())
    content = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NutriSense synthetic pilot visual review</title>
<style>
:root{{color-scheme:light;--ink:#18221e;--muted:#64716a;--line:#d8ded9;--paper:#f4f6f2;--panel:#fff;--accent:#2c604b;--warn:#8a5b00}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}}
header.hero{{padding:28px max(20px,calc((100vw - 1500px)/2));background:#173b30;color:#f5f7f4}}
header.hero h1{{margin:0 0 8px;font-size:clamp(24px,3vw,38px)}}header.hero p{{max-width:1000px;color:#d1ddd5}}
nav{{position:sticky;top:0;z-index:5;display:flex;gap:18px;padding:12px 24px;background:#fff;border-bottom:1px solid var(--line)}}nav a{{color:var(--accent);font-weight:650;text-decoration:none}}
.legend{{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:6px;padding:12px;border:1px solid var(--line);border-radius:12px;background:#fff;margin:14px 0 22px}}.legend span{{font-size:12px;color:var(--muted)}}.legend i{{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px;vertical-align:-1px}}
.criteria{{background:#fff;border:1px solid var(--line);padding:12px 16px;border-radius:12px;margin:14px 0}}.criteria li{{margin:4px 0}}
main{{max-width:1580px;margin:auto;padding:22px}}.warning{{background:#fff4d6;border:1px solid #e2c370;border-radius:12px;padding:14px 18px;margin-bottom:24px}}
h2{{font-size:26px;margin:40px 0 16px}}h2 small{{color:var(--muted);font-size:16px}}.pair{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:18px;margin:0 0 24px;box-shadow:0 4px 16px #24382b0b}}
.pair>header{{display:flex;justify-content:space-between;gap:15px;align-items:flex-start;border-bottom:1px solid var(--line);padding-bottom:12px;margin-bottom:14px}}
.pair h3{{font-size:20px;margin:2px 0}}.pair p{{margin:3px 0;color:var(--muted)}}.kind{{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);font-weight:750}}
.badge{{padding:6px 10px;border-radius:999px;font-weight:750;background:#e7eee9;color:var(--accent);white-space:nowrap}}.badge.fail{{background:#fde5e1;color:#a33424}}
.pair-sides{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}.side{{border:1px solid var(--line);border-radius:14px;padding:12px;min-width:0}}.side h4{{margin:0 0 10px;font-size:16px}}
.diagnostics{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}}figure{{margin:0;min-width:0;background:#f0f2ef;border-radius:8px;overflow:hidden}}figure img{{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#eceeeb}}figcaption{{padding:5px 7px;color:var(--muted);font-size:11px}}
.idline{{font-size:12px!important;margin-top:10px!important}}details{{margin-top:12px}}summary{{cursor:pointer;font-weight:700;color:var(--accent)}}details ul{{columns:2;padding-left:22px;color:var(--muted)}}details li{{break-inside:avoid;margin:4px 0;font-size:13px}}.review-prompt{{border-top:1px dashed var(--line);padding-top:10px;font-size:13px}}
.review-prompt strong{{color:var(--warn)}}code{{font-size:.9em;overflow-wrap:anywhere}}
@media(max-width:900px){{.pair-sides{{grid-template-columns:1fr}}.diagnostics{{grid-template-columns:repeat(2,minmax(0,1fr))}}main{{padding:14px}}}}
@media(max-width:500px){{.diagnostics{{grid-template-columns:1fr 1fr}}.pair>header{{display:block}}.badge{{display:inline-block;margin-top:8px}}nav{{gap:12px;padding:10px 14px;flex-wrap:wrap}}}}
</style></head><body>
<header class="hero"><h1>Synthetic renderer pilot — visual review</h1>
<p>44 matched pairs · 41 isolated WED classes · 3 composed thalis · 88 original pilot renders. Diagnostics are derived from the existing labels; no new food scenes were generated.</p>
<p>Visual and task decisions remain <strong>REVIEW_REQUIRED</strong>. Automated checks are shown separately and do not approve appearance or physical validity.</p></header>
<nav><a href="#isolated">41 isolated classes</a><a href="#thalis">3 composed thalis</a><a href="{html.escape(relative_csv)}">Review CSV</a></nav>
<main><div class="warning"><strong>Review focus:</strong> generic smooth mounds, class-specific texture/color, artificial angular thali boundaries, food distinguishability, rendering artifacts, and whether each physical label is independently credible.</div>
<details class="criteria"><summary>Human review criteria</summary><ul><li>Does the appearance match its assigned WED class?</li><li>Are shape and portion plausible?</li><li>Are texture and color class-specific enough?</li><li>Are there smooth mounds, primitive shapes, angular boundaries, or rendering artifacts?</li><li>Are the thali compositions believable and food items distinguishable?</li><li>Check masks, depth, 3D volume, density provenance, and marker pose independently from visual realism.</li></ul></details>
<details class="criteria"><summary>Food-class mask color legend</summary><div class="legend">{legend}</div><p>Component IDs use separate deterministic hues. Object IDs: grey=table, blue=vessel, yellow=card, coral=food. Depth uses the fixed 0.15–1.20 m scale.</p></details>
{section("Isolated food classes", "isolated", isolated)}
{section("Composed thali scenes", "thalis", thalis)}
</main></body></html>'''
    path.write_text(content, encoding="utf-8")


def build_review_package(pilot_root: Path, output_root: Path) -> dict[str, Any]:
    manifest_path = pilot_root / "manifest.jsonl"
    validation_path = pilot_root / "pilot_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    if not validation.get("all_automated_checks_passed"):
        raise ValueError("The source pilot has automated failures; review package will not hide them")
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    pairs = _pair_inputs(rows)
    output_root.mkdir(parents=True, exist_ok=True)
    diagnostics: dict[str, dict[str, str]] = {}
    for row in rows:
        sample_id = str(row["sample_id"])
        artifacts = row["artifact_hashes"]
        visual_root = output_root / "visuals" / sample_id
        paths = {
            "class_mask": visual_root / "food_class_mask.png",
            "component_mask": visual_root / "component_ids.png",
            "object_mask": visual_root / "object_ids.png",
            "depth": visual_root / "metric_depth.png",
            "geometry": visual_root / "world_geometry.png",
        }
        _save_rgb(paths["class_mask"], _class_mask_view(pilot_root / artifacts["class_mask"]["path"]))
        _save_rgb(paths["component_mask"], _component_mask_view(
            pilot_root / artifacts["component_ids"]["path"]))
        _save_rgb(paths["object_mask"], _object_mask_view(
            pilot_root / artifacts["object_ids"]["path"]))
        _save_rgb(paths["depth"], _depth_view(pilot_root / artifacts["metric_depth"]["path"]))
        _save_rgb(paths["geometry"], _geometry_view(
            pilot_root / artifacts["geometry_npz"]["path"]))
        diagnostics[sample_id] = {key: _relative(path, output_root) for key, path in paths.items()}

    verification = {pair_id: _verify_pair(pilot_root, pair_id, members)
                    for pair_id, members in sorted(pairs.items())}
    verification_report = {
        "pilot_manifest_sha256": sha256_file(manifest_path),
        "pilot_validation_sha256": sha256_file(validation_path),
        "pair_count": len(verification),
        "passed_pair_count": sum(bool(value["passed"]) for value in verification.values()),
        "failed_pair_count": sum(not bool(value["passed"]) for value in verification.values()),
        "human_pair_decisions": "REVIEW_REQUIRED",
        "checks": verification,
        "review_states": list(STATUS_VALUES),
    }
    (output_root / "pair_verification.json").write_text(
        json.dumps(verification_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    review_csv = output_root / "review_sheet.csv"
    grouped_pairs = [{"pair_id": pair_id, "members": members}
                     for pair_id, members in sorted(pairs.items())]
    _write_review_csv(review_csv, grouped_pairs, verification)
    _build_html(output_root / "index.html", output_root, pilot_root, pairs,
                diagnostics, verification, review_csv)

    classes = {annotation["class_id"] for row in rows if row["scene_kind"] == "isolated_dish"
               for annotation in row["annotations"]}
    package = {
        "package_version": 1,
        "pilot_root": str(pilot_root),
        "pilot_manifest_sha256": verification_report["pilot_manifest_sha256"],
        "pilot_validation_sha256": verification_report["pilot_validation_sha256"],
        "gallery": "index.html",
        "review_sheet": "review_sheet.csv",
        "pair_verification": "pair_verification.json",
        "scene_count": len(rows),
        "pair_count": len(pairs),
        "isolated_class_count": len(classes),
        "composed_thali_pair_count": sum(
            next(row for row in members if row["card_present"])["scene_kind"] == "composed_thali"
            for members in pairs.values()),
        "automated_pair_pass_count": verification_report["passed_pair_count"],
        "human_review_status": "REVIEW_REQUIRED",
        "source_pilot_modified": False,
        "new_synthetic_scenes_generated": False,
        "production_model_training_started": False,
        "gan_diffusion_started": False,
        "protected_data_accessed": False,
    }
    (output_root / "package_manifest.json").write_text(
        json.dumps(package, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_readme(output_root, package, verification_report)
    return package


def _write_readme(output_root: Path, package: dict[str, Any],
                  verification: dict[str, Any]) -> None:
    text = f'''# Synthetic pilot human review package

This directory is a separate visual review package for the existing renderer
pilot. The source pilot manifest and validation artifacts were not modified.

## Open the gallery

Open `index.html` in a browser. It has all {package['isolated_class_count']} isolated
classes and {package['composed_thali_pair_count']} composed thali pairs. For every
pair it places card-present and card-absent scenes side by side, each with the
original RGB, food-class mask, component mask, object mask, metric-depth view,
and world-space geometry projection.

The depth color scale is fixed at 0.15–1.20 m. The 3D geometry panel is a
deterministic orthographic projection of renderer-provided world XYZ; it is a
diagnostic view, not a new geometry estimate.

## Fill the review sheet

Edit `review_sheet.csv`. Valid status values are `PASS`, `FAIL`, and
`REVIEW_REQUIRED`. The `automated_pair_check_status` column records software
checks only. Leave any human decision `REVIEW_REQUIRED` until a person has
visually inspected it. `marker_detection_pose_card_absent` is
`NOT_APPLICABLE` because the no-card view intentionally has no marker.

Evaluate identity/appearance, shape and portion plausibility, texture/color,
artifacts, mask alignment, metric depth, 3D geometry/volume, mass-density
provenance, marker pose, thali believability, and whether foods are visually
distinguishable. Realistic-looking RGB does not by itself validate physical
labels. Record failed dimensions and reasons separately, and set a retention
decision only after review.

## Automated matched-pair audit

`pair_verification.json` independently compares scene configuration,
camera, illumination, background/noise, masks, component mass/volume/density,
depth and world geometry outside the projected card area, RGB difference
extent, and marker presence. Results: {verification['passed_pair_count']}/
{verification['pair_count']} automated pairs pass. Human pair consistency still
requires review.

Source pilot manifest SHA-256: `{package['pilot_manifest_sha256']}`  
Source pilot validation SHA-256: `{package['pilot_validation_sha256']}`

The package adds diagnostic visualizations only; it generates no new food
scenes, does not train models, and uses no DEV, LOCKED, ArUco evaluation, or WED
test data.
'''
    (output_root / "README.md").write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--baseline-report", type=Path,
                        default=ROOT / "experiments/synthetic_food/baseline_freeze.json")
    args = parser.parse_args()
    try:
        require_frozen_baseline(args.baseline_report)
        package = build_review_package(args.pilot, args.output)
    except (ValueError, json.JSONDecodeError, FileNotFoundError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(package, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
