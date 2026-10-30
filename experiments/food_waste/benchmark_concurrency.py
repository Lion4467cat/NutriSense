"""One-worker, two-in-flight local /analyze GPU smoke measurement."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import torch

ROOT = Path(__file__).resolve().parents[2]
IMAGE = ROOT / "datasets/raw/portion/ai-servicesbb-food-waste/train/480660/row-0192.jpg"
OUT = Path(__file__).resolve().parent / "api_concurrency.json"


def _rss_mib(pid: int) -> float | None:
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return float(line.split()[1]) / 1024
    except OSError:
        pass
    return None


def main() -> None:
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; refusing CPU fallback")
    raw = IMAGE.read_bytes()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    log_dir = tempfile.mkdtemp(prefix="nutrisense-api-concurrency-")
    env = {**os.environ, "NUTRISENSE_LOG_DIR": log_dir}
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    stop = threading.Event()
    rss_samples: list[float] = []
    gpu_samples: list[float] = []

    def sample() -> None:
        while not stop.is_set():
            value = _rss_mib(server.pid)
            if value is not None:
                rss_samples.append(value)
            try:
                free, total = torch.cuda.mem_get_info()
                gpu_samples.append((total - free) / 2**20)
            except Exception:
                pass
            stop.wait(0.1)

    def post(client: httpx.Client, start: threading.Barrier) -> dict:
        start.wait()
        began = time.perf_counter()
        response = client.post(
            f"{base_url}/analyze",
            files={"file": (IMAGE.name, raw, "image/jpeg")},
            data={"day": "mon", "band": "1-5"},
        )
        elapsed = (time.perf_counter() - began) * 1000
        body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        return {
            "status": response.status_code,
            "elapsed_ms": round(elapsed, 1),
            "verdict": body.get("verdict"),
            "degradations": body.get("degradations"),
            "failure_stages": [failure.get("stage") for failure in (body.get("failures") or [])],
        }

    try:
        with httpx.Client(timeout=300) as client:
            for _ in range(120):
                if server.poll() is not None:
                    raise RuntimeError("uvicorn exited before healthy")
                try:
                    if client.get(f"{base_url}/health", timeout=1).status_code == 200:
                        break
                except httpx.HTTPError:
                    time.sleep(0.5)
            else:
                raise TimeoutError("API did not become healthy within 60 seconds")
            warmup_start = time.perf_counter()
            warm = client.post(
                f"{base_url}/analyze",
                files={"file": (IMAGE.name, raw, "image/jpeg")},
                data={"day": "mon", "band": "1-5"},
            )
            warmup = {
                "status": warm.status_code,
                "elapsed_ms": round((time.perf_counter() - warmup_start) * 1000, 1),
                "verdict": warm.json().get("verdict") if warm.status_code == 200 else None,
            }
            free, total = torch.cuda.mem_get_info()
            baseline_gpu_mib = (total - free) / 2**20
            sampler = threading.Thread(target=sample, daemon=True)
            sampler.start()
            wall_start = time.perf_counter()
            barrier = threading.Barrier(3)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(post, client, barrier) for _ in range(2)]
                barrier.wait()
                concurrent = [future.result() for future in futures]
            wall_ms = (time.perf_counter() - wall_start) * 1000
            stop.set()
            sampler.join(timeout=3)
    finally:
        stop.set()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=5)

    report = {
        "measurement": "one local uvicorn worker; one warmup, then two synchronized concurrent /analyze requests",
        "image_sha256": hashlib.sha256(raw).hexdigest(),
        "image_bytes": len(raw),
        "cuda_device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "cuda_version": torch.version.cuda,
        "warmup": warmup,
        "concurrent_requests": concurrent,
        "concurrent_wall_ms": round(wall_ms, 1),
        "http_status_counts": {str(code): sum(row["status"] == code for row in concurrent)
                                for code in sorted({row["status"] for row in concurrent})},
        "resource": {
            "server_peak_rss_mib": round(max(rss_samples), 1) if rss_samples else None,
            "gpu_used_mib_baseline_system": round(baseline_gpu_mib, 1),
            "gpu_used_mib_peak_system": round(max(gpu_samples), 1) if gpu_samples else None,
            "gpu_used_mib_peak_delta_system": round(max(gpu_samples)-baseline_gpu_mib, 1)
            if gpu_samples else None,
        },
        "limitations": [
            "Two simultaneous requests only; not sustained load or throughput evidence.",
            "Loopback on one RTX 4060 Laptop GPU; remote network and deployment host are unmeasured.",
        ],
    }
    OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
