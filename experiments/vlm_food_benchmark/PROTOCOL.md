# VLM Food Benchmark participant-held-out experiment

## Purpose and limits

This research-only experiment uses a recent real-world university-canteen
dataset with item names and individually scale-weighed food grams, after
subtracting the empty-plate tare. The target for the first candidate is the
sum of the item grams in each image. This measures image-to-meal-total transfer
on this source; it does not establish performance on Indian meals or authorize
a serving-path change.

The dataset license is CC BY 4.0. Dataset images, labels, and model outputs
stay in the ignored local dataset directory. Cite Marchetti et al. and the
repository if derived outputs are redistributed. The upstream source reports
that images have no EXIF/GPS and participants are anonymous codes.

## Frozen split

Source: GTMensa 2025 from `Metabolic-Intelligence-Lab/vlm-food-benchmark`,
described in Marchetti et al., *Nutrients* 2026, 18(21), 3582,
DOI `10.3390/nu18213582`; captured at Git commit
`d715df0c0debe65da805618431e67f6d0fa01c71`. The audit script generates a
manifest before any inference. Split by participant/device group:

- Train: participants 1, 2, 4, and 5.
- Development: participant 3.
- Test: participant 6 (the largest group, 60 images).

No image or item from a participant crosses partitions. Use train only to fit
the candidate, dev only to select its epoch, and test only for one frozen
comparison. Do not tune on test results.

## Frozen comparison

1. Current serving pipeline: unchanged `engine.pipeline.analyze` on each test
   image with `day=mon`, `band=1-5`, and `serving_style=mixed`. Ground-truth
   labels are attached only after inference. Require CUDA and stop on CUDA
   failure; no CPU fallback.
2. One research candidate: frozen DINOv2-S encoder plus the existing ROI
   weight-head architecture with one scalar output for the whole image. Train
   on the participant train split against `sqrt(total_food_g)` with seed 42,
   batch size 16, AdamW (`lr=1e-3`), SmoothL1, and 80 epochs. Select the epoch
   with minimum development MAE; ties keep the earliest epoch. Then refit the
   head on train+dev for that fixed epoch count and evaluate test once.
3. Compare against the median total grams from train+dev. Report test MAE,
   signed bias, all per-image signed errors, prediction range, and the
   unchanged pipeline's numeric coverage and per-image result. Do not report
   confidence intervals: the test group is one participant/device cluster.

The candidate is research-only and will not be integrated into `main.py`,
`engine/`, production config, or existing checkpoints. A positive result on
this Italian canteen set would justify only a separate follow-up on a fresh,
Indian mixed-meal holdout; it does not permit reuse of ArUco EVAL-only plates
or WED LOCKED evidence.

## Reproduction

Run from the repository root using the project `.venv`:

```bash
./.venv/bin/python experiments/vlm_food_benchmark/audit_dataset.py
./.venv/bin/python experiments/vlm_food_benchmark/train_candidate.py
./.venv/bin/python experiments/vlm_food_benchmark/evaluate_candidate.py
./.venv/bin/python experiments/vlm_food_benchmark/run_pipeline_test.py
./.venv/bin/python experiments/vlm_food_benchmark/summarize_results.py
```

The source checkout and all images are under `datasets/raw/` and ignored by
Git. The scripts, manifest, protocol, raw predictions, and derived reports
are under `experiments/vlm_food_benchmark/`.
