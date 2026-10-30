"""Frozen inference-only evaluation on the official AI-ServicesBB test split.

This script is intentionally test-only. Its output must not inform tuning,
training, thresholds, configuration, or candidate selection.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sys
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import cv2
import torch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATASET_ID = "AI-ServicesBB/food-waste-dataset"
DATASET_SHA = "f008d0c7b41ea4408b66bd1b7bb9ecd58b70349d"
SPLIT = "test"
EXPECTED_ROWS = 160
EXPECTED_RECEIPTS = 4
PAGE_SIZE = 100
IMAGE_ROOT = ROOT / "datasets/raw/portion/ai-servicesbb-food-waste/test"
OUT_PATH = Path(__file__).resolve().parent / "raw_official_test.jsonl"
DAY = "mon"
BAND = "1-5"


def _get_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "NutriSense-frozen-test-eval/1.0"})
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def _dataset_revision() -> str:
    url = "https://huggingface.co/api/datasets/" + quote(DATASET_ID, safe="/")
    revision = _get_json(url).get("sha")
    if revision != DATASET_SHA:
        raise RuntimeError(f"dataset revision changed: expected {DATASET_SHA}, got {revision}")
    return revision


def _rows() -> list[dict]:
    base = "https://datasets-server.huggingface.co/rows"
    rows: list[dict] = []
    offset = 0
    total = None
    while total is None or offset < total:
        query = (
            f"?dataset={quote(DATASET_ID, safe='')}&config=default"
            f"&split={SPLIT}&offset={offset}&length={PAGE_SIZE}"
        )
        page = _get_json(base + query)
        total = int(page["num_rows_total"])
        for entry in page["rows"]:
            row = entry["row"]
            row["row_idx"] = int(entry["row_idx"])
            rows.append(row)
        offset += len(page["rows"])
        if not page["rows"]:
            break
    if len(rows) != EXPECTED_ROWS:
        raise RuntimeError(f"unexpected official test row count: {len(rows)}")
    receipts = {int(row["bonid"]) for row in rows}
    if len(receipts) != EXPECTED_RECEIPTS:
        raise RuntimeError(f"unexpected official test receipt count: {len(receipts)}")
    return rows


def _target(row: dict) -> float:
    values = row.get("Menge_Rückläufer")
    if not isinstance(values, list) or not values:
        raise ValueError(f"invalid returned-weight list for receipt {row['bonid']}")
    target = sum(float(value) for value in values)
    if target < 0:
        raise ValueError(f"negative food target for receipt {row['bonid']}")
    return target


def _download_image(row: dict) -> Path:
    image = row.get("image") or {}
    url = image.get("src")
    if not url:
        raise ValueError(f"missing image URL at test row {row['row_idx']}")
    receipt = int(row["bonid"])
    path = IMAGE_ROOT / str(receipt) / f"row-{int(row['row_idx']):04d}.jpg"
    if path.is_file() and path.stat().st_size:
        return path
    request = Request(url, headers={"User-Agent": "NutriSense-frozen-test-eval/1.0"})
    with urlopen(request, timeout=60) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError(f"empty image payload at test row {row['row_idx']}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; refusing CPU fallback")
    logging.basicConfig(level=logging.WARNING)
    revision = _dataset_revision()
    rows = _rows()
    by_receipt: dict[int, list[dict]] = {}
    for row in rows:
        by_receipt.setdefault(int(row["bonid"]), []).append(row)
    targets = {}
    for receipt, group in by_receipt.items():
        values = {_target(row) for row in group}
        if len(values) != 1:
            raise RuntimeError(f"inconsistent food targets for {receipt}: {values}")
        targets[receipt] = values.pop()
    rows.sort(key=lambda row: (int(row["bonid"]), int(row["row_idx"])))
    paths = {int(row["row_idx"]): _download_image(row) for row in rows}

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
    header = {
        "event": "run_metadata",
        "dataset": DATASET_ID,
        "dataset_revision": revision,
        "split_read": SPLIT,
        "train_split_read": False,
        "official_test_evaluation_only": True,
        "cuda_device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "cuda_version": torch.version.cuda,
        "day": DAY,
        "band": BAND,
        "serving_style": "mixed",
        "receipt_count": len(by_receipt),
        "image_count": len(rows),
        "target_source": "sum(Menge_Rückläufer), food-only grams",
        "pipeline_code_sha256": hashlib.sha256(
            (ROOT / "engine/pipeline.py").read_bytes()).hexdigest(),
    }
    OUT_PATH.write_text(json.dumps(header, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(header, sort_keys=True), flush=True)
    counts: dict[str, int] = {}
    try:
        for index, row in enumerate(rows, start=1):
            path = paths[int(row["row_idx"])]
            image = cv2.imread(str(path))
            if image is None:
                raise RuntimeError(f"unreadable source image: {path}")
            start = time.perf_counter()
            timing_idx = len(timing_seen)
            try:
                result = pipeline.analyze(
                    image, day=DAY, band=BAND, exif=read_exif(path),
                    serving_style="mixed")
                row_out = {
                    "event": "image_result",
                    "index": index,
                    "source_row_idx": int(row["row_idx"]),
                    "receipt_id": int(row["bonid"]),
                    "path": str(path),
                    "ground_truth_food_g": targets[int(row["bonid"])],
                    "ground_truth_components": [
                        {"label": str(label).strip(), "grams": float(grams)}
                        for label, grams in zip(row["Artikel"],
                                                row["Menge_Rückläufer"], strict=True)
                    ],
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
                    "pipeline_timings_s": timing_seen[timing_idx]
                    if len(timing_seen) > timing_idx else {},
                    "elapsed_s": round(time.perf_counter() - start, 4),
                }
            finally:
                del image
                torch.cuda.synchronize()
            with OUT_PATH.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(row_out, sort_keys=True, default=str) + "\n")
            verdict = str(row_out.get("verdict") or "null")
            counts[verdict] = counts.get(verdict, 0) + 1
            print(json.dumps({
                "event": "image_complete", "index": index,
                "receipt_id": row_out["receipt_id"], "verdict": verdict,
                "predicted_total_g": row_out["predicted_total_g"],
                "elapsed_s": row_out["elapsed_s"],
            }, sort_keys=True), flush=True)
    finally:
        pipeline.log_analysis = original_log
        registry.unload()
        torch.cuda.synchronize()
    print(json.dumps({"event": "run_complete", "counts": counts,
                      "raw_jsonl": str(OUT_PATH)}, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
