"""Freeze hashes and existing evidence for the real NutriSense pipeline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "synthetic_food" / "baseline_freeze.json"


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(relative: str) -> tuple[Path, dict[str, Any]]:
    path = ROOT / relative
    return path, json.loads(path.read_text(encoding="utf-8"))


def freeze() -> dict[str, Any]:
    integrated_path, integrated = _read("experiments/real_pipeline_baseline/dev_report.json")
    segmentation_path, segmentation = _read("experiments/wed_native_segmentation/dev_report.json")
    depth_path, depth = _read("experiments/real_pipeline_baseline/renderer_metric_depth.json")
    geometry_path, geometry = _read("experiments/real_pipeline_baseline/renderer_geometry.json")

    artifact_paths = [
        "data/gallery.npz",
        "data/weight_head.pt",
        "data/weight_head_sigma.yaml",
        "models/model_revisions.py",
        "models/food_classifier.py",
        "models/wed_inference.py",
        "models/wed_semantic_segmenter.py",
        "models/portion_estimator.py",
        "models/scale_anchor.py",
        "models/weight_head.py",
        "engine/depth.py",
        "engine/pipeline.py",
        "main.py",
        "experiments/wed_native_segmentation/model_wed_semantic_baseline.pt",
        "experiments/wed_native_segmentation/baseline_manifest.json",
        "experiments/wed_native_segmentation/dev_report.json",
        "experiments/real_pipeline_baseline/dev_report.json",
        "experiments/real_pipeline_baseline/renderer_metric_depth.json",
        "experiments/real_pipeline_baseline/renderer_geometry.json",
        "experiments/real_pipeline_baseline/renderer_depth_geometry_report.md",
        "docs/integrated-real-pipeline.md",
    ]
    artifacts = []
    for relative in artifact_paths:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Cannot freeze missing reference artifact: {relative}")
        artifacts.append({"path": relative, "sha256": _sha(path), "bytes": path.stat().st_size})

    config_files = [ROOT / item for item in (
        "data/weight_head_sigma.yaml", "models/model_revisions.py", "engine/pipeline.py",
        "engine/depth.py", "models/portion_estimator.py", "models/scale_anchor.py",
        "models/wed_inference.py",
    )]
    config_hash = hashlib.sha256("\n".join(
        f"{path.relative_to(ROOT)}:{_sha(path)}" for path in config_files
    ).encode()).hexdigest()

    dev_split = str(integrated["dev_group_sha256"])
    stages = {
        "classification": {
            "model_sha256": hashlib.sha256((
                str(integrated["classifier_gallery_sha256"]) + _sha(ROOT / "models/model_revisions.py")
            ).encode()).hexdigest(),
            "data_sha256": integrated["input_image_sha256"],
            "split_sha256": dev_split,
            "group_count": int(integrated["n_groups"]),
            "metrics": {
                "integrated_food_pixel_class_accuracy": integrated["classification"]["food_pixel_class_accuracy"],
                "exact_semantic_class_set_rate": integrated["classification"]["exact_semantic_class_set_rate"],
                "scope": "Integrated labels are produced by DeepLabV3; the separate SigLIP DEV crop result has gallery overlap and is excluded as an independent classifier score.",
            },
            "uncertainty": {"source": "fixed DEV point estimate; class-level confidence intervals not available"},
        },
        "segmentation": {
            "model_sha256": segmentation["checkpoint_sha256"],
            "data_sha256": segmentation["data_sha256"],
            "split_sha256": segmentation["dev_group_sha256"],
            "group_count": int(segmentation["metrics"]["n_groups"]),
            "metrics": {
                "macro_food_iou": segmentation["metrics"]["pixel"]["macro_food_iou"],
                "foreground_iou": segmentation["metrics"]["pixel"]["foreground_union"]["iou"],
                "region_f1": integrated["segmentation"]["region_f1"],
            },
            "uncertainty": segmentation["metrics"]["pixel"]["group_bootstrap_95ci"],
        },
        "depth_geometry": {
            "model_sha256": hashlib.sha256((
                str(depth["model"]) + _sha(ROOT / "engine/depth.py") + _sha(ROOT / "models/portion_estimator.py")
            ).encode()).hexdigest(),
            "data_sha256": hashlib.sha256((depth["data_sha256"] + geometry["data_sha256"]).encode()).hexdigest(),
            "split_sha256": hashlib.sha256(("renderer-scenes:" + str(depth["groups"])).encode()).hexdigest(),
            "group_count": int(depth["groups"]),
            "metrics": {
                "calibrated_card_abs_rel": 0.0304,
                "calibrated_card_mae_m": 0.0183,
                "renderer_geometry_mass_mae_g": geometry["summary"]["mass_mae_g"],
                "real_depth_accuracy_claim": False,
            },
            "uncertainty": {"source": "renderer-only controlled diagnostics; not a real-camera interval"},
        },
        "weight": {
            "model_sha256": integrated["weight_head_checkpoint_sha256"],
            "data_sha256": integrated["ground_truth_mask_sha256"],
            "split_sha256": dev_split,
            "group_count": int(integrated["n_groups"]),
            "metrics": {
                "individual_class_total_mae_g": integrated["weight"]["individual_class_mass_mae_g"],
                "meal_total_mae_g": integrated["weight"]["total_meal_mae_g"],
                "meal_total_bias_g": integrated["weight"]["total_meal_bias_g"],
            },
            "uncertainty": {
                "nominal_90_interval_coverage": integrated["weight"]["total_meal_90_interval_coverage"],
                "mean_90_interval_width_g": integrated["weight"]["mean_total_90_interval_width_g"],
            },
        },
        "end_to_end": {
            "model_sha256": integrated["pipeline_sha256"],
            "data_sha256": integrated["input_image_sha256"],
            "split_sha256": dev_split,
            "group_count": int(integrated["n_groups"]),
            "metrics": {
                "meal_total_mae_g": integrated["weight"]["total_meal_mae_g"],
                "meal_total_bias_g": integrated["weight"]["total_meal_bias_g"],
                "complete_weighted_class_coverage_meals": integrated["weight"]["complete_meal_weight_outputs"],
                "view_count": integrated["n_views"],
            },
            "uncertainty": {
                "nominal_90_interval_coverage": integrated["weight"]["total_meal_90_interval_coverage"],
                "mean_90_interval_width_g": integrated["weight"]["mean_total_90_interval_width_g"],
            },
        },
    }
    report = {
        "feature": "synthetic-food-corpus",
        "version": 1,
        "frozen": True,
        "created_at_utc": integrated["created_at_utc"],
        "integrated_configuration_sha256": config_hash,
        "stages": stages,
        "frozen_artifacts": artifacts,
        "limitations": [
            "The independent SigLIP crop report is contaminated by WED DEV gallery overlap; it is not frozen as independent classification accuracy.",
            "Depth and geometry accuracy evidence is renderer-controlled only.",
            "Weight uncertainty intervals cover 81.5% against a nominal 90% target on DEV.",
            "WED semantic labels do not provide serving-level instance identities.",
        ],
        "locked_accessed": False,
        "aruco_evaluation_accessed": False,
        "wed_test_accessed": False,
        "synthetic_generation_used_in_baseline": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    frozen = freeze()
    print(json.dumps({"report": str(OUT.relative_to(ROOT)),
                      "artifacts": len(frozen["frozen_artifacts"]),
                      "configuration_sha256": frozen["integrated_configuration_sha256"]}, indent=2))
