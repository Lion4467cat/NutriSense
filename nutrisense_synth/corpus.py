"""TRAIN-only generation, on-disk artifacts, and strict corpus auditing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

import cv2
import numpy as np
from PIL import Image

from nutrisense_synth.manifest import (
    AnnotationBundle,
    Method,
    SourceGroup,
    SyntheticSample,
    sha256_file,
    stable_id,
    write_jsonl,
)
from nutrisense_synth.measured import MeasuredExample
from nutrisense_synth.methods.base import AppearanceMethod, GenerationContext
from nutrisense_synth.parameters import (eligible_wed_train_rows, load_class_registry,
                                         observed_portion_ranges, read_wed_train_manifest,
                                         wed_group_id)
from nutrisense_synth.quality import check_scene, findings_to_dict
from nutrisense_synth.scene import (build_class_scene, build_thali_scene,
                                    render_card_pair, render_scene)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = ROOT / "datasets" / "processed" / "synthetic_food_v1"


def _source_group(row: dict[str, Any], image_path: Path, mask_path: Path | None) -> SourceGroup:
    if row.get("split") != "train":
        raise ValueError("Synthetic corpus generation accepts WED TRAIN rows only")
    group = wed_group_id(row)
    return SourceGroup(
        source="wed", source_group_id=group,
        source_record_id=str(row["image"]), source_split="train",
        source_image_sha256=sha256_file(image_path),
        source_label_sha256=sha256_file(mask_path) if mask_path and mask_path.is_file() else None,
    )


def _save_array_png(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if array.dtype == bool:
        array = array.astype(np.uint8) * 255
    Image.fromarray(array).save(path)


def _write_coverage_summary(output_root: Path, samples: list[SyntheticSample],
                            requested_per_class: int, scene_kind: str) -> None:
    registry = load_class_registry()
    counts = {class_id: 0 for class_id in registry}
    groups: dict[int, set[str]] = {class_id: set() for class_id in registry}
    for sample in samples:
        for annotation in sample.annotations:
            counts[annotation.class_id] = counts.get(annotation.class_id, 0) + 1
            groups.setdefault(annotation.class_id, set()).add(sample.source.source_group_id)
    summary = {
        "scene_kind": scene_kind,
        "requested_per_class": requested_per_class,
        "classes": [{"class_id": class_id, "class_name": params.class_name,
                     "sample_count": counts[class_id],
                     "distinct_source_groups": len(groups[class_id]),
                     "coverage_gap": counts[class_id] < requested_per_class}
                    for class_id, params in registry.items()],
        "unsupported_or_undercovered_classes": [
            params.class_name for class_id, params in registry.items()
            if counts[class_id] < requested_per_class
        ],
    }
    (output_root / "coverage.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _appearance_pair(scenes: tuple[dict[str, Any], ...], method: AppearanceMethod | None,
                     components: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    if method is None:
        return scenes
    from nutrisense_synth.parameters import load_class_registry
    registry = load_class_registry()
    id_by_name = {item.class_name: class_id for class_id, item in registry.items()}
    no_card = next((scene for scene in scenes if scene["anchor_gt"] is None), scenes[0])
    semantic = np.zeros(no_card["mask_food"].shape, dtype=np.uint8)
    if len(components) == 1:
        semantic[no_card["mask_food"]] = int(components[0]["class_id"])
    else:
        for component_id, component in enumerate(components, 1):
            semantic[no_card["comp_ids"] == component_id] = int(component["class_id"])
    context = GenerationContext(
        scene_id=str(no_card["cfg"].get("seed")), seed=int(no_card["cfg"].get("seed", 0)),
        condition_rgb=no_card["image_rgb"], semantic_mask=semantic,
        depth_m=no_card["depth_m"], marker_mask=(no_card["obj_ids"] == 2),
        food_mask=no_card["mask_food"],
        metadata={"class_name": ", ".join(str(id_by_name.get(c.get("name", ""), "food"))
                                           for c in no_card["cfg"]["food"]["components"]),
                  "scene_config": no_card["cfg"],
                  "mass_by_class_g": {
                      int(component["class_id"]): float(component["share_g"])
                      for component in components
                  }},
    )
    generated = method.generate(context)
    outputs = []
    for scene in scenes:
        updated = dict(scene)
        image = scene["image_rgb"].copy()
        image[scene["mask_food"]] = generated[scene["mask_food"]]
        updated["image_rgb"] = image
        updated["image_bgr"] = image[:, :, ::-1].copy()
        outputs.append(updated)
    return tuple(outputs)


def generate_renderer_corpus(rows: list[dict[str, Any]], dataset_root: Path,
                             output_root: Path = DEFAULT_DATA_ROOT,
                             samples_per_class: int = 1, seed: int = 20261102,
                             include_card_pairs: bool = True,
                             scene_kind: str = "isolated_dish",
                             appearance_method: AppearanceMethod | None = None) -> list[SyntheticSample]:
    """Generate a balanced capped TRAIN-derived renderer corpus."""
    if samples_per_class < 1:
        raise ValueError("samples_per_class must be positive")
    # Validate the measured image/mass contract before sampling any class. The
    # generation code below still uses row dictionaries for compatibility, but
    # every source row must first pass the canonical measured-data adapter.
    for row in rows:
        if row.get("split") == "train":
            MeasuredExample.from_row(row, dataset_root=dataset_root,
                                     require_files=True)
    if scene_kind == "composed_thali":
        return _generate_thali_corpus(rows, dataset_root, output_root,
                                      samples_per_class, seed, include_card_pairs,
                                      appearance_method)
    if scene_kind != "isolated_dish":
        raise ValueError(f"Unknown scene_kind: {scene_kind}")
    registry = load_class_registry()
    portions = observed_portion_ranges()
    rows_by_class: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for row in eligible_wed_train_rows(rows):
        for dish in row.get("dishes", []):
            if dish["name"] in portions:
                rows_by_class.setdefault(str(dish["name"]), []).append((row, dish))

    output_root.mkdir(parents=True, exist_ok=True)
    samples: list[SyntheticSample] = []
    for class_id, params in registry.items():
        candidates = rows_by_class.get(params.class_name, [])
        if not candidates:
            continue
        # Stable coverage sampling: distinct physical groups first, never
        # inflate a class with repeated views of the same plate.
        distinct: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
        for row, dish in candidates:
            group = wed_group_id(row)
            distinct.setdefault(group, (row, dish))
        ordered = sorted(distinct.values(), key=lambda item: float(item[1]["weight_g"]))
        if len(ordered) <= samples_per_class:
            chosen = ordered
        else:
            indexes = np.linspace(0, len(ordered) - 1, samples_per_class).round().astype(int)
            chosen = [ordered[int(index)] for index in indexes]
        for offset, (row, dish) in enumerate(chosen):
            image_path = dataset_root / row["image"]
            mask_path = dataset_root / row["mask"] if row.get("mask") else None
            source = _source_group(row, image_path, mask_path)
            grams = float(dish["weight_g"])
            low, high = portions[params.class_name]
            portion_tag = "wed_observed" if low <= grams <= high else "broader_exploratory"
            scene_seed = int(hashlib.sha256(
                f"{seed}:{source.source_group_id}:{class_id}:{offset}".encode()).hexdigest()[:8], 16)
            base_cfg = build_class_scene(class_id, params.class_name, grams,
                                         params.density_g_ml, scene_seed)
            if include_card_pairs:
                scenes = render_card_pair(base_cfg)
            else:
                base_cfg["anchor"]["card"] = False
                scenes = (render_scene(base_cfg),)
            scenes = _appearance_pair(scenes, appearance_method,
                                      [{"class_id": class_id, "name": params.class_name}])
            pair_id = stable_id(source.source_group_id, class_id, scene_seed, prefix="pair-") if include_card_pairs else None
            pending: list[dict[str, Any]] = []
            for scene in scenes:
                findings = check_scene(scene)
                valid = all(item.passed for item in findings)
                scene_id = stable_id(source.source_group_id, class_id, scene_seed,
                                     scene["cfg"]["anchor"]["card"], prefix="scene-")
                card_flag = bool(scene["cfg"]["anchor"]["card"])
                stem = stable_id(scene_id, prefix="sample-")
                image_out = output_root / "images" / f"{stem}.png"
                _save_array_png(image_out, scene["image_rgb"])
                mask_out = output_root / "labels" / f"{stem}.mask.png"
                depth_out = output_root / "labels" / f"{stem}.depth.npy"
                _save_array_png(mask_out, scene["mask_food"])
                depth_out.parent.mkdir(parents=True, exist_ok=True)
                np.save(depth_out, scene["depth_m"].astype(np.float32))
                physical_mass = float(scene["grams_gt_total"])
                marker_label = scene["anchor_gt"]
                if marker_label is not None:
                    marker_label = {key: (value.tolist() if isinstance(value, np.ndarray) else value)
                                    for key, value in marker_label.items()}
                annotation = AnnotationBundle(
                    class_id=class_id, class_name=params.class_name,
                    labels={"mask_path": str(mask_out.relative_to(output_root)),
                            "depth_path": str(depth_out.relative_to(output_root)),
                            "component_grams": scene["grams_gt"],
                            "marker": marker_label,
                            "portion_range": portion_tag},
                    task_valid={"classification": valid, "segmentation": valid,
                                "depth": valid, "marker": valid and scene["anchor_gt"] is not None,
                                "mass": valid},
                    mass_g=physical_mass,
                    mass_provenance={**params.mass_provenance(), "portion_range": portion_tag},
                )
                pending.append({"sample_id": stem, "scene_id": scene_id,
                                "scene": scene, "image_out": image_out,
                                "annotation": annotation, "card": card_flag})
            for item in pending:
                scene = item["scene"]
                paired = next((other for other in pending if other["card"] != item["card"]), None)
                samples.append(SyntheticSample(
                    sample_id=item["sample_id"], scene_id=item["scene_id"],
                    source=source,
                    method=cast(Method, "renderer" if appearance_method is None else appearance_method.name),
                    method_revision="analytic-heightfield-v1" if appearance_method is None else appearance_method.revision,
                    seed=scene_seed, config_sha256=hashlib.sha256(
                        json.dumps(scene["cfg"], sort_keys=True, default=str).encode()).hexdigest(),
                    output_path=str(item["image_out"].relative_to(output_root)),
                    output_sha256=sha256_file(item["image_out"]),
                    width=int(scene["image_rgb"].shape[1]), height=int(scene["image_rgb"].shape[0]),
                    annotations=(item["annotation"],), scene_kind="isolated_dish",
                    scene_parameters=scene["cfg"],
                    card_present=item["card"], card_pair_id=pair_id,
                    paired_sample_id=paired["sample_id"] if paired else None,
                    method_checkpoint_sha256=getattr(appearance_method, "checkpoint_sha256", None),
                    method_provenance=getattr(appearance_method, "provenance", {
                        "generator": "project analytic renderer", "external_pretrained_weights": False}),
                    quality={"findings": findings_to_dict(check_scene(scene)),
                             "automated_pass": all(f.passed for f in check_scene(scene)),
                             "human_review": "pending"},
                ))
    write_jsonl(output_root / "manifest.jsonl", samples)
    _write_coverage_summary(output_root, samples, samples_per_class, scene_kind)
    return samples


def _generate_thali_corpus(rows: list[dict[str, Any]], dataset_root: Path,
                           output_root: Path, samples_per_class: int, seed: int,
                           include_card_pairs: bool,
                           appearance_method: AppearanceMethod | None = None) -> list[SyntheticSample]:
    registry = load_class_registry()
    portions = observed_portion_ranges()
    eligible = []
    class_coverage = {class_id: 0 for class_id in registry}
    for row in eligible_wed_train_rows(rows):
        components = [dish for dish in row.get("dishes", [])
                      if dish.get("name") in portions and float(dish.get("weight_g", 0)) > 0]
        if len(components) >= 2:
            eligible.append((row, components))
    eligible.sort(key=lambda item: (str(item[0].get("date_key")), str(item[0].get("set"))))
    selected = []
    for row, components in eligible:
        ids = {int(dish["class_id"]) for dish in components if int(dish["class_id"]) in registry}
        if ids and all(class_coverage[class_id] < samples_per_class for class_id in ids):
            selected.append((row, components))
            for class_id in ids:
                class_coverage[class_id] += 1
        if all(count >= samples_per_class for count in class_coverage.values()):
            break
    output_root.mkdir(parents=True, exist_ok=True)
    samples: list[SyntheticSample] = []
    for index, (row, dishes) in enumerate(selected):
        image_path = dataset_root / row["image"]
        mask_path = dataset_root / row["mask"] if row.get("mask") else None
        source = _source_group(row, image_path, mask_path)
        scene_seed = int(hashlib.sha256(
            f"{seed}:{source.source_group_id}:thali:{index}".encode()).hexdigest()[:8], 16)
        components = [{"class_id": int(dish["class_id"]), "grams": float(dish["weight_g"])}
                      for dish in dishes if int(dish["class_id"]) in registry]
        cfg = build_thali_scene(components, seed=scene_seed)
        scenes = render_card_pair(cfg) if include_card_pairs else (render_scene(cfg),)
        scenes = _appearance_pair(scenes, appearance_method, components)
        pair_id = stable_id(source.source_group_id, "thali", scene_seed, prefix="pair-") if include_card_pairs else None
        pending = []
        for scene in scenes:
            findings = check_scene(scene)
            valid = all(item.passed for item in findings)
            is_card = bool(scene["cfg"]["anchor"]["card"])
            scene_id = stable_id(source.source_group_id, "thali", scene_seed, is_card, prefix="scene-")
            sample_id = stable_id(scene_id, prefix="sample-")
            image_out = output_root / "images" / f"{sample_id}.png"
            _save_array_png(image_out, scene["image_rgb"])
            mask_out = output_root / "labels" / f"{sample_id}.components.png"
            depth_out = output_root / "labels" / f"{sample_id}.depth.npy"
            _save_array_png(mask_out, scene["comp_ids"])
            depth_out.parent.mkdir(parents=True, exist_ok=True)
            np.save(depth_out, scene["depth_m"].astype(np.float32))
            annotations = []
            for component_index, dish in enumerate(components, 1):
                class_id = int(dish["class_id"])
                params = registry[class_id]
                grams = float(scene["grams_gt"][params.class_name])
                low, high = portions[params.class_name]
                source_grams = float(dish["grams"])
                portion_tag = "wed_observed" if low <= source_grams <= high else "broader_exploratory"
                annotations.append(AnnotationBundle(
                    class_id=class_id, class_name=params.class_name,
                    labels={"instance_mask_path": str(mask_out.relative_to(output_root)),
                            "instance_mask_id": component_index,
                            "depth_path": str(depth_out.relative_to(output_root)),
                            "component_grams": {params.class_name: grams},
                            "portion_range": portion_tag,
                            "marker": ({key: (value.tolist() if isinstance(value, np.ndarray) else value)
                                        for key, value in scene["anchor_gt"].items()}
                                       if scene["anchor_gt"] is not None else None)},
                    task_valid={"classification": valid, "segmentation": valid,
                                "depth": valid, "marker": valid and scene["anchor_gt"] is not None,
                                "mass": valid},
                    mass_g=grams, mass_provenance={**params.mass_provenance(),
                                                   "portion_range": portion_tag},
                ))
            pending.append({"sample_id": sample_id, "scene_id": scene_id,
                            "image_out": image_out, "scene": scene, "annotations": tuple(annotations),
                            "card": is_card})
        for item in pending:
            paired = next((other for other in pending if other["card"] != item["card"]), None)
            scene = item["scene"]
            samples.append(SyntheticSample(
                sample_id=item["sample_id"], scene_id=item["scene_id"], source=source,
                method=cast(Method, "renderer" if appearance_method is None else appearance_method.name),
                method_revision="analytic-heightfield-v1" if appearance_method is None else appearance_method.revision,
                seed=scene_seed,
                config_sha256=hashlib.sha256(json.dumps(scene["cfg"], sort_keys=True,
                                                        default=str).encode()).hexdigest(),
                output_path=str(item["image_out"].relative_to(output_root)),
                output_sha256=sha256_file(item["image_out"]),
                width=int(scene["image_rgb"].shape[1]), height=int(scene["image_rgb"].shape[0]),
                annotations=item["annotations"], scene_kind="composed_thali",
                scene_parameters=scene["cfg"], card_present=item["card"],
                card_pair_id=pair_id, paired_sample_id=paired["sample_id"] if paired else None,
                method_checkpoint_sha256=getattr(appearance_method, "checkpoint_sha256", None),
                method_provenance=getattr(appearance_method, "provenance", {
                    "generator": "project analytic renderer", "external_pretrained_weights": False}),
                quality={"findings": findings_to_dict(check_scene(scene)),
                         "automated_pass": all(f.passed for f in check_scene(scene)),
                         "human_review": "pending"},
            ))
    write_jsonl(output_root / "manifest.jsonl", samples)
    _write_coverage_summary(output_root, samples, samples_per_class, "composed_thali")
    return samples


def audit_manifest(manifest_path: Path, data_root: Path,
                   review_summary: Path | None = None) -> list[str]:
    from nutrisense_synth.manifest import read_jsonl
    errors: list[str] = []
    rows = read_jsonl(manifest_path)
    registry = load_class_registry()
    review_summary = review_summary or manifest_path.with_name("review_summary.json")
    if not review_summary.is_file():
        errors.append("stratified human-review summary is missing")
    else:
        summary = json.loads(review_summary.read_text(encoding="utf-8"))
        if not summary.get("passed"):
            errors.append("stratified human-review acceptance gate failed")
    by_id = {row.get("sample_id"): row for row in rows}
    if len(by_id) != len(rows):
        errors.append("sample_id values are not unique")
    pairs: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        sid = row.get("sample_id", "<missing>")
        source = row.get("source", {})
        if source.get("source") != "wed" or source.get("source_split") != "train":
            errors.append(f"{sid}: source must be WED TRAIN")
        path = data_root / row.get("output_path", "")
        if not path.is_file():
            errors.append(f"{sid}: output file missing")
        elif sha256_file(path) != row.get("output_sha256"):
            errors.append(f"{sid}: output hash mismatch")
        elif path.is_file():
            try:
                with Image.open(path) as image:
                    if image.size != (int(row.get("width", 0)), int(row.get("height", 0))):
                        errors.append(f"{sid}: output dimensions differ from manifest")
            except OSError:
                errors.append(f"{sid}: output image cannot be decoded")
        if not row.get("quality", {}).get("automated_pass", False):
            errors.append(f"{sid}: automated quality gate failed")
        findings = row.get("quality", {}).get("findings", [])
        if not findings or any(not item.get("passed", False) for item in findings):
            errors.append(f"{sid}: quality findings are missing or include failures")
        human = row.get("quality", {}).get("human_review", {})
        if isinstance(human, dict) and human:
            for annotation in row.get("annotations", []):
                validity = annotation.get("task_valid", {})
                if not human.get("identity_correct", True) and validity.get("classification"):
                    errors.append(f"{sid}: human-rejected identity remains valid for classification")
                if not human.get("geometry_valid", True) and any(
                        validity.get(task) for task in ("segmentation", "depth", "mass")):
                    errors.append(f"{sid}: human-rejected geometry remains valid for geometry tasks")
                if human.get("marker_valid") is False and validity.get("marker"):
                    errors.append(f"{sid}: human-rejected marker remains valid")
        scene = row.get("scene_parameters", {})
        if scene.get("anchor", {}).get("card") is not row.get("card_present"):
            errors.append(f"{sid}: card flag differs from scene configuration")
        for annotation in row.get("annotations", []):
            class_id = int(annotation.get("class_id", -1))
            params = registry.get(class_id)
            if params is None or params.class_name != annotation.get("class_name"):
                errors.append(f"{sid}: class id/name is outside the WED 41 taxonomy")
            validity = annotation.get("task_valid", {})
            if any(not isinstance(value, bool) for value in validity.values()):
                errors.append(f"{sid}: task validity flags must be booleans")
            grams = annotation.get("mass_g")
            provenance = annotation.get("mass_provenance", {})
            if grams is not None and (not np.isfinite(float(grams)) or float(grams) < 0
                                      or provenance.get("measurement_kind") != "synthetic_physical"):
                errors.append(f"{sid}: physical mass label/provenance is invalid")
            labels = annotation.get("labels", {})
            if validity.get("segmentation") and not (labels.get("mask_path") or labels.get("instance_mask_path")):
                errors.append(f"{sid}: valid segmentation label has no mask artifact")
            if validity.get("depth") and not labels.get("depth_path"):
                errors.append(f"{sid}: valid depth label has no depth artifact")
            if validity.get("mass") and grams is None:
                errors.append(f"{sid}: valid mass task has no physical mass label")
            marker = labels.get("marker")
            if row.get("card_present") and validity.get("marker"):
                corners = np.asarray((marker or {}).get("marker_corners_px", []))
                if corners.shape != (4, 2) or not np.isfinite(corners).all():
                    errors.append(f"{sid}: valid marker task has no four finite corners")
            if not row.get("card_present") and validity.get("marker"):
                errors.append(f"{sid}: no-card sample cannot have marker-derived labels")
            for field in ("mask_path", "instance_mask_path", "depth_path"):
                rel = labels.get(field)
                if rel is not None and not (data_root / rel).is_file():
                    errors.append(f"{sid}: annotation artifact missing: {rel}")
            mask_rel = labels.get("mask_path") or labels.get("instance_mask_path")
            if mask_rel and (data_root / mask_rel).is_file():
                try:
                    with Image.open(data_root / mask_rel) as mask_image:
                        if mask_image.size != (int(row.get("width", 0)), int(row.get("height", 0))):
                            errors.append(f"{sid}: annotation mask dimensions differ from image")
                except OSError:
                    errors.append(f"{sid}: annotation mask cannot be decoded")
            depth_rel = labels.get("depth_path")
            if depth_rel and (data_root / depth_rel).is_file():
                try:
                    depth = np.load(data_root / depth_rel, allow_pickle=False)
                    if depth.shape != (int(row.get("height", 0)), int(row.get("width", 0))) or not np.isfinite(depth).all() or np.any(depth < 0):
                        errors.append(f"{sid}: metric-depth artifact is invalid")
                except (OSError, ValueError):
                    errors.append(f"{sid}: metric-depth artifact cannot be loaded")
            class_name = annotation.get("class_name")
            if (grams is not None
                    and labels.get("component_grams", {}).get(class_name) is not None
                    and abs(float(grams) - float(labels["component_grams"][class_name])) > 1e-3):
                errors.append(f"{sid}: mass label differs from component ground truth")
        pair_id = row.get("card_pair_id")
        if pair_id:
            pairs.setdefault(pair_id, []).append(row)
    for pair_id, members in pairs.items():
        if len(members) != 2 or {m.get("card_present") for m in members} != {True, False}:
            errors.append(f"{pair_id}: pair must contain one card and one no-card sample")
        if len(members) == 2:
            for member in members:
                other = by_id.get(member.get("paired_sample_id"))
                if other is None or other.get("card_pair_id") != pair_id:
                    errors.append(f"{member.get('sample_id')}: invalid paired_sample_id")
            first, second = members
            first_cfg, second_cfg = dict(first.get("scene_parameters", {})), dict(second.get("scene_parameters", {}))
            first_anchor = dict(first_cfg.pop("anchor", {}))
            second_anchor = dict(second_cfg.pop("anchor", {}))
            first_card, second_card = first_anchor.pop("card", None), second_anchor.pop("card", None)
            if (first_cfg != second_cfg or first_anchor != second_anchor
                    or {first_card, second_card} != {True, False}):
                errors.append(f"{pair_id}: pair scene conditions differ beyond card presence")
            if first.get("source", {}).get("source_group_id") != second.get("source", {}).get("source_group_id"):
                errors.append(f"{pair_id}: pair source groups differ")
    return errors


def auditable_cutmix(
    row_a: dict[str, Any],
    row_b: dict[str, Any],
    dataset_root: Path,
    output_dir: Path | None = None,
    *,
    all_train_rows: list[dict[str, Any]] | None = None,
    seed: int = 42,
    blend_boundary: bool = True,
) -> dict[str, Any]:
    """Paste food patch from row_b into row_a with strict WED TRAIN audit and exact provenance."""
    if row_a.get("split") != "train" or row_b.get("split") != "train":
        raise ValueError("auditable_cutmix accepts WED TRAIN rows only; non-train rows are strictly forbidden")

    if all_train_rows is not None:
        eligible = eligible_wed_train_rows(all_train_rows)
        eligible_groups = {wed_group_id(r) for r in eligible}
        if wed_group_id(row_a) not in eligible_groups or wed_group_id(row_b) not in eligible_groups:
            raise ValueError("auditable_cutmix rows must belong to eligible WED TRAIN groups (excluding DEV carve)")

    img_path_a = dataset_root / row_a["image"]
    mask_path_a = dataset_root / row_a["mask"] if row_a.get("mask") else None
    img_path_b = dataset_root / row_b["image"]
    mask_path_b = dataset_root / row_b["mask"] if row_b.get("mask") else None

    if not img_path_a.is_file() or not img_path_b.is_file():
        raise FileNotFoundError(f"Source image missing: {img_path_a} or {img_path_b}")

    img_a = cv2.imread(str(img_path_a), cv2.IMREAD_COLOR)
    img_b = cv2.imread(str(img_path_b), cv2.IMREAD_COLOR)
    if img_a is None or img_b is None:
        raise ValueError("Failed to load source image(s)")

    h_a, w_a = img_a.shape[:2]
    mask_a = cv2.imread(str(mask_path_a), cv2.IMREAD_UNCHANGED) if mask_path_a and mask_path_a.is_file() else None
    if mask_a is None:
        mask_a = np.zeros((h_a, w_a), dtype=np.uint8)
    elif mask_a.ndim == 3:
        mask_a = mask_a[:, :, 0]
    if mask_a.shape[:2] != (h_a, w_a):
        mask_a = cv2.resize(mask_a, (w_a, h_a), interpolation=cv2.INTER_NEAREST)

    h_b, w_b = img_b.shape[:2]
    mask_b = cv2.imread(str(mask_path_b), cv2.IMREAD_UNCHANGED) if mask_path_b and mask_path_b.is_file() else None
    if mask_b is None:
        mask_b = np.zeros((h_b, w_b), dtype=np.uint8)
    elif mask_b.ndim == 3:
        mask_b = mask_b[:, :, 0]
    if mask_b.shape[:2] != (h_b, w_b):
        mask_b = cv2.resize(mask_b, (w_b, h_b), interpolation=cv2.INTER_NEAREST)

    dishes_b = row_b.get("dishes", [])
    classes_b = [int(d["class_id"]) for d in dishes_b if int(d.get("class_id", 0)) > 0]
    unique_b = [int(cid) for cid in np.unique(mask_b) if cid > 0]
    cand_classes = [cid for cid in classes_b if cid in unique_b] or unique_b

    rng = np.random.RandomState(seed)
    if cand_classes:
        paste_class = cand_classes[int(rng.randint(0, len(cand_classes)))]
        src_patch_mask = (mask_b == paste_class)
    else:
        paste_class = 1
        src_patch_mask = np.zeros((h_b, w_b), dtype=bool)
        src_patch_mask[h_b // 4 : 3 * h_b // 4, w_b // 4 : 3 * w_b // 4] = True

    y_idx, x_idx = np.where(src_patch_mask)
    if len(y_idx) == 0:
        y1, y2, x1, x2 = h_b // 4, 3 * h_b // 4, w_b // 4, 3 * w_b // 4
    else:
        y1, y2 = int(y_idx.min()), int(y_idx.max()) + 1
        x1, x2 = int(x_idx.min()), int(x_idx.max()) + 1

    patch_rgb = img_b[y1:y2, x1:x2]
    patch_mask = src_patch_mask[y1:y2, x1:x2]

    target_scale = float(rng.uniform(0.6, 1.1))
    th = max(4, int(round((y2 - y1) * target_scale * (h_a / max(1, h_b)))))
    tw = max(4, int(round((x2 - x1) * target_scale * (w_a / max(1, w_b)))))
    th = min(th, h_a - 2)
    tw = min(tw, w_a - 2)

    patch_rgb_resized = cv2.resize(patch_rgb, (tw, th), interpolation=cv2.INTER_LINEAR)
    patch_mask_resized = cv2.resize(patch_mask.astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST) > 0

    max_ty = max(0, h_a - th)
    max_tx = max(0, w_a - tw)
    pos_y = int(rng.randint(0, max_ty + 1)) if max_ty > 0 else 0
    pos_x = int(rng.randint(0, max_tx + 1)) if max_tx > 0 else 0

    composite_img = img_a.copy()
    composite_mask = mask_a.copy()

    region_a = composite_img[pos_y : pos_y + th, pos_x : pos_x + tw]
    if blend_boundary:
        alpha_mask = cv2.GaussianBlur(patch_mask_resized.astype(np.float32), (5, 5), 1.0)[:, :, None]
    else:
        alpha_mask = patch_mask_resized.astype(np.float32)[:, :, None]

    blended_region = (region_a.astype(np.float32) * (1.0 - alpha_mask) +
                      patch_rgb_resized.astype(np.float32) * alpha_mask).astype(np.uint8)
    composite_img[pos_y : pos_y + th, pos_x : pos_x + tw] = blended_region
    composite_mask[pos_y : pos_y + th, pos_x : pos_x + tw][patch_mask_resized] = paste_class

    composite_dishes = []
    for dish in row_a.get("dishes", []):
        cid = int(dish.get("class_id", 0))
        rem_px = int(np.count_nonzero(composite_mask == cid))
        orig_px = int(np.count_nonzero(mask_a == cid))
        frac = rem_px / max(1, orig_px) if orig_px > 0 else 1.0
        composite_dishes.append({
            "class_id": cid,
            "name": dish.get("name"),
            "weight_g": round(float(dish.get("weight_g", 0.0)) * frac, 1),
            "source": "source_a",
            "pixel_retention": round(frac, 3),
        })

    dish_b_match = next((d for d in dishes_b if int(d.get("class_id", 0)) == paste_class), None)
    b_weight = float(dish_b_match.get("weight_g", 50.0)) if dish_b_match else 50.0
    pasted_px = int(np.count_nonzero(patch_mask_resized))
    total_px_b = int(np.count_nonzero(mask_b == paste_class))
    b_frac = pasted_px / max(1, total_px_b) if total_px_b > 0 else 1.0
    composite_dishes.append({
        "class_id": paste_class,
        "name": dish_b_match.get("name", f"class_{paste_class}") if dish_b_match else f"class_{paste_class}",
        "weight_g": round(b_weight * b_frac, 1),
        "source": "source_b",
        "pixel_retention": round(b_frac, 3),
    })

    source_a_sha = sha256_file(img_path_a)
    source_b_sha = sha256_file(img_path_b)
    mask_a_sha = sha256_file(mask_path_a) if mask_path_a and mask_path_a.is_file() else None
    mask_b_sha = sha256_file(mask_path_b) if mask_path_b and mask_path_b.is_file() else None

    result = {
        "source_a": {
            "source_group_id": wed_group_id(row_a),
            "source_record_id": str(row_a["image"]),
            "source_split": "train",
            "source_image_sha256": source_a_sha,
            "source_mask_sha256": mask_a_sha,
        },
        "source_b": {
            "source_group_id": wed_group_id(row_b),
            "source_record_id": str(row_b["image"]),
            "source_split": "train",
            "source_image_sha256": source_b_sha,
            "source_mask_sha256": mask_b_sha,
        },
        "pasted_class_id": paste_class,
        "composite_dishes": composite_dishes,
        "seed": seed,
    }

    if output_dir is not None:
        out_p = Path(output_dir)
        out_p.mkdir(parents=True, exist_ok=True)
        stem = f"cutmix_{seed}_{wed_group_id(row_a)}_{wed_group_id(row_b)}"
        img_out = out_p / f"{stem}.png"
        mask_out = out_p / f"{stem}.mask.png"
        cv2.imwrite(str(img_out), composite_img)
        cv2.imwrite(str(mask_out), composite_mask)
        result["output_image_path"] = str(img_out)
        result["output_mask_path"] = str(mask_out)
        result["output_image_sha256"] = sha256_file(img_out)
        result["output_mask_sha256"] = sha256_file(mask_out)

    return result

