"""STAGE 2: pipeline performance baseline (measure only — no behaviour change).

Profiles full end-to-end analyze() calls and records per-stage wall time
(segmentation, classification, depth, portion, Monte Carlo nutrition) plus
total wall time and per-run peak VRAM (torch.cuda.max_memory_allocated).

Two inputs per invocation:
  * synthetic no-card scene (tests.synth.scene.render_scene) with the
    classifier stubbed to rice_sambar — a stub is required because the real
    gallery abstains on synthetic renders, which would skip depth/portion/
    nutrition and leave the baseline incomplete;
  * one real photo from ../DATASET (first sorted jpg, read-only) with the
    real classifier — may abstain, in which case the later stages simply
    have no samples for that input.

4 runs per input; run 1 is warm-up (model loads, cudnn autotune) and is
dropped; median and p95 are computed over the remaining 3 runs. Stage times
are captured by wrapping engine.pipeline.stage in this script only — the
pipeline itself is untouched.

Usage:
  .venv/bin/python -m tools.profile_pipeline --label before \\
      --golden-out /tmp/golden_before.json
  .venv/bin/python -m tools.profile_pipeline --label after \\
      --golden-out /tmp/golden_after.json --compare-to /tmp/golden_before.json
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

STAGES = ("segment", "classify", "depth", "portion", "nutrition")


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=_ROOT,
        text=True).strip()


def _machine() -> dict:
    import torch
    info = {"platform": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "cuda_available": torch.cuda.is_available()}
    if torch.cuda.is_available():
        info["gpu"] = torch.cuda.get_device_name(0)
    return info


def _wrap_stage_recorder(rec: dict):
    import engine.pipeline as pl
    real = pl.stage

    def wrapped(name, fn, *args, **kwargs):
        t0 = time.perf_counter()
        out = real(name, fn, *args, **kwargs)
        key = str(name)
        rec.setdefault(key, []).append((time.perf_counter() - t0) * 1000.0)
        return out

    return real, wrapped


def _render_synthetic():
    from tests.synth.scene import render_scene
    scene = render_scene({"anchor": {"card": False}})
    return scene["image_bgr"], {"grams_gt_total": scene["grams_gt_total"]}


def _real_photo():
    import cv2
    cands = sorted(Path("../DATASET").resolve().glob("*/*.jpg"))
    if not cands:
        return None, None
    img = cv2.imread(str(cands[0]))
    return img, {"path": str(cands[0])}


def _stub_classify(img, **_kw):
    return {"dish": "rice_sambar", "confidence": 1.0, "method": "stub",
            "match_score": 0.9, "margin": None, "scores": {}, "uncovered": [],
            "reason": "profile stub (synthetic input)"}


def _run_once(image_bgr, deps):
    import torch
    from engine.pipeline import analyze
    if torch.cuda.is_available():
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    out = analyze(image_bgr, day="mon", band="1-5", deps=deps)
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    total_ms = (time.perf_counter() - t0) * 1000.0
    peak = (torch.cuda.max_memory_allocated() / 2**20
            if torch.cuda.is_available() else 0.0)
    return out, total_ms, peak


def _stats(samples: list[float]) -> dict:
    return {"median_ms": round(statistics.median(samples), 1),
            "p95_ms": round(_p95(samples), 1)}


def _p95(samples: list[float]) -> float:
    s = sorted(samples)
    if len(s) == 1:
        return s[0]
    k = 0.95 * (len(s) - 1)
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _profile(label: str, name: str, image_bgr, deps,
             rec: dict[str, list[float]]) -> tuple[dict, dict]:
    rec.clear()
    _run_once(image_bgr, deps)  # warm-up: model loads + cudnn autotune
    rec.clear()
    totals, peaks, outs = [], [], []
    for i in range(4):
        out, total_ms, peak = _run_once(image_bgr, deps)
        outs.append(out)
        totals.append(total_ms)
        peaks.append(peak)
        print(f"[{label}/{name}] run {i + 1}/4 total {total_ms:.0f} ms "
              f"peak_vram {peak:.0f} MiB", flush=True)
    summary = {s: _stats(rec[s]) for s in STAGES if s in rec}
    summary["total"] = _stats(totals)
    summary["peak_vram_mib"] = _stats(peaks)
    return outs[-1], summary


def _compare(golden_path: Path, current: dict) -> None:
    golden = json.loads(golden_path.read_text())
    # Normalise the live object to what json round-trips produce, so tuples /
    # numpy scalars compare equal to their golden JSON counterparts.
    current = json.loads(json.dumps(current))
    diffs = []

    def walk(a, b, path=""):
        if isinstance(a, dict) and isinstance(b, dict):
            if set(a) != set(b):
                diffs.append(f"{path}: key sets differ "
                             f"{sorted(set(a) ^ set(b))[:5]}")
                return
            for k in a:
                walk(a[k], b[k], f"{path}.{k}")
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                diffs.append(f"{path}: length {len(a)} != {len(b)}")
                return
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{path}[{i}]")
        elif isinstance(a, bool) or isinstance(b, bool):
            if a != b:
                diffs.append(f"{path}: {a!r} != {b!r}")
        elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if abs(float(a) - float(b)) > 1e-6:
                diffs.append(f"{path}: {a!r} != {b!r}")
        elif a != b:
            diffs.append(f"{path}: {a!r} != {b!r}")

    walk(golden, current)
    if diffs:
        print("GOLDEN MISMATCH:")
        for d in diffs[:20]:
            print(" ", d)
        raise SystemExit(1)
    print("GOLDEN MATCH: outputs identical within 1e-6")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--label", required=True, help="before | after")
    ap.add_argument("--golden-out", required=True)
    ap.add_argument("--compare-to", default=None)
    ap.add_argument("--runs", type=int, default=4)
    args = ap.parse_args()

    import engine.pipeline as pl

    rec: dict[str, list[float]] = {}
    real_stage, wrapped = _wrap_stage_recorder(rec)
    pl.stage = wrapped
    try:
        syn_img, syn_meta = _render_synthetic()
        syn_deps = {"classify": _stub_classify}
        syn_out, syn_summary = _profile(args.label, "synthetic", syn_img,
                                        syn_deps, rec)

        real_img, real_meta = _real_photo()
        real_out, real_summary = None, None
        if real_img is not None:
            real_out, real_summary = _profile(args.label, "real", real_img,
                                              {}, rec)
    finally:
        pl.stage = real_stage

    Path(args.golden_out).write_text(json.dumps(syn_out, indent=2,
                                                sort_keys=True) + "\n")
    if args.compare_to:
        _compare(Path(args.compare_to), syn_out)

    report = {"label": args.label, "git_commit": _git_commit(),
              "machine": _machine(), "warmup_dropped": 1,
              "runs_scored": args.runs - 1,
              "synthetic": syn_meta, "synthetic_stats": syn_summary,
              "real": real_meta, "real_stats": real_summary,
              "real_verdict": (real_out or {}).get("verdict")}
    out = Path(f"/tmp/profile_{args.label}.json")
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"wrote {args.golden_out}, {out}")


if __name__ == "__main__":
    main()
