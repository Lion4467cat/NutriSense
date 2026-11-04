"""Generate a local WED TRAIN-derived synthetic renderer corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nutrisense_synth.corpus import DEFAULT_DATA_ROOT, generate_renderer_corpus
from nutrisense_synth.evaluation import require_frozen_baseline
from nutrisense_synth.parameters import read_wed_train_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/wed_manifest.jsonl")
    parser.add_argument("--dataset-root", type=Path, default=ROOT / "data/wed")
    parser.add_argument("--output", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--baseline-report", type=Path,
                        default=ROOT / "experiments/synthetic_food/baseline_freeze.json")
    parser.add_argument("--method", choices=("renderer", "gan", "diffusion"), default="renderer")
    parser.add_argument("--checkpoint", type=Path,
                        help="Local GAN state checkpoint or local diffusion model directory")
    parser.add_argument("--revision", default="local-unversioned")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--scene", choices=("isolated_dish", "composed_thali"), default="isolated_dish")
    parser.add_argument("--samples-per-class", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--no-card-pairs", action="store_true")
    args = parser.parse_args()
    try:
        require_frozen_baseline(args.baseline_report)
    except (ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    appearance_method = None
    if args.method == "gan":
        if args.checkpoint is None:
            parser.error("--checkpoint is required for --method gan")
        from nutrisense_synth.methods.gan import GANMethod
        appearance_method = GANMethod(args.checkpoint, revision=args.revision, device=args.device)
    elif args.method == "diffusion":
        if args.checkpoint is None:
            parser.error("--checkpoint is required for --method diffusion")
        from nutrisense_synth.methods.diffusion import DiffusionMethod
        appearance_method = DiffusionMethod(args.checkpoint, revision=args.revision, device=args.device)
    rows = read_wed_train_manifest(args.manifest)
    samples = generate_renderer_corpus(
        rows, args.dataset_root, args.output,
        samples_per_class=args.samples_per_class, seed=args.seed,
        include_card_pairs=not args.no_card_pairs, scene_kind=args.scene,
        appearance_method=appearance_method,
    )
    print(json.dumps({"samples": len(samples), "manifest": str(args.output / "manifest.jsonl"),
                      "output": str(args.output), "method": args.method}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
