"""Run the unchanged NutriSense pipeline on LeFood-Set's reserved test classes."""
from __future__ import annotations

import csv
import hashlib
import json
import logging
import sys
import time
from pathlib import Path

import cv2
import torch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MANIFEST = Path(__file__).resolve().parent / "manifest.csv"
OUTPUT = Path(__file__).resolve().parent / "raw_baseline_test.jsonl"
DAY = "mon"
BAND = "1-5"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; refusing CPU fallback")
    logging.basicConfig(level=logging.WARNING)
    with MANIFEST.open(newline="", encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["split"] == "test"]
    rows.sort(key=lambda row: int(row["row_id"]))
    if not rows:
        raise RuntimeError("manifest contains no test rows")

    import engine.pipeline as pipeline
    from models import registry
    from models.scale_anchor import read_exif

    timing_seen: list[dict[str, float]] = []
    original_log = pipeline.log_analysis

    def capture_log(verdict: str, day: str, band: str,
                    timings: dict[str, float]) -> None:
        timing_seen.append(dict(timings))
        original_log(verdict, day, band, timings)

    pipeline.log_analysis = capture_log
    metadata = {
        "event": "run_metadata",
        "dataset": "LeFood-Set V1",
        "doi": "10.17632/cchsk79jkt.1",
        "archive_sha256": sha256(ROOT / "datasets/raw/portion/lefood-set/LeFood-Set_v1.zip"),
        "manifest_sha256": sha256(MANIFEST),
        "split_read": "test",
        "split_rule": "whole-food-category-group hash; see DATA_AUDIT.md",
        "candidate_selection_allowed": False,
        "train_split_read": False,
        "cuda_device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "cuda_version": torch.version.cuda,
        "day": DAY,
        "band": BAND,
        "serving_style": "mixed",
        "image_count": len(rows),
        "food_category_count": len({row["food_name"] for row in rows}),
        "target_source": "Mendeley Weight Before Eaten (g), source-described food mass",
        "target_tare_caveat": "paper does not document tare handling",
        "pipeline_code_sha256": sha256(ROOT / "engine/pipeline.py"),
    }
    OUTPUT.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metadata, sort_keys=True), flush=True)
    verdict_counts: dict[str, int] = {}
    try:
        for index, row in enumerate(rows, start=1):
            path = ROOT / row["before_path"]
            image = cv2.imread(str(path))
            if image is None:
                raise RuntimeError(f"unreadable before image: {path}")
            start = time.perf_counter()
            timing_index = len(timing_seen)
            try:
                result = pipeline.analyze(
                    image, day=DAY, band=BAND, exif=read_exif(path),
                    serving_style="mixed")
                # Food label/ground truth are attached only after inference.
                record = {
                    "event": "image_result",
                    "index": index,
                    "row_id": row["row_id"],
                    "food_category_truth": row["food_name"],
                    "image": row["before_path"],
                    "ground_truth_food_g": float(row["before_g"]),
                    "predicted_total_g": (result.get("portion") or {}).get("grams"),
                    "dish": result.get("dish"),
                    "classification": result.get("classification"),
                    "anchor": result.get("anchor"),
                    "verdict": result.get("verdict"),
                    "reasons": result.get("reasons"),
                    "failures": result.get("failures"),
                    "portion": result.get("portion"),
                    "items": result.get("items") or [],
                    "segmentation": result.get("segmentation"),
                    "pipeline_timings_s": timing_seen[timing_index]
                    if len(timing_seen) > timing_index else {},
                    "elapsed_s": round(time.perf_counter() - start, 4),
                }
            finally:
                del image
                torch.cuda.synchronize()
            with OUTPUT.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            verdict = str(record.get("verdict") or "null")
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            print(json.dumps({
                "event": "image_complete", "index": index,
                "row_id": row["row_id"], "verdict": verdict,
                "predicted_total_g": record["predicted_total_g"],
                "elapsed_s": record["elapsed_s"],
            }, sort_keys=True), flush=True)
    finally:
        pipeline.log_analysis = original_log
        registry.unload()
        torch.cuda.synchronize()
    print(json.dumps({"event": "run_complete", "verdicts": verdict_counts,
                      "raw_jsonl": str(OUTPUT)}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
