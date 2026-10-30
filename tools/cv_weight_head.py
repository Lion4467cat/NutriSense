"""Outer plate-grouped CV over WED TRAIN, with an inner val carve per fold.

The WED DEV carve is excluded from every fold's gradients and selection data;
WED test/LOCKED is never opened. Each outer fold selects its epoch using a
separate plate group from the remaining TRAIN plates, then scores the held
outer plates once. This tool writes fold artifacts under ignored data/cache.

Run: .venv/bin/python -m tools.cv_weight_head --folds 5 --epochs 100
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cv(*, folds: int, epochs: int, seed: int, encoder: str,
           weight_decay: float = 1e-4, tag: str | None = None,
           limit: int | None = None) -> dict:
    if folds < 2:
        raise ValueError("folds must be >= 2")
    label = tag or f"wd{weight_decay:g}"
    safe_label = "".join(ch if ch.isalnum() or ch in "-_" else "_"
                         for ch in label)
    report_root = ROOT / "data" / "cache" / (
        f"weight_cv_{seed}_{folds}_{safe_label}")
    report_root.mkdir(parents=True, exist_ok=True)
    runs = []
    for fold in range(folds):
        prefix = report_root / f"fold_{fold}"
        command = [
            sys.executable, "-m", "tools.train_weight_head",
            "--cv-folds", str(folds), "--cv-fold-index", str(fold),
            "--epochs", str(epochs), "--seed", str(seed),
            "--encoder", encoder, "--features-cache", "none",
            "--weight-decay", str(weight_decay),
            "--out", str(prefix.with_suffix(".pt")),
            "--sigma-out", str(prefix.with_suffix(".yaml")),
            "--report-out", str(prefix.with_suffix(".json")),
        ]
        if limit is not None:
            command += ["--limit", str(limit)]
        subprocess.run(command, cwd=ROOT, check=True)
        report = json.loads(prefix.with_suffix(".json").read_text())
        result = report.get("outer_cv")
        if not result:
            raise RuntimeError(f"fold {fold} did not produce outer-CV metrics")
        result["artifact_sha256"] = {}
        for suffix in (".pt", ".yaml", ".json"):
            result["artifact_sha256"][suffix[1:]] = hashlib.sha256(
                prefix.with_suffix(suffix).read_bytes()).hexdigest()
        runs.append(result)

    all_plates = [plate for row in runs for plate in row["held_out_plates"]]
    if len(all_plates) != len(set(all_plates)):
        raise RuntimeError("outer fold plate overlap detected")
    n_rois = sum(row["n_rois"] for row in runs)
    absolute_error_sum = sum(
        float(plate["sum_abs_err_g"])
        for row in runs for plate in row["per_plate_errors"].values())
    weighted_mae = absolute_error_sum / max(1, n_rois)
    payload = {
        "protocol": "outer plate-grouped CV over WED TRAIN; inner plate carve for epoch selection",
        "seed": seed,
        "folds": folds,
        "epochs": epochs,
        "encoder": encoder,
        "weight_decay": weight_decay,
        "tag": safe_label,
        "limit": limit,
        "n_outer_plates": len(all_plates),
        "n_outer_rois": n_rois,
        "weighted_outer_mae_g": round(weighted_mae, 3),
        "fold_mae_std_g": round(
            statistics.pstdev([r["mae_g"] for r in runs]), 3),
        "manifest_sha256": hashlib.sha256(
            (ROOT / "data" / "wed_manifest.jsonl").read_bytes()).hexdigest(),
        "code_sha256": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("tools/cv_weight_head.py",
                         "tools/train_weight_head.py")
        },
        "fold_results": runs,
        "limitations": [
            "CV folds estimate variability within WED TRAIN; WED DEV remains an epoch-selection carve and is not independent.",
            "No WED LOCKED records are accessed by this tool.",
            "Fold-level MAEs are not a candidate-versus-baseline paired promotion test.",
        ],
    }
    out = ROOT / "data" / "reports" / (
        f"cv_weight_head_s{seed}_k{folds}_{safe_label}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    print(f"wrote {out}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--encoder", choices=("dinov2", "resnet50"),
                        default="dinov2")
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--tag", default=None,
                        help="artifact/report label; defaults to the decay")
    parser.add_argument("--limit", type=int, default=None,
                        help="smoke-only row cap; report will be exploratory")
    args = parser.parse_args()
    run_cv(folds=args.folds, epochs=args.epochs, seed=args.seed,
           encoder=args.encoder, weight_decay=args.weight_decay,
           tag=args.tag, limit=args.limit)


if __name__ == "__main__":
    main()
