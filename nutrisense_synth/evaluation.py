"""Evaluation metadata and baseline evidence readiness report."""
from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import platform
from pathlib import Path
import subprocess
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BASELINE_STAGES = ("classification", "segmentation", "depth_geometry", "weight", "end_to_end")


def require_frozen_baseline(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"Frozen baseline report is missing: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("frozen") is not True:
        raise ValueError("Baseline report must have frozen=true")
    for stage in BASELINE_STAGES:
        entry = report.get("stages", {}).get(stage)
        if not isinstance(entry, dict) or not entry.get("metrics"):
            raise ValueError(f"Frozen baseline is missing {stage} metrics")
        for key in ("model_sha256", "data_sha256", "split_sha256"):
            if not entry.get(key):
                raise ValueError(f"Frozen baseline {stage} is missing {key}")
        if int(entry.get("group_count", 0)) < 1 or not entry.get("uncertainty"):
            raise ValueError(f"Frozen baseline {stage} must include group_count and uncertainty")
    artifacts = report.get("frozen_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("Frozen baseline must list its immutable artifact hashes")
    for artifact in artifacts:
        rel = Path(str(artifact.get("path", "")))
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError(f"Frozen artifact path must be repository-relative: {rel}")
        target = ROOT / rel
        if not target.is_file():
            raise ValueError(f"Frozen baseline artifact is missing: {rel}")
        if sha256_file(target) != artifact.get("sha256"):
            raise ValueError(f"Frozen baseline artifact changed: {rel}")
    return report


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                       text=True, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def group_bootstrap_ci(values_by_group: dict[str, list[float]], *, seed: int = 42,
                       reps: int = 2000) -> list[float | None]:
    groups = sorted(values_by_group)
    if len(groups) < 2 or reps < 1:
        return [None, None]
    rng = np.random.default_rng(seed)
    estimates = []
    for _ in range(reps):
        selected = rng.choice(groups, size=len(groups), replace=True)
        values = [value for group in selected for value in values_by_group[str(group)]]
        if values:
            estimates.append(float(np.mean(values)))
    return [float(np.quantile(estimates, 0.025)), float(np.quantile(estimates, 0.975))]


def metric_depth_metrics(predicted_m: np.ndarray, target_m: np.ndarray,
                         mask: np.ndarray | None = None) -> dict[str, float | int]:
    """Metric-depth scores against renderer camera-Z ground truth.

    Both maps must use metres. Invalid predictions are counted in coverage
    and excluded from error metrics so a caller cannot silently hide them.
    """
    pred = np.asarray(predicted_m, dtype=np.float64)
    target = np.asarray(target_m, dtype=np.float64)
    if pred.shape != target.shape:
        raise ValueError(f"Depth shape mismatch: prediction {pred.shape}, target {target.shape}")
    selected = (np.ones(target.shape, dtype=bool) if mask is None
                else np.array(mask, dtype=bool, copy=True))
    if selected.shape != target.shape:
        raise ValueError("Depth metric mask must match depth maps")
    selected &= np.isfinite(target) & (target > 0)
    n_target = int(selected.sum())
    if n_target == 0:
        raise ValueError("Depth metrics require at least one valid target pixel")
    valid = selected & np.isfinite(pred) & (pred > 0)
    n_valid = int(valid.sum())
    if n_valid == 0:
        raise ValueError("Depth metrics require at least one valid prediction")
    p, t = pred[valid], target[valid]
    ratio = np.maximum(p / t, t / p)
    log_error = np.log(p) - np.log(t)
    return {
        "mae_m": float(np.mean(np.abs(p - t))),
        "rmse_m": float(np.sqrt(np.mean((p - t) ** 2))),
        "abs_rel": float(np.mean(np.abs(p - t) / t)),
        "silog_pct": float(100.0 * np.sqrt(max(0.0, np.mean(log_error ** 2)
                                                  - np.mean(log_error) ** 2))),
        "delta_1_25": float(np.mean(ratio < 1.25)),
        "median_prediction_to_target_scale": float(np.median(p / t)),
        "median_prediction_m": float(np.median(p)),
        "median_target_m": float(np.median(t)),
        "valid_prediction_fraction": float(n_valid / n_target),
        "target_pixels": n_target,
        "valid_prediction_pixels": n_valid,
    }


def build_depth_report(*, synthetic_metrics: dict[str, float],
                       marker_scale_diagnostics: dict[str, Any],
                       model_sha256: str, data_sha256: str,
                       split_sha256: str, configuration: dict[str, Any],
                       group_count: int) -> dict[str, Any]:
    if group_count < 1 or not (model_sha256 and data_sha256 and split_sha256):
        raise ValueError("Depth reports require hashes and at least one source group")
    return {
        "stage": "depth_geometry",
        "synthetic_metric_depth": {
            "ground_truth_source": "renderer",
            "metrics": synthetic_metrics,
            "group_count": group_count,
        },
        "real_marker_scale_diagnostics": {
            "metrics": marker_scale_diagnostics,
            "depth_accuracy_claim": False,
        },
        "real_depth_accuracy_claim": False,
        "model_sha256": model_sha256,
        "data_sha256": data_sha256,
        "split_sha256": split_sha256,
        "configuration": configuration,
    }


def baseline_preflight(reports_dir: Path = ROOT / "data" / "reports") -> dict[str, Any]:
    """Summarize evidence already present without treating contaminated reports as baselines."""
    classifier_path = reports_dir / "classifier_41way_dev.json"
    weight_path = reports_dir / "run_eval_dev_008_baseline.json"
    stages: dict[str, Any] = {
        "classification": {
            "status": "blocked_contaminated_reference" if classifier_path.exists() else "missing",
            "source_report": str(classifier_path.relative_to(ROOT)) if classifier_path.exists() else None,
            "limitation": "Saved classifier report has DEV gallery-source overlap; not a clean frozen baseline.",
        },
        "segmentation": {
            "status": "blocked_metrics_not_run",
            "limitation": "WED semantic masks are available, but SAM2 has no real WED DEV IoU/Dice evaluation report yet.",
        },
        "depth_geometry": {
            "status": "blocked_metrics_not_frozen",
            "limitation": "The required synthetic metric-depth baseline and real marker/scale diagnostics have not been frozen together.",
        },
        "weight": {
            "status": "reference_available_for_baseline_review" if weight_path.exists() else "missing",
            "source_report": str(weight_path.relative_to(ROOT)) if weight_path.exists() else None,
            "limitation": "Existing DEV reference is available; verify hashes/configuration and freeze it before candidate tuning.",
        },
        "end_to_end": {
            "status": "blocked_missing_report",
            "limitation": "No real DEV full-meal critical-failure baseline is recorded for this feature.",
        },
    }
    return {
        "feature": "009-synthetic-training-data",
        "created_at": datetime.now(UTC).isoformat(),
        "git_revision": git_revision(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "stages": stages,
        "frozen": False,
        "candidate_generation_allowed": False,
        "reason": "At least one required stage lacks an uncontaminated independent baseline.",
        "locked_accessed": False,
        "aruco_accessed": False,
    }
