"""One-shot evaluation of the frozen train/dev LeFood candidate on test classes."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = HERE / "manifest.csv"
CHECKPOINT = HERE / "candidate.pt"
OUTPUT = HERE / "raw_candidate_test.jsonl"
REPORT = HERE / "RESULTS_CANDIDATE_TEST.md"
DEVICE = "cuda"
RESIZE = (224, 224)
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
BATCH_SIZE = 16


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    started = time.perf_counter()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; refusing CPU fallback")
    with MANIFEST.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["split"] == "test"]
    rows.sort(key=lambda row: int(row["row_id"]))
    if not rows:
        raise RuntimeError("manifest contains no test rows")
    from models.weight_head import WeightHead
    model = WeightHead.load(CHECKPOINT, device=DEVICE)
    transform = transforms.Compose([
        transforms.Resize(RESIZE), transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    metadata = {
        "event": "run_metadata",
        "dataset": "LeFood-Set V1",
        "doi": "10.17632/cchsk79jkt.1",
        "split_read": "test",
        "candidate_selection_allowed": False,
        "train_split_read": False,
        "dev_split_read": False,
        "candidate_checkpoint_sha256": sha256(CHECKPOINT),
        "manifest_sha256": sha256(MANIFEST),
        "cuda_device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "cuda_version": torch.version.cuda,
        "image_count": len(rows),
        "test_category_count": len({row["food_name"] for row in rows}),
        "target_source": "Mendeley Weight Before Eaten (g), source-described food mass",
        "target_tare_caveat": "paper does not document tare handling",
        "baseline_global_median_g": 36.0,
    }
    OUTPUT.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metadata, sort_keys=True), flush=True)
    model.eval()
    records = []
    with torch.inference_mode():
        for start in range(0, len(rows), BATCH_SIZE):
            batch_rows = rows[start:start + BATCH_SIZE]
            tensors = []
            for row in batch_rows:
                path = ROOT / row["before_path"]
                with Image.open(path) as image:
                    tensors.append(transform(image.convert("RGB")))
            pixels = torch.stack(tensors).to(DEVICE)
            features = model.encode(pixels, no_grad=True)
            h, w = features.shape[-2:]
            rois = torch.tensor([[i, 0.0, 0.0, float(w), float(h)]
                                 for i in range(len(batch_rows))],
                                dtype=torch.float, device=DEVICE)
            outputs = model(features, rois).squeeze(1).clamp(min=0).square()
            estimates = outputs.detach().cpu().tolist()
            for row, estimate in zip(batch_rows, estimates, strict=True):
                record = {
                    "event": "image_result",
                    "row_id": row["row_id"],
                    "food_category_truth": row["food_name"],
                    "image": row["before_path"],
                    "ground_truth_food_g": float(row["before_g"]),
                    "predicted_total_g": float(estimate),
                    "baseline_global_median_g": 36.0,
                }
                records.append(record)
                with OUTPUT.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(record, sort_keys=True) + "\n")
                print(json.dumps({"event": "image_complete", "row_id": row["row_id"],
                                  "category": row["food_name"],
                                  "predicted_total_g": round(float(estimate), 3)},
                                 sort_keys=True), flush=True)
    truth = np.asarray([r["ground_truth_food_g"] for r in records], dtype=np.float64)
    pred = np.asarray([r["predicted_total_g"] for r in records], dtype=np.float64)
    median = np.full_like(truth, 36.0)
    report = {
        "test_count": len(records),
        "test_category_count": len({r["food_category_truth"] for r in records}),
        "candidate_mae_g": float(np.mean(np.abs(pred - truth))),
        "candidate_signed_bias_g": float(np.mean(pred - truth)),
        "train_global_median_mae_g": float(np.mean(np.abs(median - truth))),
        "candidate_minus_median_mae_g": float(
            np.mean(np.abs(pred - truth)) - np.mean(np.abs(median - truth))),
        "checkpoint_sha256": sha256(CHECKPOINT),
        "raw_jsonl": str(OUTPUT),
        "test_used_for_selection": False,
        "wall_elapsed_s": time.perf_counter() - started,
    }
    lines = [
        "# LeFood-Set one-shot candidate test results", "",
        "The candidate and best epoch were frozen using train/dev categories before this run. "
        "The six test categories were not used for training or selection. This evaluates only "
        "single-food mass transfer, not mixed-meal production behavior.", "",
        "The source calls the target food weight; the paper does not document tare handling. "
        "Treat the target-semantics caveat as unresolved.", "",
        f"Candidate checkpoint SHA-256: `{report['checkpoint_sha256']}`.", "",
        "| Metric | Candidate | Train-only global median | Candidate minus baseline |",
        "|---|---:|---:|---:|",
        f"| Test MAE g | {report['candidate_mae_g']:.3f} | "
        f"{report['train_global_median_mae_g']:.3f} | {report['candidate_minus_median_mae_g']:+.3f} |",
        f"| Signed bias g | {report['candidate_signed_bias_g']:+.3f} | — | — |",
        "",
        "## Per-category results", "",
        "| Food category | Pairs | Mean true g | Mean candidate g | MAE g | Bias g |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    categories = sorted({r["food_category_truth"] for r in records})
    for category in categories:
        cat = [r for r in records if r["food_category_truth"] == category]
        y = np.asarray([r["ground_truth_food_g"] for r in cat])
        p = np.asarray([r["predicted_total_g"] for r in cat])
        lines.append(f"| {category} | {len(cat)} | {y.mean():.1f} | {p.mean():.1f} | "
                     f"{np.mean(np.abs(p-y)):.1f} | {np.mean(p-y):+.1f} |")
    lines.extend(["", "## Per-image predictions", "",
                  "| Row | Food | True g | Pred g | Signed error g | Error % |",
                  "|---:|---|---:|---:|---:|---:|"])
    for row in records:
        error = row["predicted_total_g"] - row["ground_truth_food_g"]
        percent = 100.0 * error / row["ground_truth_food_g"] if row["ground_truth_food_g"] else None
        lines.append(f"| {row['row_id']} | {row['food_category_truth']} | "
                     f"{row['ground_truth_food_g']:.1f} | {row['predicted_total_g']:.1f} | "
                     f"{error:+.1f} | {'—' if percent is None else f'{percent:+.1f}'} |")
    lines.extend(["", "## Scope", "",
                  "This one-shot test result is final for this category split. Do not tune, retrain, "
                  "change thresholds, or select another candidate from it. The test categories are "
                  "Indonesian single-food plates and do not establish performance on mixed Indian meals.", ""])
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    print(f"wrote {REPORT}")
    print(f"wall_elapsed_s={report['wall_elapsed_s']:.3f}")


if __name__ == "__main__":
    main()
