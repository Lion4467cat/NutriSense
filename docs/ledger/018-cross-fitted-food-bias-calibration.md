# 018 — Cross-fitted per-food bias calibration

- **id**: 018
- **branch**: `spec-002-integration`
- **date**: 2026-10-30
- **author**: Codex

## Hypothesis

The DEV profile shows persistent food-specific signed offsets (notably beans
curry, non-spicy curry, and aloo curry), while a global affine calibration
worsened MAE. A robust per-food residual median may remove only repeatable
class bias. To reduce calibration overfit, estimate each held-out plate's
correction from other plates only, using one residual summary per physical
plate/food pair.

## Fixed procedure

For each held-out DEV plate and food class, calculate the median of the other
plates' mean signed residuals for that food. Apply the additive correction
`prediction - median_residual`, clamped to zero. Require at least five other
plates containing that food; otherwise use zero correction. This threshold
and statistic are fixed before observing the result. No fitted value may use
any frame from its held-out plate. Bootstrap the paired MAE difference by
whole plates. Report subgroup behavior and the number of corrected samples.

This cross-fit prevents direct calibrator leakage between plates, but DEV was
also used for checkpoint epoch selection. The comparison remains model-
selection evidence, not an independent generalization estimate. No LOCKED
data may be read. If this procedure passes, fit the same fixed rule on all
available calibration plates, freeze its table and model together, then use
WED LOCKED only for the final report.

## Success criterion

Keep only if the paired plate-bootstrap 95% CI for corrected-minus-baseline
DEV MAE is entirely below zero, interval coverage remains in [0.80, 0.95],
and no food-size band with at least 50 samples has mean absolute error more
than 10% worse than baseline. Otherwise revert the calibration implementation.
Do not change the fixed correction rule after seeing the output.

## Change

`tools/eval_class_bias_calibration.py` applies the fixed leave-one-plate-out
diagnostic through the deployable baseline scorer. It does not modify the
checkpoint, sigma file, or serving path. Synthetic tests verify that a
held-out plate's own residual cannot affect its correction.

## Result

Report `data/reports/run_eval_dev_018_bias_calibration.json`:

- Baseline DEV MAE: 15.0338 g.
- Cross-fitted candidate DEV MAE: 15.1868 g.
- Paired change: +0.1530 g; plate-bootstrap 95% CI [−0.3958, +0.7354].
- Baseline/candidate coverage: 0.8522 / 0.8522.

The paired interval does not show a reliable improvement, so the
pre-registered keep condition fails. The diagnostic never accessed LOCKED.
The candidate MAE is still tuning evidence because the same DEV carve was
used for checkpoint epoch selection.

## Decision

- **Rejected** — cross-fitted per-food median bias correction did not improve
  MAE; no calibration table was added to serving and the deployable
  checkpoint/sigma remain unchanged. Keep the diagnostic as a reusable
  measurement tool; do not promote this calibration rule.
