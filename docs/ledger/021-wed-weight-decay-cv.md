# 021 — WED head weight-decay regularization, grouped outer CV

- **date**: 2026-10-30
- **status**: preregistered before candidate training
- **baseline**: frozen DINOv2-S head recipe, AdamW weight decay `1e-4`
- **candidate**: same recipe, same seed and plate folds, weight decay `1e-3`

## Hypothesis

The five-fold TRAIN-only baseline has a 16.421 g pooled outer MAE. The small
head is trained for up to 100 epochs while the frozen encoder is fixed. A
10x increase in AdamW decay may reduce plate-specific fitting and improve
unseen-plate error without changing inputs, labels, architecture, augmentation,
or epoch-selection rules.

## Protocol and safeguards

- Use the same five outer WED TRAIN plate folds and inner plate-group epoch
  selection for baseline and candidate. The fixed DEV carve is excluded from
  all fold fitting and selection. WED LOCKED is never opened.
- Evaluate candidate-minus-baseline MAE on identical outer-held plates and
  bootstrap whole plates in paired draws (10,000 replicates).
- Keep only if the paired 95% CI upper bound is below 0 g and no food class
  with at least 50 outer-fold ROIs has a greater than 10% MAE regression;
  mean absolute plate-total error may not regress by more than 5%, and the
  absolute global signed bias may not worsen by more than 2 g.
- This is one preregistered candidate. Do not adjust the decay value after
  seeing its result. No DEV or LOCKED result may rescue a failed CV gate.
- A pass would establish a TRAIN-only development candidate, not authorize
  replacing the deployed artifact because the one-time LOCKED set has already
  been evaluated.

## Results

The paired reports are `data/reports/cv_weight_head_s42_k5_wd1e-4.json`,
`data/reports/cv_weight_head_s42_k5_wd1e-3.json`, and
`data/reports/compare_cv_weight_decay_021.json`.

- Baseline pooled outer MAE: **16.421 g**; candidate: **16.274 g**.
- Paired change: **−0.148 g**, 95% plate-bootstrap CI **[−0.281, −0.016]**,
  over the same 198 outer plates / 11,759 ROIs.
- Mean absolute plate-total error improved from 364.698 g to 354.561 g.
- Signed bias changed from −0.942 g to −1.110 g (absolute change 0.168 g,
  within the 2 g guardrail).
- The `boondi` subgroup (62 ROIs) regressed from 3.752 g to 5.220 g MAE
  (**+39.1%**). It exceeds the 10% guardrail. Other high-support classes
  passed that guardrail.

## Decision

**Reject.** Although the overall paired CV improvement is statistically
below zero and plate-total error improved, the pre-registered food-class
guardrail failed. Do not promote the checkpoint. Do not tune the decay value
or add a boondi-specific correction using these same outer-fold results.
These CV folds are now development evidence; the one-time WED LOCKED result
cannot be repeated, and the fixed DEV carve is already a tuning signal.
