"""DEV-only error profile for the current deployable WED weight head.

Unlike ``tools.run_eval`` this sidecar reports signed bias, RMSE, portion-size
bands, and plate-level totals. It never accepts a split argument, so it cannot
read WED test/LOCKED data. Its 95% intervals resample physical plates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch

from tools import run_eval

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_REPS = 2000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_revision() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=10
        ).strip()
    except Exception:
        return "unknown"


def _metrics(samples: list[dict[str, float]]) -> dict[str, float | int | None]:
    errors = np.asarray([s["pred"] - s["gt"] for s in samples], dtype=float)
    abs_errors = np.abs(errors)
    weights = np.asarray([s["gt"] for s in samples], dtype=float)
    valid_pct = weights >= 1.0
    return {
        "n": int(len(samples)),
        "mae_g": round(float(abs_errors.mean()), 3),
        "median_absolute_error_g": round(float(np.median(abs_errors)), 3),
        "rmse_g": round(float(np.sqrt(np.mean(np.square(errors)))), 3),
        "mean_bias_g": round(float(errors.mean()), 3),
        "p90_absolute_error_g": round(float(np.percentile(abs_errors, 90)), 3),
        "mape_pct": (round(float(np.mean(abs_errors[valid_pct] / weights[valid_pct])
                                  * 100), 3) if valid_pct.any() else None),
    }


def _plate_totals(samples: list[dict[str, float | str]]) -> list[dict[str, float | str | int]]:
    """Average repeated view estimates per plate/dish, then sum dishes once."""
    grouped: dict[tuple[str, str], list[dict[str, float | str]]] = defaultdict(list)
    for row in samples:
        grouped[(str(row["plate"]), str(row["dish"]))].append(row)
    by_plate: dict[str, list[dict[str, float]]] = defaultdict(list)
    for (plate, _dish), views in grouped.items():
        preds = [float(row["pred"]) for row in views]
        gts = [float(row["gt"]) for row in views]
        # WED views of one physical plate/dish should share one mass target.
        if max(gts) - min(gts) > 1e-6:
            raise ValueError(f"WED target changes across views: {plate}/{_dish}")
        by_plate[plate].append({
            "pred": float(np.mean(preds)),
            "gt": float(np.mean(gts)),
        })
    return [
        {
            "plate": plate,
            "n_foods": len(dishes),
            "n_views": sum(len(grouped[(plate, dish)]) for dish in
                           {key[1] for key in grouped if key[0] == plate}),
            "predicted_total_g": round(sum(item["pred"] for item in dishes), 3),
            "ground_truth_total_g": round(sum(item["gt"] for item in dishes), 3),
        }
        for plate, dishes in sorted(by_plate.items())
    ]


def _bootstrap_ci(
    groups: dict[str, list[dict[str, float]]],
    metric,
    *, seed: int,
) -> list[float]:
    keys = sorted(groups)
    if len(keys) < 2:
        return [None, None]
    rng = random.Random(seed)
    estimates = []
    for _ in range(BOOTSTRAP_REPS):
        picked = [rng.choice(keys) for _ in keys]
        resampled = [sample for key in picked for sample in groups[key]]
        estimates.append(metric(resampled))
    return [round(float(value), 3) for value in np.percentile(estimates, [2.5, 97.5])]


def _add_grouped_intervals(samples: list[dict], plates: list[dict]) -> dict:
    by_plate: dict[str, list[dict[str, float]]] = defaultdict(list)
    for row in samples:
        by_plate[str(row["plate"])].append(row)
    total_groups = {
        str(row["plate"]): [{
            "pred": float(row["predicted_total_g"]),
            "gt": float(row["ground_truth_total_g"]),
        }]
        for row in plates
    }
    return {
        "item_mae_g": _bootstrap_ci(
            by_plate,
            lambda rows: float(np.mean([abs(r["pred"] - r["gt"])
                                        for r in rows])),
            seed=42,
        ),
        "item_bias_g": _bootstrap_ci(
            by_plate,
            lambda rows: float(np.mean([r["pred"] - r["gt"]
                                        for r in rows])),
            seed=43,
        ),
        "plate_total_mae_g": _bootstrap_ci(
            total_groups,
            lambda rows: float(np.mean([abs(r["pred"] - r["gt"])
                                        for r in rows])),
            seed=44,
        ),
        "plate_total_bias_g": _bootstrap_ci(
            total_groups,
            lambda rows: float(np.mean([r["pred"] - r["gt"]
                                        for r in rows])),
            seed=45,
        ),
    }


def _cross_fitted_affine(samples: list[dict]) -> dict:
    """Fit y=a+b*prediction on all other DEV plates for each held-out plate."""
    by_plate: dict[str, list[dict]] = defaultdict(list)
    for row in samples:
        by_plate[str(row["plate"])].append(row)
    if len(by_plate) < 3:
        raise ValueError("Need at least three DEV plates for cross-fitted calibration")

    predictions: list[dict] = []
    coefficients: dict[str, dict[str, float]] = {}
    plate_keys = sorted(by_plate)
    for held_out in plate_keys:
        train = [row for plate in plate_keys if plate != held_out
                 for row in by_plate[plate]]
        x = np.asarray([float(row["pred"]) for row in train], dtype=float)
        y = np.asarray([float(row["gt"]) for row in train], dtype=float)
        intercept, slope = np.linalg.lstsq(
            np.column_stack([np.ones_like(x), x]), y, rcond=None
        )[0]
        coefficients[held_out] = {
            "intercept_g": round(float(intercept), 4),
            "slope": round(float(slope), 6),
        }
        for row in by_plate[held_out]:
            adjusted = max(0.0, float(intercept + slope * float(row["pred"])))
            predictions.append({**row, "base_pred": float(row["pred"]),
                                "pred": adjusted})

    delta_groups: dict[str, list[dict[str, float]]] = defaultdict(list)
    for row in predictions:
        delta_groups[str(row["plate"])].append({
            "pred": abs(float(row["pred"]) - float(row["gt"])),
            "gt": abs(float(row["base_pred"]) - float(row["gt"])),
        })
    delta_ci = _bootstrap_ci(
        delta_groups,
        lambda rows: float(np.mean([r["pred"] - r["gt"] for r in rows])),
        seed=46,
    )
    return {
        "method": "leave-one-plate-out affine calibration; fit target on all other DEV plates",
        "metrics": _metrics(predictions),
        "paired_mae_change_g_calibrated_minus_base": round(float(np.mean([
            abs(float(row["pred"]) - float(row["gt"]))
            - abs(float(row["base_pred"]) - float(row["gt"]))
            for row in predictions
        ])), 3),
        "paired_mae_change_g_bootstrap_95ci": delta_ci,
        "fold_coefficients": coefficients,
        "note": "Exploratory DEV-only cross-fit; not applied to serving and not an independent test result.",
    }
def build_report(*, batch: int = 4) -> dict:
    started = time.time()
    rows = run_eval.dev_rows()
    if "test" in run_eval.LOADED:
        raise RuntimeError("split guard: diagnostics must not read WED test data")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = run_eval.WeightHead.load(ROOT / "data" / "weight_head.pt", device=device)
    samples = run_eval.score(model, rows, run_eval.wed_root(), device, batch=batch)
    if "test" in run_eval.LOADED:
        raise RuntimeError("split guard: WED test data was read")

    for row in samples:
        row["plate"] = str(row["plate"])
        row["dish"] = str(row["dish"])
        row["pred"] = float(row["pred"])
        row["gt"] = float(row["gt"])
    plate_rows = _plate_totals(samples)
    bands = {
        "lt_50g": [row for row in samples if float(row["gt"]) < 50],
        "50_to_lt_100g": [row for row in samples if 50 <= float(row["gt"]) < 100],
        "100_to_lt_200g": [row for row in samples if 100 <= float(row["gt"]) < 200],
        "ge_200g": [row for row in samples if float(row["gt"]) >= 200],
    }
    by_dish: dict[str, list[dict]] = defaultdict(list)
    for row in samples:
        by_dish[str(row["dish"])].append(row)
    report = {
        "created_utc": datetime.now(UTC).isoformat(),
        "tier": "dev",
        "split": "WED val carve from train plates (seed 42, 10% of plates)",
        "n_views": len(rows),
        "n_plates": len({row["plate"] for row in samples}),
        "n_samples": len(samples),
        "metrics": _metrics(samples),
        "portion_size_bands": {name: _metrics(group) for name, group in bands.items()},
        "per_dish": {
            dish: _metrics(group)
            for dish, group in sorted(by_dish.items())
        },
        "plate_totals": {
            "metrics": _metrics([
                {"pred": float(row["predicted_total_g"]),
                 "gt": float(row["ground_truth_total_g"])}
                for row in plate_rows
            ]),
            "by_plate": plate_rows,
        },
        "grouped_bootstrap_95ci": {},
        "cross_fitted_affine_calibration": _cross_fitted_affine(samples),
        "bootstrap_reps": BOOTSTRAP_REPS,
        "checkpoint_sha256": _sha256(ROOT / "data" / "weight_head.pt"),
        "weight_head_code_sha256": _sha256(ROOT / "models" / "weight_head.py"),
        "run_eval_code_sha256": _sha256(ROOT / "tools" / "run_eval.py"),
        "manifest_sha256": _sha256(ROOT / "data" / "wed_manifest.jsonl"),
        "git_revision": _git_revision(),
        "device": str(device),
        "batch_size": batch,
    }
    report["grouped_bootstrap_95ci"] = _add_grouped_intervals(samples, plate_rows)
    report["wall_s"] = round(time.time() - started, 2)
    if device.type == "cuda":
        report["peak_vram_mb"] = round(torch.cuda.max_memory_allocated() / 2**20, 1)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", type=Path,
        default=ROOT / "data" / "reports" / "run_eval_diagnostics_dev.json",
    )
    parser.add_argument("--batch", type=int, default=4)
    args = parser.parse_args(argv)
    if args.batch < 1:
        parser.error("--batch must be positive")
    report = build_report(batch=args.batch)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"tier=dev mae_g={report['metrics']['mae_g']} "
          f"rmse_g={report['metrics']['rmse_g']} "
          f"bias_g={report['metrics']['mean_bias_g']} "
          f"plate_total_mae_g={report['plate_totals']['metrics']['mae_g']} "
          f"report={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
