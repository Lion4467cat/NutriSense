# 019 — Preserve food-region scale in the weight head

- **id**: 019
- **branch**: `spec-002-integration`
- **date**: 2026-10-30
- **author**: Codex

## Hypothesis

The weight head ROI-aligns every food box to a fixed 7×7 grid and globally
average-pools it. This removes explicit crop size before regression. Add three
fixed, label-independent geometric inputs derived only from the observed ROI:
log normalized width, log normalized height, and log normalized area. This
may help distinguish a small from a large portion when appearance is similar.
The frozen encoder, WED records, augmentation and optimization remain fixed.

## Leakage and generalization safeguards

- Every view of one WED plate stays in one partition; training's epoch
  selection is a plate carve from WED TRAIN.
- `--skip-test` must report zero WED test views. No candidate or threshold is
  chosen using LOCKED.
- The DEV tier is the same TRAIN plate carve used for epoch selection. Its
  results are model-selection evidence only, not an independent estimate.
- Candidate artifacts use isolated paths; the deployed checkpoint and sigma
  must be restored byte-identically after evaluation.

## Success criterion

Keep the architecture option only if the fresh paired DEV MAE change has a
plate-bootstrap 95% CI entirely below zero, coverage remains in [0.80, 0.95],
and no shared stress perturbation has a paired MAE-change CI entirely above
zero. Otherwise revert all ROI-geometry model/training changes. Do not tune
the feature set after observing this candidate.

## Change

Added an opt-in `roi_geometry` model/training path and trained with seed 42,
100 epochs, DINOv2-S, the existing WED TRAIN plate carve and `ledger001`
augmentation. `--skip-test` reported zero test views. Candidate checkpoint,
sigma and report were written to separate ignored paths. The architecture
round-tripped through `WeightHead.load` with matching train-validation MAE.

## Result

Fresh deployable-path DEV comparison over the same 21 plates / 1,218 ROIs:

- Baseline MAE: 15.034 g; candidate MAE: 15.613 g.
- Paired candidate-minus-baseline MAE: +0.580 g; plate-bootstrap 95% CI
  [−0.186, +1.312].
- Coverage: 0.8522 baseline / 0.8571 candidate.
- All five stress-transform point estimates were worse; none had a paired CI
  entirely below zero. No stress axis had a CI entirely above zero.

The DEV carve was also used for epoch selection, so this is development
evidence only. The deployed checkpoint and sigma were restored byte-identically
and hash-verified. LOCKED was not read.

## Decision

- **Rejected** — ROI geometry did not reduce MAE, so the pre-registered keep
  gate failed. Its model/training changes were removed; deployment artifacts
  remain unchanged.
