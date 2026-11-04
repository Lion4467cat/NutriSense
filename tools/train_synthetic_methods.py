"""Train the local WED-only GAN or validate a local diffusion candidate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=("gan", "diffusion"), required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--dataset-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "datasets/processed/synthetic_food_v1/models/gan.pt")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--baseline-report", type=Path,
                        default=ROOT / "experiments/synthetic_food/baseline_freeze.json")
    parser.add_argument("--review-queue", type=Path,
                        default=ROOT / "datasets/processed/synthetic_food_pilot_20261103/human_review.csv")
    args = parser.parse_args()
    from nutrisense_synth.evaluation import require_frozen_baseline
    from nutrisense_synth.review import review_gate
    try:
        require_frozen_baseline(args.baseline_report)
        review = review_gate(args.review_queue)
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    if not review["passed"]:
        parser.error("synthetic pilot human-review gate did not pass")
    if args.method == "gan":
        from nutrisense_synth.methods.gan_training import train_gan
        provenance = train_gan(args.manifest, args.dataset_root, args.output,
                               epochs=args.epochs, batch_size=args.batch_size,
                               learning_rate=args.learning_rate, device=args.device,
                               seed=args.seed)
        print(json.dumps(provenance, indent=2))
        return 0
    parser.error("Diffusion weights must be trained/adapted on the approved GPU runtime and reviewed for license/training-data overlap; the local adapter only loads reviewed local checkpoints.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
