"""Generate a small renderer-only 41-class pilot and a human review sheet."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nutrisense_synth.evaluation import require_frozen_baseline
from nutrisense_synth.pilot import generate_pilot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--dataset-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "datasets/processed/synthetic_food_pilot_20261103")
    parser.add_argument("--baseline-report", type=Path,
                        default=ROOT / "experiments/synthetic_food/baseline_freeze.json")
    parser.add_argument("--seed", type=int, default=20261103)
    parser.add_argument("--thalis", type=int, default=3)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    args = parser.parse_args()
    try:
        require_frozen_baseline(args.baseline_report)
        summary = generate_pilot(args.manifest, args.dataset_root, args.output,
                                 seed=args.seed, image_size=(args.width, args.height),
                                 thali_count=args.thalis)
    except (ValueError, json.JSONDecodeError, FileNotFoundError) as exc:
        parser.error(str(exc))
    print(json.dumps({"summary": summary,
                      "manifest": str(args.output / "manifest.jsonl"),
                      "output": str(args.output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
