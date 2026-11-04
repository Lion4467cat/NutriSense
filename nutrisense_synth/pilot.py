"""Small renderer-only pilot: 41 isolated classes plus composed WED thalis."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import cv2
from PIL import Image, ImageDraw

from nutrisense_synth.appearance import build_train_appearance_profiles
from nutrisense_synth.manifest import sha256_file, stable_id
from nutrisense_synth.parameters import (eligible_wed_train_rows, load_class_registry,
                                         DEFAULT_MANIFEST, read_wed_train_manifest, wed_group_id)
from nutrisense_synth.quality import check_card_pair, check_scene, findings_to_dict
from nutrisense_synth.review import write_review_queue
from nutrisense_synth.scene import build_class_scene, build_thali_scene, render_card_pair


def _save_image(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array).save(path)


def _write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def _density_for(class_id: int, seed: int) -> tuple[float, dict[str, Any]]:
    params = load_class_registry()[class_id]
    evidence = params.mass_provenance()
    configured_low, configured_high = evidence["uncertainty_range"]
    # Steamed rice has an actual state match in the cited table with two
    # reported values. Other rows are analogues or absent foods, so their
    # wider bounds remain explicit project assumptions.
    exact_reference = next((item for item in evidence["density_evidence"]
                            if item.get("generic_id") == "rice_boiled"
                            and item.get("reference_range_g_ml")), None)
    if params.class_name == "steamed-rice" and exact_reference:
        low, high = map(float, exact_reference["reference_range_g_ml"])
        range_kind = "cited FAO/INFOODS reference range for boiled white rice"
    else:
        low, high = float(configured_low), float(configured_high)
        range_kind = "project-assumed uncertainty interval around configured class prior"
    rng = np.random.default_rng(seed ^ (class_id * 2654435761))
    chosen = float(rng.uniform(low, high))
    evidence.update({
        "density_g_ml": chosen,
        "configured_center_g_ml": params.density_g_ml,
        "sampled_from_range": [float(low), float(high)],
        "sampled_from_range_kind": range_kind,
        "configured_assumption_range_g_ml": [float(configured_low), float(configured_high)],
        "assumption_status": "assumed_not_measured",
        "evidence_kind": "FAO direct/analogue cross-reference where available; otherwise project class assumption",
    })
    return chosen, evidence


def _source_record(row: dict[str, Any], dataset_root: Path) -> dict[str, Any]:
    if row.get("split") != "train":
        raise ValueError("Pilot accepts only eligible WED TRAIN rows")
    image_path = dataset_root / str(row["image"])
    mask_path = dataset_root / str(row["mask"])
    return {
        "source": "wed",
        "source_split": "train",
        "source_group_id": wed_group_id(row),
        "source_record_id": str(row["image"]),
        "source_image_sha256": sha256_file(image_path),
        "source_annotation_sha256": sha256_file(mask_path),
        "source_net_food_mass_only": True,
    }


def _persist_scene(output_root: Path, scene: dict[str, Any], *, scene_kind: str,
                   seed: int, pair_id: str, pair_index: int,
                   source: dict[str, Any], components: list[dict[str, Any]],
                   density_provenance: dict[int, dict[str, Any]],
                   portion_tags: dict[int, str], scene_profile_hashes: dict[int, str]) -> dict[str, Any]:
    card = bool(scene["cfg"]["anchor"]["card"])
    scene_id = stable_id(pair_id, "card" if card else "no-card", prefix="scene-")
    sample_id = stable_id(scene_id, prefix="sample-")
    base = Path("scenes") / scene_kind / sample_id
    image_rel = base / "rgb.png"
    mask_rel = base / "food_class_mask.png"
    component_rel = base / "component_ids.png"
    object_rel = base / "object_ids.png"
    depth_rel = base / "metric_depth.npy"
    geometry_rel = base / "geometry.npz"
    geometry_json_rel = base / "geometry.json"
    image_path = output_root / image_rel
    _save_image(image_path, scene["image_rgb"])
    class_mask = np.zeros(scene["mask_food"].shape, dtype=np.uint8)
    if len(components) == 1:
        class_mask[scene["mask_food"]] = int(components[0]["class_id"])
    else:
        for component_index, component in enumerate(components, 1):
            class_mask[scene["comp_ids"] == component_index] = int(component["class_id"])
    _save_image(output_root / mask_rel, class_mask)
    _save_image(output_root / component_rel, scene["comp_ids"].astype(np.uint8))
    _save_image(output_root / object_rel, scene["obj_ids"].astype(np.uint8))
    depth_path = output_root / depth_rel
    depth_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(depth_path, scene["depth_m"].astype(np.float32), allow_pickle=False)

    names = [str(component["name"]) for component in scene["cfg"]["food"]["components"]]
    masses = np.asarray([scene["grams_gt"][name] for name in names], dtype=np.float32)
    volumes = np.asarray([scene["volume_ml_gt"][name] for name in names], dtype=np.float32)
    densities = np.asarray([scene["density_g_ml_by_component"][name] for name in names], dtype=np.float32)
    geometry_path = output_root / geometry_rel
    geometry_path.parent.mkdir(parents=True, exist_ok=True)
    marker_corners = (np.asarray(scene["anchor_gt"]["marker_corners_px"], dtype=np.float32)
                      if scene["anchor_gt"] else np.empty((0, 2), dtype=np.float32))
    marker_corners_world = (np.asarray(scene["anchor_gt"]["marker_corners_world_mm"], dtype=np.float32)
                            if scene["anchor_gt"] else np.empty((0, 3), dtype=np.float32))
    np.savez_compressed(
        geometry_path,
        depth_m=scene["depth_m"].astype(np.float32),
        object_ids=scene["obj_ids"].astype(np.uint8),
        component_ids=scene["comp_ids"].astype(np.uint8),
        food_class_mask=class_mask,
        surface_height_mm=scene["surface_height_mm"].astype(np.float32),
        surface_xyz_world_mm=scene["surface_xyz_world_mm"].astype(np.float32),
        camera_K=scene["camera"]["K"].astype(np.float64),
        camera_R_wc=scene["camera"]["R_wc"].astype(np.float64),
        camera_C_mm=scene["camera"]["C"].astype(np.float64),
        component_class_ids=np.asarray([int(c["class_id"]) for c in components], dtype=np.uint8),
        component_mass_g=masses,
        component_volume_ml=volumes,
        component_density_g_ml=densities,
        marker_corners_px=marker_corners,
        marker_corners_world_mm=marker_corners_world,
    )
    marker = scene["anchor_gt"]
    geometry_metadata = {
        "scene_id": scene_id,
        "generation_seed": int(seed),
        "scene_kind": scene_kind,
        "world_frame": "X right, Y away, Z up; millimetres",
        "depth_frame": "camera-Z in metres",
        "camera": {key: np.asarray(value).tolist() for key, value in scene["camera"].items()
                   if key in {"K", "R_wc", "C"}} | {"size_px": list(scene["camera"]["size"])},
        "components": [{
            "class_id": int(component["class_id"]),
            "class_name": str(component["name"]),
            "component_id": component_index,
            "mass_g": float(scene["grams_gt"][str(component["name"])]),
            "volume_ml": float(scene["volume_ml_gt"][str(component["name"])]),
            "density_g_ml": float(scene["density_g_ml_by_component"][str(component["name"])]),
            "density_provenance": density_provenance[int(component["class_id"])],
            "portion_range": portion_tags[int(component["class_id"])],
            "shape_assumption": component.get("shape_assumption", scene["cfg"].get("shape_assumption")),
            "renderer_geometry": {key: scene["cfg"]["food"]["components"][component_index - 1].get(key)
                                  for key in
                                  ("center_mm", "radius_mm", "kappa", "surface_model",
                                   "appearance_seed", "train_rgb")
                                  if key in scene["cfg"]["food"]["components"][component_index - 1]},
            "surface_recipe": scene.get("component_surface_metadata", {}).get(str(component["name"])),
            "appearance_profile_sha256": scene_profile_hashes.get(int(component["class_id"])),
        } for component_index, component in enumerate(components, 1)],
        "total_food_mass_g": float(scene["grams_gt_total"]),
        "total_food_volume_ml": float(scene["volume_ml_gt_total"]),
        "marker": ({**{key: (value.tolist() if isinstance(value, np.ndarray) else value)
                     for key, value in marker.items()},
                    "outer_sheet_mm": [105.0, 148.0],
                    "renderer_card_art": "legacy A6 synthetic fixture"}
                   if marker else None),
        "scene_parameters": scene["cfg"],
        "source": source,
        "ground_truth_mass_source": "renderer-integrated volume × explicitly recorded density; no model-inferred mass",
    }
    (output_root / geometry_json_rel).write_text(
        json.dumps(geometry_metadata, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8")
    artifacts = {}
    for name, relative in (("rgb", image_rel), ("class_mask", mask_rel),
                           ("component_ids", component_rel), ("object_ids", object_rel),
                           ("metric_depth", depth_rel), ("geometry_npz", geometry_rel),
                           ("geometry_json", geometry_json_rel)):
        artifacts[name] = {"path": relative.as_posix(), "sha256": sha256_file(output_root / relative)}
    findings = check_scene(scene)
    annotations = []
    for component_index, component in enumerate(components, 1):
        class_id, class_name = int(component["class_id"]), str(component["name"])
        annotations.append({
            "class_id": class_id,
            "class_name": class_name,
            "labels": {
                "class_mask_path": mask_rel.as_posix(),
                "component_mask_path": component_rel.as_posix(),
                "component_id": component_index,
                "object_ids_path": object_rel.as_posix(),
                "metric_depth_path": depth_rel.as_posix(),
                "geometry_path": geometry_rel.as_posix(),
                "geometry_metadata_path": geometry_json_rel.as_posix(),
                "mass_g": float(scene["grams_gt"][class_name]),
                "volume_ml": float(scene["volume_ml_gt"][class_name]),
                "density_g_ml": float(scene["density_g_ml_by_component"][class_name]),
                "portion_range": portion_tags[class_id],
            },
            "task_valid": {
                "classification": all(item.passed for item in findings),
                "segmentation": all(item.passed for item in findings),
                "depth": all(item.passed for item in findings),
                "marker": bool(all(item.passed for item in findings) and marker is not None),
                "mass": all(item.passed for item in findings),
            },
            "mass_g": float(scene["grams_gt"][class_name]),
            "mass_provenance": density_provenance[class_id],
            "inferred_mass_g": None,
        })
    return {
        "sample_id": sample_id,
        "scene_id": scene_id,
        "source": source,
        "method": "renderer",
        "method_revision": "analytic-heightfield-v2-pilot",
        "generation_seed": int(seed),
        "scene_config_sha256": hashlib.sha256(
            json.dumps(scene["cfg"], sort_keys=True, default=str).encode()).hexdigest(),
        "scene_kind": scene_kind,
        "rgb_path": image_rel.as_posix(),
        "rgb_sha256": artifacts["rgb"]["sha256"],
        "width": int(scene["image_rgb"].shape[1]),
        "height": int(scene["image_rgb"].shape[0]),
        "annotations": annotations,
        "artifact_hashes": artifacts,
        "camera": geometry_metadata["camera"],
        "marker": geometry_metadata["marker"],
        "card_present": card,
        "card_pair_id": pair_id,
        "paired_sample_id": None,
        "scene_parameters": scene["cfg"],
        "quality": {"findings": findings_to_dict(findings),
                    "automated_pass": all(item.passed for item in findings),
                    "pair_checks_pending": True,
                    "human_review": "pending"},
    }


def _class_sources(rows: list[dict[str, Any]]) -> dict[int, list[tuple[dict[str, Any], dict[str, Any]]]]:
    by_class: dict[int, dict[str, tuple[dict[str, Any], dict[str, Any]]]] = {
        class_id: {} for class_id in load_class_registry()
    }
    for row in rows:
        group = wed_group_id(row)
        for dish in row.get("dishes", []):
            class_id = int(dish.get("class_id", 0))
            if class_id in by_class and float(dish.get("weight_g", 0)) > 0:
                by_class[class_id].setdefault(group, (row, dish))
    return {class_id: sorted(items.values(), key=lambda pair: float(pair[1]["weight_g"]))
            for class_id, items in by_class.items()}


def _select_thalis(rows: list[dict[str, Any]], count: int = 3) -> list[dict[str, Any]]:
    candidates = []
    registry = load_class_registry()
    for row in rows:
        components = [dish for dish in row.get("dishes", [])
                      if int(dish.get("class_id", 0)) in registry
                      and float(dish.get("weight_g", 0)) > 0]
        if len(components) >= 3:
            candidates.append((row, components))
    candidates.sort(key=lambda pair: wed_group_id(pair[0]))
    if len(candidates) < count:
        raise ValueError(f"Pilot needs {count} eligible multi-item WED TRAIN groups; found {len(candidates)}")
    if len(candidates) == count:
        return [row for row, _ in candidates]
    indices = np.linspace(0, len(candidates) - 1, count).round().astype(int)
    return [candidates[int(index)][0] for index in indices]


def _contact_sheet(rows: list[dict[str, Any]], root: Path, path: Path) -> None:
    from PIL import ImageFont
    thumb_w, thumb_h, label_h = 190, 150, 36
    cols = 5
    font = ImageFont.load_default()
    sheet = Image.new("RGB", (cols * thumb_w, ((len(rows) + cols - 1) // cols) * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(rows):
        image = Image.open(root / row["rgb_path"]).convert("RGB")
        image.thumbnail((thumb_w, thumb_h))
        x, y = (index % cols) * thumb_w, (index // cols) * (thumb_h + label_h)
        sheet.paste(image, (x, y))
        names = ", ".join(annotation["class_name"] for annotation in row["annotations"])
        label = f"{row['scene_kind']} | {names[:30]}"
        draw.text((x + 2, y + thumb_h + 2), label, fill="black", font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)


def generate_pilot(manifest: Path, dataset_root: Path, output_root: Path,
                   seed: int = 20261103, image_size: tuple[int, int] = (640, 480),
                   thali_count: int = 3) -> dict[str, Any]:
    rows = eligible_wed_train_rows(read_wed_train_manifest(manifest))
    source_groups = {wed_group_id(row) for row in rows}
    output_root.mkdir(parents=True, exist_ok=True)
    profiles = build_train_appearance_profiles(manifest, dataset_root)
    (output_root / "appearance_profiles.json").write_text(
        json.dumps({str(key): value for key, value in profiles.items()}, indent=2,
                   sort_keys=True) + "\n", encoding="utf-8")
    sources = _class_sources(rows)
    registry = load_class_registry()
    manifest_rows: list[dict[str, Any]] = []
    class_coverage = []

    for class_id, params in registry.items():
        candidates = sources[class_id]
        if not candidates:
            raise ValueError(f"No eligible TRAIN portion for WED class {params.class_name}")
        row, dish = candidates[len(candidates) // 2]
        class_seed = int(hashlib.sha256(
            f"{seed}:{wed_group_id(row)}:{class_id}:median-pilot".encode()).hexdigest()[:8], 16)
        source = _source_record(row, dataset_root)
        grams = float(dish["weight_g"])
        low, high = min(float(item[1]["weight_g"]) for item in candidates), max(
            float(item[1]["weight_g"]) for item in candidates)
        portion_tag = "wed_observed" if low <= grams <= high else "unsupported"
        density, density_prov = _density_for(class_id, class_seed)
        components = [{"class_id": class_id, "name": params.class_name, "grams": grams}]
        scene_cfg = build_class_scene(
            class_id, params.class_name, grams, density, seed=class_seed,
            card_present=True, size=image_size, appearance_profile=profiles[class_id])
        from nutrisense_synth.scene import render_scene
        present, absent = render_card_pair(scene_cfg)
        pair_id = stable_id(source["source_group_id"], class_id, class_seed, prefix="pair-")
        pair_checks = check_card_pair(present, absent)
        pair_passed = all(item.passed for item in pair_checks)
        for pair_index, scene in enumerate((present, absent)):
            sample = _persist_scene(
                output_root, scene, scene_kind="isolated_dish", seed=class_seed,
                pair_id=pair_id, pair_index=pair_index, source=source,
                components=components, density_provenance={class_id: density_prov},
                portion_tags={class_id: portion_tag},
                scene_profile_hashes={class_id: profiles[class_id]["profile_sha256"]})
            sample["quality"].update({
                "card_pair_checks": findings_to_dict(pair_checks),
                "pair_checks_pending": False,
                "automated_pass": sample["quality"]["automated_pass"] and pair_passed,
            })
            manifest_rows.append(sample)
        manifest_rows[-2]["paired_sample_id"] = manifest_rows[-1]["sample_id"]
        manifest_rows[-1]["paired_sample_id"] = manifest_rows[-2]["sample_id"]
        class_coverage.append({"class_id": class_id, "class_name": params.class_name,
                               "eligible_source_groups": len(candidates),
                               "appearance_profile_groups": profiles[class_id]["source_group_count"],
                               "appearance_profile_sha256": profiles[class_id]["profile_sha256"],
                               "density_g_ml_sampled": density,
                               "density_assumption_range_g_ml": density_prov["sampled_from_range"],
                               "density_source": density_prov["density_source"],
                               "density_evidence": density_prov["density_evidence"],
                               "portion_g": grams, "train_observed_range_g": [low, high],
                               "source_group_id": source["source_group_id"]})

    for thali_index, row in enumerate(_select_thalis(rows, count=thali_count)):
        source = _source_record(row, dataset_root)
        dishes = [dish for dish in row.get("dishes", [])
                  if int(dish.get("class_id", 0)) in registry
                  and float(dish.get("weight_g", 0)) > 0]
        thali_seed = int(hashlib.sha256(
            f"{seed}:{source['source_group_id']}:thali:{thali_index}".encode()).hexdigest()[:8], 16)
        components, density_provenance, portion_tags, profile_hashes = [], {}, {}, {}
        for dish in dishes:
            class_id = int(dish["class_id"])
            params = registry[class_id]
            density, density_prov = _density_for(class_id, thali_seed + class_id)
            components.append({"class_id": class_id, "grams": float(dish["weight_g"]),
                               "density_g_ml": density})
            density_provenance[class_id] = density_prov
            portion_tags[class_id] = "wed_observed"
            profile_hashes[class_id] = profiles[class_id]["profile_sha256"]
        scene_cfg = build_thali_scene(
            components, seed=thali_seed, card_present=True, size=image_size,
            appearance_profiles=profiles)
        present, absent = render_card_pair(scene_cfg)
        pair_checks = check_card_pair(present, absent)
        pair_passed = all(item.passed for item in pair_checks)
        pair_id = stable_id(source["source_group_id"], "thali", thali_seed, prefix="pair-")
        components_for_labels = [dict(item, name=registry[int(item["class_id"])].class_name)
                                 for item in components]
        for pair_index, scene in enumerate((present, absent)):
            sample = _persist_scene(
                output_root, scene, scene_kind="composed_thali", seed=thali_seed,
                pair_id=pair_id, pair_index=pair_index, source=source,
                components=components_for_labels, density_provenance=density_provenance,
                portion_tags=portion_tags, scene_profile_hashes=profile_hashes)
            sample["quality"].update({
                "card_pair_checks": findings_to_dict(pair_checks),
                "pair_checks_pending": False,
                "automated_pass": sample["quality"]["automated_pass"] and pair_passed,
            })
            manifest_rows.append(sample)
        manifest_rows[-2]["paired_sample_id"] = manifest_rows[-1]["sample_id"]
        manifest_rows[-1]["paired_sample_id"] = manifest_rows[-2]["sample_id"]

    _write_manifest(output_root / "manifest.jsonl", manifest_rows)
    review_count = write_review_queue(output_root / "manifest.jsonl",
                                      output_root / "human_review.csv",
                                      per_stratum=1, seed=seed)
    card_examples = [row for row in manifest_rows if row["card_present"]]
    _contact_sheet(card_examples, output_root, output_root / "contact_sheet.png")
    summary = {
        "pilot_version": 1,
        "seed": seed,
        "renderer_revision": "analytic-heightfield-v2-pilot",
        "split_used": "eligible WED TRAIN only; seed-42 DEV groups removed",
        "eligible_wed_train_groups": len(source_groups),
        "eligible_wed_train_group_ids": sorted(source_groups),
        "class_count": len(registry),
        "class_coverage": class_coverage,
        "isolated_class_scenes": 41,
        "composed_thali_scenes": thali_count,
        "scene_pairs": len(manifest_rows) // 2,
        "rendered_images": len(manifest_rows),
        "card_present_images": sum(bool(row["card_present"]) for row in manifest_rows),
        "card_absent_images": sum(not row["card_present"] for row in manifest_rows),
        "automated_pass_count": sum(bool(row["quality"]["automated_pass"]) for row in manifest_rows),
        "automated_failures": [{"sample_id": row["sample_id"], "findings": row["quality"]}
                               for row in manifest_rows if not row["quality"]["automated_pass"]],
        "human_review_rows": review_count,
        "human_review_status": "pending; pilot is not approved for training or scale-up",
        "promotion_status": "blocked_pending_human_review",
        "outputs": ["manifest.jsonl", "appearance_profiles.json", "human_review.csv",
                    "contact_sheet.png", "pilot_validation.json"],
        "appearance_profiles_sha256": sha256_file(output_root / "appearance_profiles.json"),
        "locked_accessed": False,
        "aruco_evaluation_accessed": False,
        "wed_test_accessed": False,
        "wed_dev_images_used": False,
        "production_models_trained": False,
        "gan_or_diffusion_used": False,
    }
    (output_root / "pilot_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def validate_pilot(output_root: Path, source_manifest: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    manifest_path = output_root / "manifest.jsonl"
    rows = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    errors: list[str] = []
    by_id = {str(row.get("sample_id")): row for row in rows}
    if len(by_id) != len(rows):
        errors.append("sample ids are not unique")
    registry = load_class_registry()
    source_rows = eligible_wed_train_rows(read_wed_train_manifest(source_manifest))
    eligible_groups = {wed_group_id(row) for row in source_rows}
    if any(row.get("source", {}).get("source_group_id") not in eligible_groups for row in rows):
        errors.append("a generated scene source group is outside eligible WED TRAIN")
    profile_rows = json.loads((output_root / "appearance_profiles.json").read_text(encoding="utf-8"))
    for class_id, profile in profile_rows.items():
        groups = {str(item.get("group_id")) for item in profile.get("statistics", [])}
        if not groups or not groups.issubset(eligible_groups):
            errors.append(f"appearance profile {class_id} has no eligible TRAIN-only group lineage")
    classes = {int(annotation["class_id"]) for row in rows if row["scene_kind"] == "isolated_dish"
               for annotation in row["annotations"]}
    if classes != set(registry):
        errors.append(f"pilot class coverage is incomplete: {sorted(classes)}")
    pairs: dict[str, list[dict[str, Any]]] = {}
    artifact_count = 0
    for row in rows:
        sid = row["sample_id"]
        if row.get("source", {}).get("source_split") != "train":
            errors.append(f"{sid}: source split is not train")
        if row.get("quality", {}).get("human_review") != "pending":
            errors.append(f"{sid}: unexpected human-review state")
        for kind, artifact in row.get("artifact_hashes", {}).items():
            path = output_root / artifact["path"]
            artifact_count += 1
            if not path.is_file() or sha256_file(path) != artifact.get("sha256"):
                errors.append(f"{sid}: {kind} artifact missing or hash mismatch")
        try:
            with np.load(output_root / row["artifact_hashes"]["geometry_npz"]["path"],
                         allow_pickle=False) as geometry:
                food = geometry["food_class_mask"] > 0
                comp = geometry["component_ids"]
                obj = geometry["object_ids"]
                if not np.array_equal(food, comp > 0) or not np.array_equal(food, obj == 3):
                    errors.append(f"{sid}: food/class/component/object masks disagree")
                depth = geometry["depth_m"]
                if not np.isfinite(depth).all() or np.any(depth <= 0):
                    errors.append(f"{sid}: camera-Z depth is nonfinite or nonpositive")
                xyz = geometry["surface_xyz_world_mm"]
                if xyz.shape != (*depth.shape, 3) or not np.isfinite(xyz).all():
                    errors.append(f"{sid}: 3D geometry dimensions/values are invalid")
                mass = geometry["component_mass_g"].astype(float)
                volume = geometry["component_volume_ml"].astype(float)
                density = geometry["component_density_g_ml"].astype(float)
                if (not np.isfinite(mass).all() or not np.isfinite(volume).all()
                        or not np.isfinite(density).all() or np.any(mass <= 0)
                        or np.any(volume <= 0) or np.any(density <= 0)
                        or not np.allclose(mass, volume * density, rtol=1e-6, atol=1e-3)):
                    errors.append(f"{sid}: mass/volume/density labels are inconsistent")
                if bool(row["card_present"]) != bool(np.any(obj == 2)):
                    errors.append(f"{sid}: card presence disagrees with object map")
                if row["card_present"]:
                    marker = row.get("marker") or {}
                    corners = np.asarray(marker.get("marker_corners_px", []), dtype=float)
                    if (marker.get("marker_id") != 7 or marker.get("dictionary") != "DICT_4X4_50"
                            or marker.get("marker_side_mm") != 60.0 or corners.shape != (4, 2)
                            or not np.isfinite(corners).all()):
                        errors.append(f"{sid}: ID7/60mm marker label is invalid")
        except (OSError, ValueError, KeyError) as exc:
            errors.append(f"{sid}: geometry bundle could not be verified ({exc})")
        if row.get("card_pair_id"):
            pairs.setdefault(str(row["card_pair_id"]), []).append(row)

    pair_passed = 0
    pair_checks = []
    for pair_id, members in sorted(pairs.items()):
        if len(members) != 2 or {bool(member.get("card_present")) for member in members} != {True, False}:
            errors.append(f"{pair_id}: must have exactly one present and one absent card sample")
            continue
        present = next(member for member in members if member["card_present"])
        absent = next(member for member in members if not member["card_present"])
        if present.get("paired_sample_id") != absent["sample_id"] or absent.get("paired_sample_id") != present["sample_id"]:
            errors.append(f"{pair_id}: paired sample pointers disagree")
        p_cfg, a_cfg = dict(present["scene_parameters"]), dict(absent["scene_parameters"])
        p_anchor, a_anchor = dict(p_cfg.pop("anchor", {})), dict(a_cfg.pop("anchor", {}))
        p_flag, a_flag = p_anchor.pop("card", None), a_anchor.pop("card", None)
        if p_cfg != a_cfg or p_anchor != a_anchor or (p_flag, a_flag) != (True, False):
            errors.append(f"{pair_id}: config differs beyond card presence")
        try:
            with np.load(output_root / present["artifact_hashes"]["geometry_npz"]["path"],
                         allow_pickle=False) as p, np.load(
                             output_root / absent["artifact_hashes"]["geometry_npz"]["path"],
                             allow_pickle=False) as a:
                p_card, a_card = (p["object_ids"] == 2), (a["object_ids"] == 2)
                card_region = p_card | a_card
                exact_keys = ("food_class_mask", "component_ids", "component_mass_g",
                              "component_volume_ml", "component_density_g_ml", "camera_K",
                              "camera_R_wc", "camera_C_mm")
                exact = all(np.array_equal(p[key], a[key]) for key in exact_keys)
                depth_same = np.array_equal(p["depth_m"][~card_region], a["depth_m"][~card_region])
                xyz_same = np.array_equal(p["surface_xyz_world_mm"][~card_region],
                                          a["surface_xyz_world_mm"][~card_region])
                image_p = np.asarray(Image.open(output_root / present["rgb_path"]).convert("RGB"))
                image_a = np.asarray(Image.open(output_root / absent["rgb_path"]).convert("RGB"))
                changed = np.any(image_p != image_a, axis=2)
                allowed = cv2.dilate(card_region.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
                rgb_local = not np.any(changed & ~allowed)
                ok = exact and depth_same and xyz_same and rgb_local
                if not ok:
                    errors.append(f"{pair_id}: paired scenes differ outside marker/card region or labels")
                else:
                    pair_passed += 1
                pair_checks.append({"pair_id": pair_id, "passed": bool(ok),
                                    "scene_labels_exact": bool(exact),
                                    "depth_equal_outside_card": bool(depth_same),
                                    "geometry_equal_outside_card": bool(xyz_same),
                                    "rgb_changed_only_at_card": bool(rgb_local)})
        except (OSError, ValueError, KeyError) as exc:
            errors.append(f"{pair_id}: pair artifacts could not be verified ({exc})")

    result = {
        "sample_count": len(rows),
        "artifact_count": artifact_count,
        "unique_class_count": len(classes),
        "appearance_profile_class_count": len(profile_rows),
        "pair_count": len(pairs),
        "passed_pair_count": pair_passed,
        "all_automated_checks_passed": not errors,
        "errors": errors,
        "pair_checks": pair_checks,
        "human_review_status": "pending",
        "promotion_status": "blocked_pending_human_review" if not errors else "blocked_automated_failures",
        "locked_accessed": False,
        "aruco_evaluation_accessed": False,
        "wed_test_accessed": False,
        "wed_dev_images_used": False,
    }
    (output_root / "pilot_validation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result
