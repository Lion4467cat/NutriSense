"""One-shot test of the frozen plate-total candidate on participant 6."""
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
DATA = ROOT / "datasets/raw/portion/vlm-food-benchmark"
MANIFEST = HERE / "manifest.csv"
CHECKPOINT = HERE / "candidate.pt"
OUTPUT = HERE / "raw_candidate_test.jsonl"
REPORT = HERE / "RESULTS_CANDIDATE_TEST.md"
DEVICE = "cuda"
BATCH_SIZE = 16
RESIZE = (224, 224)
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
    rows.sort(key=lambda row: row["image"])
    if not rows:
        raise RuntimeError("manifest has no test rows")
    from models.weight_head import WeightHead
    model = WeightHead.load(CHECKPOINT, device=DEVICE)
    transform = transforms.Compose([
        transforms.Resize(RESIZE), transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    metadata = {
        "event": "run_metadata", "dataset": "VLM Food Benchmark",
        "source_revision": "d715df0c0debe65da805618431e67f6d0fa01c71",
        "split": "test", "test_participants": ["participant_6"],
        "image_count": len(rows), "test_selection_allowed": False,
        "train_split_read": False, "dev_split_read": False,
        "manifest_sha256": sha256(MANIFEST),
        "candidate_checkpoint_sha256": sha256(CHECKPOINT),
        "cuda_device": torch.cuda.get_device_name(0),
        "torch": torch.__version__, "cuda_version": torch.version.cuda,
    }
    OUTPUT.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metadata, sort_keys=True), flush=True)
    results = []
    model.eval()
    with torch.inference_mode():
        for start in range(0, len(rows), BATCH_SIZE):
            batch = rows[start:start + BATCH_SIZE]
            tensors = []
            for row in batch:
                image_path = DATA / "GT_Mensa_2025/resized_images" / row["image"]
                with Image.open(image_path) as image:
                    tensors.append(transform(image.convert("RGB")))
            pixels = torch.stack(tensors).to(DEVICE)
            features = model.encode(pixels, no_grad=True)
            height, width = features.shape[-2:]
            rois = torch.tensor(
                [[i, 0.0, 0.0, float(width), float(height)] for i in range(len(batch))],
                dtype=torch.float32, device=DEVICE,
            )
            estimates = model(features, rois).squeeze(1).clamp(min=0).square().cpu().tolist()
            for row, estimate in zip(batch, estimates, strict=True):
                truth = float(row["total_food_g"])
                result = {
                    "event": "image_result", "image": row["image"],
                    "participant_id": row["participant_id"],
                    "ground_truth_total_g": truth,
                    "predicted_total_g": float(estimate),
                    "signed_error_g": float(estimate) - truth,
                    "item_count": int(row["item_count"]),
                }
                results.append(result)
                with OUTPUT.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(result, sort_keys=True) + "\n")
    truth = np.asarray([row["ground_truth_total_g"] for row in results], dtype=np.float64)
    prediction = np.asarray([row["predicted_total_g"] for row in results], dtype=np.float64)
    with MANIFEST.open(newline="", encoding="utf-8") as stream:
        train_dev = [row for row in csv.DictReader(stream) if row["split"] in {"train", "dev"}]
    median = float(np.median([float(row["total_food_g"]) for row in train_dev]))
    median_pred = np.full_like(truth, median)
    report = {
        "test_count": len(results),
        "test_participants": sorted({row["participant_id"] for row in results}),
        "candidate_mae_g": float(np.mean(np.abs(prediction - truth))),
        "candidate_signed_bias_g": float(np.mean(prediction - truth)),
        "candidate_median_g": float(np.median(prediction)),
        "candidate_prediction_min_g": float(np.min(prediction)),
        "candidate_prediction_max_g": float(np.max(prediction)),
        "train_dev_global_median_g": median,
        "train_dev_median_mae_g": float(np.mean(np.abs(median_pred - truth))),
        "candidate_minus_median_mae_g": float(
            np.mean(np.abs(prediction - truth)) - np.mean(np.abs(median_pred - truth))
        ),
        "test_used_for_selection": False,
        "raw_jsonl": str(OUTPUT),
        "wall_elapsed_s": time.perf_counter() - started,
    }
    lines = [
        "# VLM Food Benchmark candidate test", "",
        ("One participant group (participant_6) was reserved as the final test. "
         "This is one cluster and does not support confidence-interval claims."), "",
        "| Metric | Candidate | Train+dev median | Difference |",
        "|---|---:|---:|---:|",
        (f"| Test MAE g | {report['candidate_mae_g']:.3f} | "
         f"{report['train_dev_median_mae_g']:.3f} | "
         f"{report['candidate_minus_median_mae_g']:+.3f} |"),
        f"| Signed bias g | {report['candidate_signed_bias_g']:+.3f} | — | — |",
        (f"| Predicted range g | {report['candidate_prediction_min_g']:.1f}–"
         f"{report['candidate_prediction_max_g']:.1f} | — | — |"), "",
        "## Per-image results", "",
        "| Image | True total g | Predicted g | Signed error g | Items |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in results:
        lines.append(
            f"| {row['image']} | {row['ground_truth_total_g']:.1f} | "
            f"{row['predicted_total_g']:.1f} | {row['signed_error_g']:+.1f} | "
            f"{row['item_count']} |"
        )
    lines.extend(["", ("Participant 6 is one photographer/device cluster. Results are "
                  "cross-dataset research evidence and do not establish Indian-meal "
                  "performance or justify serving integration."), ""])
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True), flush=True)
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
