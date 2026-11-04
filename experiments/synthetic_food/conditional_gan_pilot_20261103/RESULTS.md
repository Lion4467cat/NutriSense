# Conditional GAN five-class pilot results

## Decision

**Do not scale this candidate or use its outputs for food-classification training.** The small 256 × 256 SPADE-style GAN was stable and fit comfortably on the requested RTX 4060, but its RGB output is not yet photorealistic or class-consistent for four of five classes. A frozen WED segmenter recognized the generated phulka region; that sample still needs human review. No sample is approved automatically.

![Eligible WED TRAIN reference, Blender input, GAN RGB, authoritative mask, and frozen-segmenter diagnostic](/home/tinkerer/Desktop/Nutrisense/NutriSense-main/datasets/processed/conditional_gan_pilot_20261103/five_class_comparison.png)

## Experiment

- Method: project-authored SPADE-style semantic generator with a two-scale conditional PatchGAN, feature-matching and paired reconstruction losses. No official code or weights were downloaded.
- Input: 42-channel one-hot semantic layout; no depth condition. The existing local pix2pix trainer was not reused because it trains with a zero depth channel but supplies normalized depth at inference.
- Training: 20 epochs, 20,760 steps, batch 1, AMP, 256 × 256, seed 42, eligible WED TRAIN only (1,038 views / 198 groups). Groups from the fixed DEV carve were excluded. No DEV, LOCKED, ArUco evaluation or WED test assets were read.
- Time/resources: 883.8 s total (14 min 44 s), mean 44.2 s/epoch, 23.5 images/s, peak allocated training VRAM 553.6 MB of the 8 GB device. Five GAN inferences took 0.128–0.312 s/image (mean 0.165 s); peak allocated inference VRAM was 131.6 MB. Segmenter diagnostic time is reported separately in `five_class_metrics.json` and ran on CPU.
- Losses: generator 33.42 → 27.21; discriminator 2.27 → 2.29; feature-matching 2.15 → 1.81; paired L1 0.201 → 0.134. These are optimization diagnostics, not visual-quality metrics.

## Frozen-segmenter consistency diagnostics

The same frozen DeepLabV3 checkpoint was run on each original Blender RGB and GAN RGB. IoU is against the unchanged Blender semantic mask; boundary F1 uses a 2 px tolerance. This is a domain diagnostic, not a real-world accuracy claim. The existing Blender renderer itself scored poorly on these render inputs, so the comparison is relative to that baseline.

| Class | Blender RGB IoU | GAN RGB IoU | GAN boundary F1 | GAN predicted/target area | Top predicted WED class | Pilot screen |
|---|---:|---:|---:|---:|---|---|
| Bottle-gourd curry | 0.000 | 0.000 | 0.000 | 0.000 | curd (14) | **Reject** |
| Chicken dum biryani | 0.000 | 0.000 | 0.000 | 0.000 | rasam (31) | **Reject** |
| Phulka | 0.146 | 0.757 | 0.821 | 0.757 | phulka (28) | Human review required |
| Salad | 0.000 | 0.179 | 0.374 | 0.179 | non-spicy-curry (25) | **Reject** |
| Steamed rice | 0.000 | 0.010 | 0.000 | 0.010 | phulka (28) | **Reject** |

The conservative research screen requires target-class IoU ≥ 0.50, 2 px boundary F1 ≥ 0.60, the target to be the top predicted food class, and predicted/target area ratio in [0.70, 1.30]. Passing only means human review is still required; it is not approval. Four outputs fail and are rejected for training. Phulka passes this machine screen but remains unapproved pending human class-identity and realism review.

Visual inspection agrees with the diagnostics: biryani, curry, rice and salad contain conspicuous noisy or wrong-colour textures and do not read as their assigned foods. Phulka is the most recognizable output, but the appearance is still stylized and requires a human decision. No human review has been recorded in the review sheet.

## Ground-truth preservation

For all five outputs, pixels outside the Blender food mask are byte-identical to the corresponding original Blender RGB, so background and ID 7 / 60 mm marker appearance remain unchanged. The generator wrote RGB only. The semantic masks, metric-depth maps, volume/mass metadata, density assumptions, camera parameters and marker pose were not modified. These properties do not make the generated food RGB semantically valid; the failed outputs remain rejected.

WED TRAIN references in the comparison sheet are eligible TRAIN examples also used for GAN training, so they are visual references, not held-out evidence. The model and images are WED-derived and stay local; WED's dataset terms are unpublished, so the checkpoint or images must not be publicly distributed.

## Recommendation

This confirms that a compact conditional SPADE-style model can be trained and run on the RTX 4060, but it does **not** yet show that this data volume and training setup can translate the simple Blender masks into trustworthy food appearances. Do not expand the corpus or train production models on these outputs. A next research trial should first diagnose why in-domain class-mask layouts (notably rice) collapse to other classes; consider training longer only if eligible TRAIN reconstruction samples show the generator has learned class-specific appearance. Any follow-up must use group-aware TRAIN-only inputs and repeat the same frozen-segmenter and human-review gates.

## Artifacts

- `RESEARCH.md`: official SPADE/pix2pixHD architecture, access, hardware and license review.
- `STATUS.md`: WED TRAIN support audit and protections.
- `README.md`: reproduction commands and experiment contract.
- `prepare_pilot_inputs.py`, `spade_pilot.py`, `render_pilot.py`: selection, training and RGB-only inference/evaluation scripts.
- Ignored outputs: `datasets/processed/conditional_gan_pilot_20261103/` including `five_class_comparison.png`, `five_class_metrics.json`, `human_review.csv` (human fields pending), checkpoints, training log and eligible TRAIN references.

Verification: focused Ruff and Python compilation passed; model CPU forward and one CPU gradient-update smoke checks passed. The actual training and five-class inference ran on the RTX 4060. No full test suite or protected evaluation was run.
