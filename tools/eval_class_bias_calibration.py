"""Cross-fitted DEV-only diagnostic for robust per-food bias correction.

Each plate's correction is fitted from other plates only. This evaluator has
no tier option and refuses to continue if the shared evaluator touched WED
LOCKED. DEV is nevertheless reused for epoch selection, so this is tuning
evidence, not an independent generalization estimate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from tools import run_eval

ROOT = Path(__file__).resolve().parents[1]
MIN_OTHER_PLATES = 5
BOOTSTRAP_REPS = 2000


def _metric(rows: list[dict]) -> dict:
    errors = np.asarray([float(row["pred"]) - float(row["gt"])
                         for row in rows], dtype=float)
    absolute = np.abs(errors)
    targets = np.asarray([float(row["gt"]) for row in rows], dtype=float)
    valid = targets >= 1.0
    return {
        "n": len(rows),
        "mae_g": round(float(absolute.mean()), 4),
        "mean_bias_g": round(float(errors.mean()), 4),
        "rmse_g": round(float(np.sqrt(np.mean(errors ** 2))), 4),
        "mape_pct": round(float(np.mean(absolute[valid] / targets[valid]) * 100), 3)
        if valid.any() else None,
    }


def _coverage(rows: list[dict], sigma: dict[str, float]) -> float:
    hits = []
    for row in rows:
        value = sigma.get(str(row["dish"]))
        if value is not None:
            hits.append(abs(float(row["pred"]) - float(row["gt"]))
                        <= run_eval.Z90 * value)
    return float(np.mean(hits)) if hits else float("nan")


def _plate_bootstrap_delta(base: list[dict], candidate: list[dict]) -> list[float]:
    by_base: dict[str, list[dict]] = defaultdict(list)
    by_candidate: dict[str, list[dict]] = defaultdict(list)
    for row in base:
        by_base[str(row["plate"])].append(row)
    for row in candidate:
        by_candidate[str(row["plate"])].append(row)
    plates = sorted(by_base)
    if plates != sorted(by_candidate):
        raise ValueError("baseline and calibrated predictions have different plates")
    rng = np.random.default_rng(42)
    deltas = []
    for _ in range(BOOTSTRAP_REPS):
        selected = rng.integers(0, len(plates), size=len(plates))
        base_errors, cand_errors = [], []
        for index in selected:
            plate = plates[int(index)]
            base_errors.extend(abs(float(row["pred"]) - float(row["gt"]))
                               for row in by_base[plate])
            cand_errors.extend(abs(float(row["pred"]) - float(row["gt"]))
                               for row in by_candidate[plate])
        deltas.append(float(np.mean(cand_errors) - np.mean(base_errors)))
    return [round(float(value), 4)
            for value in np.percentile(deltas, [2.5, 97.5])]


def cross_fitted(rows: list[dict], *, min_other_plates: int = MIN_OTHER_PLATES) -> tuple[list[dict], dict]:
    by_plate_dish: dict[tuple[str, str], list[dict]] = defaultdict(list)
    plates_by_dish: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        plate, dish = str(row["plate"]), str(row["dish"])
        by_plate_dish[(plate, dish)].append(row)
        plates_by_dish[dish].add(plate)

    plate_mean_residual: dict[tuple[str, str], float] = {
        key: float(np.mean([float(item["pred"]) - float(item["gt"])
                            for item in values]))
        for key, values in by_plate_dish.items()
    }
    output = []
    correction_details: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        plate, dish = str(row["plate"]), str(row["dish"])
        other_residuals = [value for (other_plate, other_dish), value
                           in plate_mean_residual.items()
                           if other_dish == dish and other_plate != plate]
        correction = (float(np.median(other_residuals))
                      if len(other_residuals) >= min_other_plates else 0.0)
        output.append({**row, "base_pred": float(row["pred"]),
                       "pred": max(0.0, float(row["pred"]) - correction),
                       "correction_g": correction})
        correction_details[dish].append({
            "plate": plate,
            "other_plate_support": len(other_residuals),
            "correction_g": round(correction, 4),
        })
    return output, {
        "method": "leave-one-plate-out median of per-plate mean signed food residual",
        "minimum_other_plate_support": min_other_plates,
        "food_classes": len(plates_by_dish),
        "cross_fitted_plate_support": {
            dish: len(plates) for dish, plates in sorted(plates_by_dish.items())
        },
    }


def _bands(rows: list[dict], base_rows: list[dict]) -> dict:
    groups = {
        "lt_50g": lambda gt: gt < 50,
        "50_to_lt_100g": lambda gt: 50 <= gt < 100,
        "100_to_lt_200g": lambda gt: 100 <= gt < 200,
        "ge_200g": lambda gt: gt >= 200,
    }
    result = {}
    for name, predicate in groups.items():
        base_group = [row for row in base_rows if predicate(float(row["gt"]))]
        candidate_group = [row for row in rows if predicate(float(row["gt"]))]
        result[name] = {"baseline": _metric(base_group),
                        "candidate": _metric(candidate_group)}
    return result


def build_report(batch: int = 4) -> dict:
    rows = run_eval.dev_rows()
    if "test" in run_eval.LOADED:
        raise RuntimeError("split guard: WED LOCKED was read")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = run_eval.WeightHead.load(ROOT / "data" / "weight_head.pt", device=device)
    samples = run_eval.score(model, rows, run_eval.wed_root(), device, batch=batch)
    if "test" in run_eval.LOADED:
        raise RuntimeError("split guard: WED LOCKED was read")
    candidate, procedure = cross_fitted(samples)
    sigma = run_eval.sigma_map()
    base_metric, candidate_metric = _metric(samples), _metric(candidate)
    delta = candidate_metric["mae_g"] - base_metric["mae_g"]
    return {
        "tier": "dev",
        "split": "WED 10% train-plate carve; same carve used for epoch selection",
        "n_plates": len({row["plate"] for row in samples}),
        "n_samples": len(samples),
        "baseline": base_metric,
        "cross_fitted_candidate": candidate_metric,
        "paired_mae_change_g_candidate_minus_baseline": round(delta, 4),
        "paired_plate_bootstrap_95ci_g": _plate_bootstrap_delta(samples, candidate),
        "baseline_coverage_90": round(_coverage(samples, sigma), 4),
        "candidate_coverage_90": round(_coverage(candidate, sigma), 4),
        "portion_size_bands": _bands(candidate, samples),
        "procedure": procedure,
        "checkpoint_sha256": hashlib.sha256(
            (ROOT / "data" / "weight_head.pt").read_bytes()
        ).hexdigest(),
        "warning": "DEV was used for epoch selection; this cross-fit prevents direct calibration leakage per plate but is tuning evidence, not an independent generalization estimate.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "data" / "reports" / "run_eval_dev_018_bias_calibration.json")
    parser.add_argument("--batch", type=int, default=4)
    args = parser.parse_args(argv)
    if args.batch < 1:
        parser.error("--batch must be positive")
    report = build_report(args.batch)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"baseline_mae={report['baseline']['mae_g']:.4f}g "
          f"crossfit_mae={report['cross_fitted_candidate']['mae_g']:.4f}g "
          f"delta={report['paired_mae_change_g_candidate_minus_baseline']:+.4f}g "
          f"paired_ci={report['paired_plate_bootstrap_95ci_g']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
