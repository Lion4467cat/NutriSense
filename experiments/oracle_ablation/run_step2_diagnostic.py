"""Reproduce the Step 2 full-pipeline refusal diagnostic.

Uses the existing WED DEV plate carve (one deterministic view per plate) and
the six phone images already recorded in data/reports/real_photo_e2e.json.
No labels are fed to the analyzer. Model outputs, reasons, and timings are
written as JSONL for review.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable

import cv2
import torch

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "step2_raw.jsonl"
DAY = "mon"
BAND = "1-5"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _unload_models() -> None:
    from models import registry

    registry.unload()


def _measure_stage(name: str, fn: Callable[..., Any], peaks: dict[str, dict[str, float]]) -> Callable[..., Any]:
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        _unload_models()
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
        try:
            return fn(*args, **kwargs)
        finally:
            torch.cuda.synchronize()
            peaks[name] = {
                "allocated_peak_mb": round(torch.cuda.max_memory_allocated() / 2**20, 2),
                "reserved_peak_mb": round(torch.cuda.max_memory_reserved() / 2**20, 2),
            }
            _unload_models()

    return wrapped


class _DepthStage:
    def __init__(self, peaks: dict[str, dict[str, float]]) -> None:
        self.peaks = peaks

    def __call__(self, image_bgr: Any, fov_x: float | None = None) -> dict[str, Any]:
        from engine.depth import MonocularDepth

        return _measure_stage(
            "depth", MonocularDepth(), self.peaks
        )(image_bgr, fov_x=fov_x)


def _input_rows() -> list[dict[str, Any]]:
    from tools.run_eval import dev_rows, wed_root
    from tools.train_weight_head import plate_key

    root = wed_root()
    by_plate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in dev_rows():
        by_plate[plate_key(row)].append(row)
    rows: list[dict[str, Any]] = []
    for key in sorted(by_plate):
        chosen = min(by_plate[key], key=lambda row: row["image"])
        rows.append({
            "source": "WED_DEV",
            "source_path": str(root / chosen["image"]),
            "plate": key,
            "gt_dishes": chosen["dishes"],
        })

    phone_path = ROOT / "data/reports/real_photo_e2e.json"
    for row in json.loads(phone_path.read_text()):
        rows.append({
            "source": "phone_no_card",
            "source_path": str((ROOT / row["photo"]).resolve()),
            "plate": None,
            "gt_dishes": [],
        })
    return rows


def _categorize(result: dict[str, Any]) -> str:
    if result.get("verdict") == "out_of_scope":
        return "out_of_scope"
    if result.get("verdict") != "cannot_verify":
        return str(result.get("verdict"))
    kinds = {reason.get("kind") for reason in result.get("reasons") or []}
    if "off_menu_dish" in kinds:
        return "cannot_verify_by_design_off_menu"
    if kinds & {"zoom", "unknown_day", "unknown_band"}:
        return "input_gate_rejection"
    if "unrecognized" in kinds:
        return "classifier_abstention"
    failures = result.get("failures") or []
    if failures:
        return "stage_failure:" + ",".join(sorted({f.get("stage", "unknown") for f in failures}))
    return "cannot_verify_other"


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; refusing CPU fallback")
    logging.basicConfig(level=logging.WARNING)
    import engine.pipeline as pipeline
    from models.dish_segmenter import segment_food, segment_items
    from models.food_classifier import classify_dish
    from models import registry

    original_log_analysis = pipeline.log_analysis
    timing_rows: list[dict[str, Any]] = []

    def capture_log(verdict: str, day: str, band: str,
                    timings: dict[str, float]) -> None:
        timing_rows.append({"verdict": verdict, "timings": dict(timings)})
        original_log_analysis(verdict, day, band, timings)

    pipeline.log_analysis = capture_log
    rows = _input_rows()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("")

    print(json.dumps({
        "event": "run_started", "device": torch.cuda.get_device_name(0),
        "torch": torch.__version__, "cuda": torch.version.cuda,
        "day": DAY, "band": BAND, "n_images": len(rows),
        "wed_dev_plates": sum(r["source"] == "WED_DEV" for r in rows),
        "phone_images": sum(r["source"] == "phone_no_card" for r in rows),
        "view_selection": "lexicographically first image path per plate",
    }, sort_keys=True), flush=True)

    summary: dict[str, int] = defaultdict(int)
    for index, row in enumerate(rows, start=1):
        image_path = Path(row["source_path"])
        image = cv2.imread(str(image_path))
        if image is None:
            result_row = {
                "index": index, "source": row["source"],
                "source_path": str(image_path), "plate": row["plate"],
                "error": "image_unreadable",
            }
            summary["image_unreadable"] += 1
        else:
            from models.scale_anchor import read_exif

            stage_peaks: dict[str, dict[str, float]] = {}
            deps = {
                "segment": _measure_stage("segment", segment_food, stage_peaks),
                "classify": _measure_stage("classify", classify_dish, stage_peaks),
                "depth": _DepthStage(stage_peaks),
                "segment_items": _measure_stage("segment_items", segment_items, stage_peaks),
            }
            started = time.perf_counter()
            timing_index = len(timing_rows)
            try:
                result = pipeline.analyze(
                    image, day=DAY, band=BAND, exif=read_exif(image_path),
                    serving_style="mixed", deps=deps,
                )
                category = _categorize(result)
                summary[category] += 1
                comp = result.get("compliance") or {}
                item_rows = result.get("items") or []
                result_row = {
                    "index": index, "source": row["source"],
                    "source_path": str(image_path), "plate": row["plate"],
                    "gt_dishes": row["gt_dishes"],
                    "verdict": result.get("verdict"), "outcome_category": category,
                    "reason_codes": [r.get("kind") for r in result.get("reasons") or []],
                    "reason_text": [r.get("text") for r in result.get("reasons") or []],
                    "failures": result.get("failures") or [],
                    "dish": result.get("dish"), "anchor": result.get("anchor"),
                    "portion": result.get("portion"),
                    "segmentation": result.get("segmentation"),
                    "items": item_rows,
                    "compliance_nutrients": comp.get("nutrients"),
                    "policy": result.get("policy"),
                    "degradations": result.get("degradations"),
                    "path_used": result.get("path_used"),
                    "elapsed_s": round(time.perf_counter() - started, 3),
                    "pipeline_stage_timings_s": (
                        timing_rows[timing_index]["timings"]
                        if len(timing_rows) > timing_index else {}
                    ),
                    "stage_vram_peak": stage_peaks,
                }
            except Exception as exc:
                summary["uncaught_exception"] += 1
                result_row = {
                    "index": index, "source": row["source"],
                    "source_path": str(image_path), "plate": row["plate"],
                    "gt_dishes": row["gt_dishes"],
                    "error": f"{type(exc).__name__}: {exc}",
                    "elapsed_s": round(time.perf_counter() - started, 3),
                    "stage_vram_peak": stage_peaks,
                }
            finally:
                del image
                registry.unload()
                torch.cuda.synchronize()

        with OUT.open("a") as stream:
            stream.write(json.dumps(result_row, sort_keys=True, default=str) + "\n")
        print(json.dumps({
            "event": "image_complete", "index": index,
            "source": result_row["source"], "plate": result_row["plate"],
            "verdict": result_row.get("verdict", "ERROR"),
            "category": result_row.get("outcome_category", "uncaught_exception"),
            "reason_codes": result_row.get("reason_codes", []),
            "elapsed_s": result_row.get("elapsed_s"),
        }, sort_keys=True), flush=True)

    print(json.dumps({
        "event": "run_complete", "counts": dict(sorted(summary.items())),
        "raw_jsonl": str(OUT),
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
