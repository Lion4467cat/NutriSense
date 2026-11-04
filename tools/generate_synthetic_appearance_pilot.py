"""Generate a small class-specific appearance pilot from eligible WED TRAIN only."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw

from nutrisense_synth.appearance import build_train_appearance_profiles
from nutrisense_synth.manifest import sha256_file, stable_id
from nutrisense_synth.parameters import (eligible_wed_train_rows, load_class_registry,
                                         read_wed_train_manifest, wed_group_id)
from nutrisense_synth.pilot import _density_for, _persist_scene, _source_record, _class_sources
from nutrisense_synth.quality import check_card_pair, findings_to_dict
from nutrisense_synth.scene import build_class_scene, build_thali_scene, render_card_pair


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "datasets/processed/synthetic_food_appearance_pilot_20261103"
PILOT_CLASSES = (1, 12, 26, 28, 32, 34)
THALI_CLASSES = (34, 1, 26, 32)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
                    encoding="utf-8")


def _save_reference(root: Path, row: dict[str, Any], class_id: int,
                    dataset_root: Path) -> dict[str, Any]:
    """Save a labeled crop only after TRAIN and DEV-group eligibility is established."""
    if row.get("split") != "train":
        raise ValueError("Appearance references must be TRAIN rows")
    image_path, mask_path = dataset_root / str(row["image"]), dataset_root / str(row["mask"])
    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    mask = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
    if image is None or mask is None:
        raise FileNotFoundError(f"Cannot read eligible TRAIN reference for class {class_id}")
    if mask.ndim == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGRA2GRAY if mask.shape[2] == 4 else cv2.COLOR_BGR2GRAY)
    if mask.shape != image.shape[:2]:
        mask = cv2.resize(mask, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
    selected = mask == class_id
    if int(selected.sum()) < 100:
        raise ValueError(f"Eligible TRAIN reference for class {class_id} has too few mask pixels")
    ys, xs = np.where(selected)
    pad = max(12, int(0.08 * max(xs.max() - xs.min(), ys.max() - ys.min())))
    x0, x1 = max(0, int(xs.min()) - pad), min(image.shape[1], int(xs.max()) + pad + 1)
    y0, y1 = max(0, int(ys.min()) - pad), min(image.shape[0], int(ys.max()) + pad + 1)
    crop = image[y0:y1, x0:x1]
    crop_mask = selected[y0:y1, x0:x1]
    color = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    overlay = color.copy()
    overlay[crop_mask] = (0.55 * overlay[crop_mask] + 0.45 * np.array([45, 202, 132])).astype(np.uint8)
    target = root / "references" / f"class_{class_id:02d}"
    target.mkdir(parents=True, exist_ok=True)
    Image.fromarray(color).save(target / "wed_train_crop.png")
    Image.fromarray(overlay).save(target / "wed_train_mask_overlay.png")
    info = {
        "class_id": class_id, "source_split": "eligible WED TRAIN only",
        "source_group_id": wed_group_id(row), "source_record_id": row["image"],
        "source_mask_record_id": row["mask"], "source_image_sha256": sha256_file(image_path),
        "source_mask_sha256": sha256_file(mask_path), "crop_xyxy": [x0, y0, x1, y1],
        "cropped_class_pixels": int(crop_mask.sum()),
        "note": "Reference crop/overlay is for human appearance review; source pixels are not pasted into rendered output.",
    }
    _write_json(target / "source.json", info)
    return {**info, "crop_path": (target / "wed_train_crop.png").relative_to(root).as_posix(),
            "mask_overlay_path": (target / "wed_train_mask_overlay.png").relative_to(root).as_posix()}


def _diagnostics(root: Path, sample: dict[str, Any], scene: dict[str, Any]) -> dict[str, str]:
    out = root / "diagnostics" / sample["sample_id"]
    out.mkdir(parents=True, exist_ok=True)
    class_mask = np.zeros(scene["mask_food"].shape, dtype=np.uint8)
    for index, annotation in enumerate(sample["annotations"], 1):
        class_mask[scene["comp_ids"] == index] = int(annotation["class_id"])
    Image.fromarray(class_mask).save(out / "food_class_mask.png")
    Image.fromarray(scene["comp_ids"]).save(out / "component_ids.png")
    Image.fromarray(scene["obj_ids"]).save(out / "object_ids.png")
    depth = scene["depth_m"].copy()
    valid = scene["mask_food"]
    depth_view = np.zeros(depth.shape, dtype=np.uint8)
    if valid.any():
        lo, hi = np.quantile(depth[valid], [0.02, 0.98])
        depth_view[valid] = np.clip((depth[valid] - lo) / max(hi - lo, 1e-6) * 255, 0, 255)
    Image.fromarray(cv2.applyColorMap(depth_view, cv2.COLORMAP_TURBO)[:, :, ::-1]).save(out / "metric_depth_visualization.png")
    height = scene["surface_height_mm"].copy()
    geometry = np.zeros(height.shape, dtype=np.uint8)
    vals = height[valid]
    if vals.size:
        lo, hi = np.quantile(vals, [0.02, 0.98])
        geometry[valid] = np.clip((height[valid] - lo) / max(hi - lo, 1e-6) * 255, 0, 255)
    Image.fromarray(cv2.applyColorMap(geometry, cv2.COLORMAP_VIRIDIS)[:, :, ::-1]).save(out / "surface_height_visualization.png")
    return {key: (out / name).relative_to(root).as_posix() for key, name in {
        "class_mask": "food_class_mask.png", "component_ids": "component_ids.png",
        "object_ids": "object_ids.png", "metric_depth": "metric_depth_visualization.png",
        "geometry": "surface_height_visualization.png"}.items()}


def _render_pair(root: Path, scene_cfg: dict[str, Any], *, scene_kind: str,
                 seed: int, pair_id: str, source: dict[str, Any],
                 components: list[dict[str, Any]], density_provenance: dict[int, dict[str, Any]],
                 portion_tags: dict[int, str], profile_hashes: dict[int, str]) -> list[dict[str, Any]]:
    present, absent = render_card_pair(scene_cfg)
    pair_checks = check_card_pair(present, absent)
    pair_ok = all(finding.passed for finding in pair_checks)
    rows = []
    for pair_index, scene in enumerate((present, absent)):
        sample = _persist_scene(root, scene, scene_kind=scene_kind, seed=seed,
                                pair_id=pair_id, pair_index=pair_index, source=source,
                                components=components, density_provenance=density_provenance,
                                portion_tags=portion_tags, scene_profile_hashes=profile_hashes)
        sample["method_revision"] = "class_surface_v1"
        sample["quality"].update({
            "card_pair_checks": findings_to_dict(pair_checks),
            "pair_checks_pending": False,
            "automated_pass": bool(sample["quality"]["automated_pass"] and pair_ok),
            "visual_identity": "REVIEW_REQUIRED",
            "photorealism": "REVIEW_REQUIRED",
            "physical_label_validity": "PASS" if sample["quality"]["automated_pass"] and pair_ok else "FAIL",
        })
        sample["review_dimensions"] = {
            "visual_identity": "REVIEW_REQUIRED", "photorealism": "REVIEW_REQUIRED",
            "physical_labels": "PASS" if sample["quality"]["automated_pass"] and pair_ok else "FAIL",
            "matched_pair_consistency": "PASS" if pair_ok else "FAIL",
            "automated_task_checks": "PASS" if sample["quality"]["automated_pass"] else "FAIL",
            "human_approval": "PENDING",
        }
        rows.append((sample, scene))
    rows[0][0]["paired_sample_id"] = rows[1][0]["sample_id"]
    rows[1][0]["paired_sample_id"] = rows[0][0]["sample_id"]
    for sample, scene in rows:
        sample["diagnostics"] = _diagnostics(root, sample, scene)
    return [sample for sample, _ in rows]


def validate_appearance_pilot(output_root: Path, eligible_groups: set[str]) -> dict[str, Any]:
    rows = [json.loads(line) for line in (output_root / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    errors: list[str] = []
    if len(rows) != 14 or len({row["sample_id"] for row in rows}) != len(rows):
        errors.append("expected 14 unique samples for seven paired scenes")
    pairs: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        pairs.setdefault(str(row["card_pair_id"]), []).append(row)
        source = row["source"]
        ancestors = source.get("source_group_ids", [source.get("source_group_id")])
        if not ancestors or not set(ancestors).issubset(eligible_groups):
            errors.append(f"{row['sample_id']}: source lineage is outside eligible TRAIN groups")
        if source.get("source_split") != "train":
            errors.append(f"{row['sample_id']}: source split is not TRAIN")
        if row.get("quality", {}).get("human_review") != "pending":
            errors.append(f"{row['sample_id']}: human review should remain pending")
        for name, artifact in row.get("artifact_hashes", {}).items():
            path = output_root / artifact["path"]
            if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
                errors.append(f"{row['sample_id']}: {name} missing or hash mismatch")
        try:
            with np.load(output_root / row["artifact_hashes"]["geometry_npz"]["path"], allow_pickle=False) as bundle:
                food = bundle["food_class_mask"] > 0
                if not (np.array_equal(food, bundle["component_ids"] > 0)
                        and np.array_equal(food, bundle["object_ids"] == 3)):
                    errors.append(f"{row['sample_id']}: visible food labels do not align")
                if not np.isfinite(bundle["depth_m"]).all() or np.any(bundle["depth_m"] <= 0):
                    errors.append(f"{row['sample_id']}: metric depth must be finite and positive")
                mass, volume, density = (bundle[key].astype(float) for key in
                                         ("component_mass_g", "component_volume_ml", "component_density_g_ml"))
                if not np.allclose(mass, volume * density, rtol=1e-6, atol=1e-3):
                    errors.append(f"{row['sample_id']}: mass does not equal volume times density")
        except (OSError, ValueError, KeyError) as exc:
            errors.append(f"{row['sample_id']}: cannot read geometry artifacts: {exc}")
    for pair_id, members in pairs.items():
        if len(members) != 2 or {bool(row["card_present"]) for row in members} != {True, False}:
            errors.append(f"{pair_id}: expected one card-present and one card-absent sample")
            continue
        for row in members:
            if not all(item["passed"] for item in row["quality"].get("card_pair_checks", [])):
                errors.append(f"{pair_id}: pair consistency check failed")
    report = {
        "sample_count": len(rows), "pair_count": len(pairs), "errors": errors,
        "automated_result": "PASS" if not errors else "FAIL",
        "human_visual_identity": "REVIEW_REQUIRED",
        "human_photorealism": "REVIEW_REQUIRED",
        "human_approval": "PENDING",
        "protected_splits_accessed": False,
        "full_corpus_generated": False,
    }
    _write_json(output_root / "pilot_validation.json", report)
    return report


def generate_appearance_pilot(manifest: Path, dataset_root: Path, output_root: Path,
                               seed: int = 20261104,
                               image_size: tuple[int, int] = (800, 600)) -> dict[str, Any]:
    # Parse TRAIN JSONL and remove the fixed DEV carve before opening any image.
    source_rows = eligible_wed_train_rows(read_wed_train_manifest(manifest))
    eligible_groups = {wed_group_id(row) for row in source_rows}
    profiles = build_train_appearance_profiles(manifest, dataset_root)
    sources = _class_sources(source_rows)
    registry = load_class_registry()
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "appearance_profiles.json").write_text(
        json.dumps({str(key): value for key, value in profiles.items()}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    manifest_rows: list[dict[str, Any]] = []
    reference_rows = {}
    selected: dict[int, tuple[dict[str, Any], dict[str, Any]]] = {}
    density_by_class: dict[int, tuple[float, dict[str, Any]]] = {}

    for class_id in PILOT_CLASSES:
        params = registry[class_id]
        candidates = sources[class_id]
        if not candidates:
            raise ValueError(f"No eligible TRAIN mass/source for {params.class_name}")
        row, dish = candidates[len(candidates) // 2]
        if wed_group_id(row) not in eligible_groups:
            raise ValueError("Selected source escaped eligible TRAIN groups")
        selected[class_id] = (row, dish)
        reference_rows[class_id] = _save_reference(output_root, row, class_id, dataset_root)
        class_seed = int(hashlib.sha256(f"{seed}:{wed_group_id(row)}:{class_id}:appearance".encode()).hexdigest()[:8], 16)
        grams = float(dish["weight_g"])
        density, density_prov = _density_for(class_id, class_seed)
        density_by_class[class_id] = (density, density_prov)
        component = {"class_id": class_id, "name": params.class_name, "grams": grams}
        source = _source_record(row, dataset_root)
        pair_id = stable_id("appearance", source["source_group_id"], class_id, class_seed, prefix="pair-")
        cfg = build_class_scene(class_id, params.class_name, grams, density,
                                seed=class_seed, card_present=True, size=image_size,
                                appearance_profile=profiles[class_id],
                                surface_model="class_surface_v1")
        pair_rows = _render_pair(
            output_root, cfg, scene_kind="isolated_dish", seed=class_seed,
            pair_id=pair_id, source=source, components=[component],
            density_provenance={class_id: density_prov},
            portion_tags={class_id: "eligible_wed_train_observed"},
            profile_hashes={class_id: profiles[class_id]["profile_sha256"]})
        for sample in pair_rows:
            sample["train_reference"] = reference_rows[class_id]
        manifest_rows.extend(pair_rows)

    # Compose four distinct dishes, each with independently traced TRAIN appearance/portion evidence.
    thali_parts, thali_source_records = [], {}
    density_provenance, portion_tags, profile_hashes = {}, {}, {}
    for class_id in THALI_CLASSES:
        row, dish = selected[class_id]
        density, prov = density_by_class[class_id]
        params = registry[class_id]
        thali_parts.append({"class_id": class_id, "grams": float(dish["weight_g"]),
                            "density_g_ml": density})
        thali_source_records[str(class_id)] = _source_record(row, dataset_root)
        density_provenance[class_id] = prov
        portion_tags[class_id] = "eligible_wed_train_observed"
        profile_hashes[class_id] = profiles[class_id]["profile_sha256"]
    group_ids = sorted({value["source_group_id"] for value in thali_source_records.values()})
    composite_id = "composite-" + hashlib.sha256("|".join(group_ids).encode()).hexdigest()[:20]
    thali_source = {
        "source": "wed", "source_split": "train", "source_group_id": composite_id,
        "source_group_ids": group_ids,
        "component_source_records": thali_source_records,
        "source_record_id": "composite_of_eligible_train_examples",
        "source_net_food_mass_only": True,
        "lineage_note": "Each component appearance and observed portion uses its own eligible TRAIN group; no DEV/test/ArUco data used.",
    }
    thali_seed = int(hashlib.sha256(f"{seed}:class_surface:thali".encode()).hexdigest()[:8], 16)
    thali_cfg = build_thali_scene(thali_parts, seed=thali_seed, card_present=True,
                                  size=image_size, appearance_profiles=profiles,
                                  surface_model="class_surface_v1")
    label_components = [dict(item, name=registry[int(item["class_id"])].class_name)
                        for item in thali_parts]
    pair_rows = _render_pair(
        output_root, thali_cfg, scene_kind="composed_thali", seed=thali_seed,
        pair_id=stable_id("appearance-thali", group_ids, thali_seed, prefix="pair-"),
        source=thali_source, components=label_components,
        density_provenance=density_provenance, portion_tags=portion_tags,
        profile_hashes=profile_hashes)
    for sample in pair_rows:
        sample["train_references"] = {str(class_id): reference_rows[class_id] for class_id in THALI_CLASSES}
    manifest_rows.extend(pair_rows)

    with (output_root / "manifest.jsonl").open("w", encoding="utf-8") as stream:
        for row in manifest_rows:
            stream.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    validation = validate_appearance_pilot(output_root, eligible_groups)
    summary = {
        "pilot_version": 2, "renderer_revision": "class_surface_v1",
        "seed": seed, "split_used": "eligible WED TRAIN only; seed-42 DEV groups removed before image access",
        "classes": [{"class_id": i, "class_name": registry[i].class_name,
                     "archetype": __import__("nutrisense_synth.food_models", fromlist=["style_for"]).style_for(registry[i].class_name).model,
                     "source_group_id": reference_rows[i]["source_group_id"]} for i in PILOT_CLASSES],
        "isolated_classes": len(PILOT_CLASSES), "composed_thali_scenes": 1,
        "scene_pairs": len(manifest_rows) // 2, "rendered_images": len(manifest_rows),
        "automated_pass_count": sum(bool(row["quality"]["automated_pass"]) for row in manifest_rows),
        "validation_result": validation["automated_result"],
        "validation_errors": validation["errors"],
        "human_review_status": "pending; no visual identity or photorealism approval implied",
        "visual_identity_assessment": "REVIEW_REQUIRED",
        "photorealism_assessment": "REVIEW_REQUIRED",
        "physical_label_checks": "renderer-integrated geometry/volume/mass and task-specific automated checks; assumptions remain explicit",
        "promotion_status": "blocked_pending_human_review",
        "no_production_training": True, "no_gan_or_diffusion": True,
        "full_corpus_generation": False, "locked_accessed": False,
        "aruco_evaluation_accessed": False, "wed_test_accessed": False,
        "wed_dev_images_used": False,
        "limitations": [
            "Procedural ingredient forms and materials are a renderer hypothesis, not photorealistic ground truth.",
            "WED semantic masks do not provide ingredient-instance labels; ingredient microgeometry is inside the parent class region.",
            "Density is cited where a direct reference applies and otherwise explicitly assumed with uncertainty.",
            "Photographic texture/color statistics guide palette only; WED pixels are not copied into generated scenes.",
        ],
    }
    _write_json(output_root / "pilot_summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--dataset-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=20261104)
    args = parser.parse_args()
    print(json.dumps(generate_appearance_pilot(args.manifest, args.dataset_root,
                                              args.out, args.seed), indent=2))


if __name__ == "__main__":
    main()
