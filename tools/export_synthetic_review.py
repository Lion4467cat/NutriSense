"""Export a stratified, human-editable synthetic sample review queue."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nutrisense_synth.corpus import DEFAULT_DATA_ROOT
from nutrisense_synth.review import review_gate, write_review_queue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_DATA_ROOT / "manifest.jsonl")
    parser.add_argument("--out", type=Path, default=DEFAULT_DATA_ROOT / "review_queue.csv")
    parser.add_argument("--per-stratum", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-acceptance", type=float, default=0.90)
    parser.add_argument("--apply-reviewed", action="store_true",
                        help="check the filled queue and save review_summary.json beside the manifest")
    args = parser.parse_args()
    if args.apply_reviewed:
        summary = review_gate(args.out, min_acceptance=args.min_acceptance,
                              manifest_path=args.manifest)
        summary_path = args.manifest.with_name("review_summary.json")
        summary_path.write_text(__import__("json").dumps(summary, indent=2) + "\n",
                                encoding="utf-8")
        print(f"review gate {'passed' if summary['passed'] else 'failed'}: {summary_path}")
        return 0 if summary["passed"] else 2
    count = write_review_queue(args.manifest, args.out, args.per_stratum, args.seed)
    print(f"wrote {count} stratified review rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
