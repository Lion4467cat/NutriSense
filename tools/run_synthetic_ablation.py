"""Prepare a matched-budget synthetic fraction matrix for a model stage.

This writes an immutable condition plan. It does not train models; stage-run
orchestration remains a separate implementation task.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nutrisense_synth.ablation import METHODS, STAGE_ORDER, build_conditions
from nutrisense_synth.corpus import DEFAULT_DATA_ROOT, audit_manifest
from nutrisense_synth.evaluation import require_frozen_baseline
from nutrisense_synth.manifest import read_jsonl


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_DATA_ROOT / "manifest.jsonl")
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--baseline-report", type=Path,
                        default=ROOT / "experiments/synthetic_food/baseline_freeze.json")
    parser.add_argument("--stage", choices=STAGE_ORDER, required=True)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--total-examples", type=int, required=True)
    parser.add_argument("--out", type=Path,
                        default=ROOT / "datasets/processed/synthetic_food_v1/condition_plan.json")
    args = parser.parse_args()
    try:
        require_frozen_baseline(args.baseline_report)
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    errors = audit_manifest(args.manifest, args.data_root)
    if errors:
        parser.error("synthetic manifest/review gate failed: " + "; ".join(errors[:5]))
    rows = read_jsonl(args.manifest)
    available_methods = {str(row.get("method")) for row in rows}
    missing_methods = set(args.methods) - available_methods
    if missing_methods:
        parser.error(f"requested method data is absent from manifest: {sorted(missing_methods)}")
    classes = {int(annotation["class_id"])
               for row in rows for annotation in row.get("annotations", [])
               if annotation.get("task_valid", {}).get("classification")}
    if len(classes) != 41:
        parser.error(f"expected all 41 WED classes in candidate corpus, found {len(classes)}")
    conditions = build_conditions(args.total_examples, {class_id: 1 for class_id in classes},
                                  methods=args.methods)
    report = {
        "status": "prepared_not_run",
        "created_at": datetime.now(UTC).isoformat(),
        "stage": args.stage,
        "methods": args.methods,
        "synthetic_fractions": [0, .25, .5, .75, 1],
        "total_training_examples_per_condition": args.total_examples,
        "evaluation_tier": "dev",
        "source_split": "wed_train_excluding_seed42_dev_carve",
        "baseline_sha256": _sha(args.baseline_report),
        "manifest_sha256": _sha(args.manifest),
        "conditions": [asdict(item) for item in conditions],
        "training_run_completed": False,
        "promotion_decision": "pending",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"prepared {len(conditions)} matched conditions; training not run: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
