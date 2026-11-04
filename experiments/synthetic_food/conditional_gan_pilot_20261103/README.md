# Conditional GAN appearance pilot

This experiment evaluates semantic-layout-to-RGB generation on the five requested WED classes. It is isolated from product inference and frozen production checkpoints. Generated RGB is composited only inside Blender's food mask; semantic masks, depth, geometry, volume, mass/density metadata, camera and marker data remain renderer-owned and unchanged.

## Current status

- Official SPADE/pix2pixHD feasibility research is in `RESEARCH.md`.
- `prepare_pilot_inputs.py` selects eligible WED TRAIN references and existing Blender samples, writing only under ignored `datasets/processed/conditional_gan_pilot_20261103/`.
- `spade_pilot.py` is an independent, project-authored 256 × 256 SPADE-style generator with a two-scale conditional PatchGAN. It uses 42 semantic channels and no depth input, avoiding the current trainer/inference depth-condition mismatch.
- `render_pilot.py` applies a local checkpoint to the five Blender masks and compares outputs against the frozen WED semantic segmenter.
- The 20-epoch RTX 4060 pilot and five fixed-mask outputs are complete. Four of five samples fail the frozen-segmenter consistency screen and are rejected for training; phulka is pending human review. See `RESULTS.md`.
- `datasets/processed/conditional_gan_pilot_20261103/human_review.csv` tracks the automated screen alongside class-identity, realism and label-validity fields that remain pending.
- No generated RGB is approved. Existing Blender labels and all production checkpoints remain unchanged.

## Reproduce / run

```bash
.venv/bin/python experiments/synthetic_food/conditional_gan_pilot_20261103/prepare_pilot_inputs.py
.venv/bin/python experiments/synthetic_food/conditional_gan_pilot_20261103/spade_pilot.py --epochs 20 --batch-size 1 --workers 1 --device cuda --amp --save-every 5
.venv/bin/python experiments/synthetic_food/conditional_gan_pilot_20261103/render_pilot.py --checkpoint datasets/processed/conditional_gan_pilot_20261103/spade_epoch_020.pt --device cuda
```

The training command intentionally fails fast when CUDA is absent; it does not fall back to a long CPU run. Outputs and WED-derived references stay under `datasets/processed/`, which is ignored. Do not copy WED images or derived checkpoints outside the authorized environment; WED dataset terms are not published (see `docs/licenses.md`). No upstream weights or code were downloaded.

## Frozen label checks

The GAN output is RGB only. The inference script restores all non-food pixels from Blender RGB, then runs the frozen DeepLabV3 checkpoint on the generated image. Per-class semantic IoU, area ratio and 2-pixel boundary F1 are diagnostics for label drift, not proof of realistic class identity. Human class-identity and realism review remain separate and pending.
