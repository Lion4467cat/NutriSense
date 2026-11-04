"""Verify pilot artifacts, physical labels and card/no-card pair invariants."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nutrisense_synth.evaluation import require_frozen_baseline
from nutrisense_synth.pilot import validate_pilot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path,
                        default=ROOT / "datasets/processed/synthetic_food_pilot_20261103")
    parser.add_argument("--baseline-report", type=Path,
                        default=ROOT / "experiments/synthetic_food/baseline_freeze.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    args = parser.parse_args()
    try:
        require_frozen_baseline(args.baseline_report)
        report = validate_pilot(args.pilot, source_manifest=args.manifest)
    except (ValueError, json.JSONDecodeError, FileNotFoundError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))
    return 0 if report["all_automated_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
