"""Measure local /analyze request latency and resource use.

Example:
  .venv/bin/python -m tools.benchmark_api --image /path/to/plate.jpg --runs 8

This is a local measurement, not a deployment SLO. It records the image hash
instead of the source path so reports do not disclose user directory names.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import httpx


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)


def _rss_mib() -> float | None:
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return round(float(line.split()[1]) / 1024, 1)
    except OSError:
        pass
    return None


def _process_rss_mib(pid: int) -> float | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024
    except OSError:
        pass
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--runs", type=int, default=6,
                    help="scored calls after one warm-up (default: 6)")
    ap.add_argument("--day", default="mon")
    ap.add_argument("--band", default="1-5")
    ap.add_argument("--output", type=Path,
                    default=Path("data/reports/api_benchmark.json"))
    args = ap.parse_args()
    if args.runs < 2:
        ap.error("--runs must be at least 2 to report a useful percentile")
    raw = args.image.read_bytes()
    upload_limit = int(os.environ.get("NUTRISENSE_MAX_UPLOAD_BYTES",
                                     str(12 * 1024 * 1024)))
    if len(raw) > upload_limit:
        ap.error(f"image is {len(raw)} bytes, above upload limit {upload_limit}")
    decoded = cv2.imdecode(np.frombuffer(raw, dtype="uint8"), cv2.IMREAD_COLOR)
    if decoded is None:
        ap.error("image cannot be decoded by OpenCV")

    latencies, verdicts, statuses = [], [], []
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    log_dir = tempfile.mkdtemp(prefix="nutrisense-api-benchmark-")
    env = {**os.environ, "NUTRISENSE_LOG_DIR": log_dir}
    gpu_baseline_mib = None
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        gpu_baseline_mib = (total - free) / 2**20
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        cwd=Path(__file__).resolve().parents[1], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    stop_sampling = threading.Event()
    server_rss_samples: list[float] = []
    gpu_used_samples: list[float] = []

    def sample_resources() -> None:
        while not stop_sampling.is_set():
            rss = _process_rss_mib(server.pid)
            if rss is not None:
                server_rss_samples.append(rss)
            if torch.cuda.is_available():
                try:
                    free, total = torch.cuda.mem_get_info()
                    gpu_used_samples.append((total - free) / 2**20)
                except Exception:
                    pass
            stop_sampling.wait(0.2)

    sampler = threading.Thread(target=sample_resources, daemon=True)
    try:
      with httpx.Client(timeout=300.0) as client:
        ready = False
        for _ in range(120):
            if server.poll() is not None:
                raise RuntimeError("uvicorn exited before becoming healthy")
            try:
                if client.get(f"{base_url}/health", timeout=1.0).status_code == 200:
                    ready = True
                    break
            except httpx.HTTPError:
                time.sleep(0.5)
        if not ready:
            raise TimeoutError("local API did not become healthy within 60 seconds")
        sampler.start()
        for i in range(args.runs + 1):
            start = time.perf_counter()
            response = client.post(
                f"{base_url}/analyze",
                files={"file": (args.image.name, raw, "image/jpeg")},
                data={"day": args.day, "band": args.band},
            )
            elapsed = (time.perf_counter() - start) * 1000
            statuses.append(response.status_code)
            if response.status_code == 200:
                verdicts.append(response.json().get("verdict", "missing"))
            if i > 0:
                latencies.append(elapsed)
    finally:
        stop_sampling.set()
        if sampler.is_alive():
            sampler.join(timeout=2)
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)
    report = {
        "measurement": "local uvicorn over loopback HTTP /analyze; sequential; first call dropped",
        "image_sha256": hashlib.sha256(raw).hexdigest(),
        "image_bytes": len(raw),
        "runs_scored": len(latencies),
        "http_status_counts": {str(s): statuses.count(s) for s in sorted(set(statuses))},
        "verdict_counts": {v: verdicts.count(v) for v in sorted(set(verdicts))},
        "latency_ms": {
            "p50": round(statistics.median(latencies), 1),
            "p95": round(_percentile(latencies, 0.95), 1),
            "min": round(min(latencies), 1),
            "max": round(max(latencies), 1),
        },
        "resource": {
            "server_rss_mib_after": round(server_rss_samples[-1], 1) if server_rss_samples else None,
            "server_peak_rss_mib": round(max(server_rss_samples), 1) if server_rss_samples else None,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "gpu_used_mib_baseline_system": round(gpu_baseline_mib, 1) if gpu_baseline_mib is not None else None,
            "gpu_used_mib_peak_system": round(max(gpu_used_samples), 1) if gpu_used_samples else None,
            "gpu_used_mib_peak_delta_system": round(max(gpu_used_samples) - gpu_baseline_mib, 1) if gpu_used_samples and gpu_baseline_mib is not None else None,
        },
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "upload_limit_bytes": upload_limit,
        },
        "limitations": [
            "Loopback single-process latency excludes remote network effects.",
            "Sequential single-worker measurement; no throughput or multi-worker claim.",
            "No deployment latency/resource budget has been specified.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
