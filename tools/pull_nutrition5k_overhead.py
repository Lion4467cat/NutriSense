"""07b data step: pull a Nutrition5k overhead-RGB subset for the
ingredient-conditional teacher.

Primary route history (2026-10-29): the public GCS bucket now contains ONLY
nutrition5k_dataset.tar.gz (194.8 GB) — the loose imagery/realsense_overhead/
objects listed by the original README no longer exist as individual objects
(verified: bucket listing = 1 item). The working unauthenticated route is the
HuggingFace mirror `mmathys/food-nutrients`: an ungated derivative of
Nutrition5k with the same overhead plates as `test/dish_XXXXX.png`, keyed by
identical dish ids (verified 2026-10-29: all 1,000 image ids match this
repo's local dish_metadata_cafe1/2.csv ids), plus metadata.jsonl with
per-ingredient grams.

Attribution chain: CC (source) -> Nutrition5k (Google Research, CC BY 4.0)
-> mirror. Images land git-ignored under data/nutrition5k/imagery/ per the
house cite-only rule (docs/licenses.md).

Usage:
  .venv/bin/python -m tools.pull_nutrition5k_overhead --limit 600
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import httpx

HF_API = "https://huggingface.co/api/datasets/mmathys/food-nutrients/tree/main/test"
HF_RAW = ("https://huggingface.co/datasets/mmathys/food-nutrients/resolve/main/"
          "test/{dish}.png")
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "nutrition5k"
METADATA_DIR = DATA_DIR / "metadata"
IMAGERY_DIR = DATA_DIR / "imagery" / "realsense_overhead"


def dish_ids_from_metadata() -> list[str]:
    ids: list[str] = []
    for csv_path in sorted(METADATA_DIR.glob("dish_metadata_cafe*.csv")):
        with open(csv_path) as f:
            for row in csv.reader(f):
                if row and row[0].startswith("dish_"):
                    ids.append(row[0])
    return ids


def available_dish_ids(client: httpx.Client) -> set[str]:
    """List the mirror's image ids (HF tree API, header-paginated)."""
    names: list[str] = []
    page = ""
    for _ in range(100):
        params = {"limit": 1000}
        if page:
            params["cursor"] = page
        r = client.get(HF_API, params=params)
        if r.status_code != 200:
            break
        items = r.json()
        names.extend(it["path"].rsplit("/", 1)[-1][:-4]
                     for it in items if it["path"].endswith(".png"))
        page = r.headers.get("X-Repo-Cursor") or r.headers.get("x-repo-cursor") or ""
        if not page:
            break
    return set(names)


def fetch_png(client: httpx.Client, dish: str) -> bool:
    r = client.get(HF_RAW.format(dish=dish), follow_redirects=True)
    if r.status_code != 200 or len(r.content) < 5_000 or r.content[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    out = IMAGERY_DIR / dish / "rgb.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(r.content)
    return True


def should_stop_clear() -> bool:
    import subprocess
    r = subprocess.run(
        [sys.executable, "-m", "tools.should_stop"],
        check=False, capture_output=True,
        cwd=Path(__file__).resolve().parent.parent)
    return r.returncode == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=600)
    args = ap.parse_args()

    if not should_stop_clear():
        print("should_stop: set — aborting before any fetch")
        return 0

    with httpx.Client(timeout=90.0, headers={"User-Agent": "nutrisense-07b/0.1"}) as client:
        wanted = available_dish_ids(client) & set(dish_ids_from_metadata())
        ordered = [d for d in dish_ids_from_metadata() if d in wanted]
        print(f"mirror has {len(wanted)} fetchable dishes matching local metadata; "
              f"target={args.limit}")
        t0 = time.time()
        ok = miss = 0
        for dish in ordered:
            if ok >= args.limit:
                break
            if (IMAGERY_DIR / dish / "rgb.png").is_file():
                ok += 1
                continue
            if not should_stop_clear():
                print("should_stop: set mid-run — stopping cleanly")
                return 0
            if fetch_png(client, dish):
                ok += 1
            else:
                miss += 1
            if (ok + miss) % 25 == 0:
                print(f"  ok={ok} miss={miss} t={time.time()-t0:.0f}s", flush=True)

    print(f"done: ok={ok} miss={miss} in {time.time()-t0:.0f}s -> {IMAGERY_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
