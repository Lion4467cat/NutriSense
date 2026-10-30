"""Run the unchanged serving pipeline once on the participant-held-out test."""
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
HERE = Path(__file__).resolve().parent
DATA = ROOT / "datasets/raw/portion/vlm-food-benchmark"
MANIFEST = HERE / "manifest.csv"
OUTPUT = HERE / "raw_pipeline_test.jsonl"
DAY = "mon"
BAND = "1-5"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


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
    rows.sort(key=lambda row: row["image"])
    if not rows:
        raise RuntimeError("manifest has no test rows")

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
        "event": "run_metadata", "dataset": "VLM Food Benchmark",
        "source_revision": "d715df0c0debe65da805618431e67f6d0fa01c71",
        "split_read": "test", "test_participants": ["participant_6"],
        "train_split_read": False, "dev_split_read": False,
        "image_count": len(rows), "manifest_sha256": sha256(MANIFEST),
        "day": DAY, "band": BAND, "serving_style": "mixed",
        "target_source": "sum of item weights; scale measured, empty plate tare subtracted",
        "pipeline_code_sha256": sha256(ROOT / "engine/pipeline.py"),
        "cuda_device": torch.cuda.get_device_name(0),
        "torch": torch.__version__, "cuda_version": torch.version.cuda,
    }
    OUTPUT.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metadata, sort_keys=True), flush=True)
    verdict_counts: dict[str, int] = {}
    try:
        for index, row in enumerate(rows, start=1):
            image_path = DATA / "GT_Mensa_2025/resized_images" / row["image"]
            image = cv2.imread(str(image_path))
            if image is None:
                raise RuntimeError(f"unreadable image: {row['image']}")
            started = time.perf_counter()
            timing_index = len(timing_seen)
            try:
                result = pipeline.analyze(
                    image, day=DAY, band=BAND, exif=read_exif(str(image_path)),
                    serving_style="mixed",
                )
                # Ground-truth rows are attached only after pipeline inference.
                record = {
                    "event": "image_result", "index": index,
                    "image": row["image"],
                    "participant_id": row["participant_id"],
                    "ground_truth_total_g": float(row["total_food_g"]),
                    "item_count": int(row["item_count"]),
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
                    "elapsed_s": round(time.perf_counter() - started, 4),
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
                "image": row["image"], "verdict": verdict,
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
