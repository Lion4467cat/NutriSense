# 017 — Reweight larger portions during WED training

- **id**: 017
- **branch**: `spec-002-integration`
- **date**: 2026-10-30
- **author**: Codex

## Hypothesis

The deployable model has near-zero overall signed bias, but the new DEV
diagnostic profile shows that the `>=200 g` group has 43.865 g MAE and
−34.766 g mean bias (105 ROI samples). The lower groups are overestimated on
average. A global affine correction was also evaluated with leave-one-plate-
out fitting and worsened MAE by 0.263 g [0.189, 0.339]. A mild target-weighted
SmoothL1 objective may reduce large-portion underestimation without changing
the encoder, data, augmentation, or inference contract.

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| WED DEV MAE (g) | 15.034 | lower | paired plate-bootstrap CI, same 21 plates |
| WED DEV `>=200 g` bias (g) | −34.766 | closer to 0 | diagnostics on 105 ROIs |
| WED DEV coverage_90 | 0.8522 | remain 0.80–0.95 | candidate sigma refit from train validation carve |

## Success criterion (written BEFORE coding)

Keep the candidate only if a fresh deployable-path WED DEV comparison has
paired plate-bootstrap 95% CI for ΔMAE (candidate − baseline) entirely below
zero, DEV coverage_90 stays in [0.80, 0.95], and no shared DEV stress axis has
a paired ΔMAE CI entirely above zero; otherwise revert the training option.
No LOCKED data may be loaded. The candidate is trained and evaluated at a
separate path; the deployed checkpoint and sigma are restored byte-identically
after candidate scoring.

## Generalization and leakage safeguards

- WED grouping is by physical plate (`date_key+set`); all views from one plate
  stay together. Training's epoch-selection carve is made from TRAIN plates,
  and `--skip-test` must leave the WED test manifest unloaded.
- The 21-plate DEV set is held out from gradient updates, but it is used for
  candidate comparisons and therefore becomes a tuning signal. Its paired
  interval supports this experiment's decision only; it is not an independent
  estimate of population generalization, especially after repeated experiments.
- Do not choose thresholds, augmentations, losses, or checkpoints from LOCKED.
  If a candidate is frozen for release, use the authorized LOCKED protocol
  exactly once and report that result separately. A failed locked result cannot
  be tuned against and re-reported as a fresh locked score.
- Do not combine repeated views as independent samples in uncertainty
  estimates. Resample plates for confidence intervals and report plate counts.
- FinnFoodPics identities and their ten calorie tiers remain grouped. Its
  nominal mass labels are derived from workbook calorie tiers, not direct
  per-image weighing, so they are not interchangeable with WED gram labels.

## Change

`tools/train_weight_head.py` adds opt-in `--loss-weighting sqrt_mass`. The
candidate objective is a per-ROI SmoothL1 weighted mean with
`w_i = sqrt(max(gt_i, 1 g) / mean_batch_gt)` normalized to mean one. The
default objective remains unweighted. Training uses the same seed, DINOv2-S,
100 epochs, batch size, learning rate, WED split, and `ledger001` augmentation
as the current recipe. Candidate checkpoint, sigma, and training report use
separate non-deployment paths. The test split is skipped.

## Sources

- `data/reports/run_eval_dev_008_baseline.json` — fresh deployable DEV baseline.
- `data/reports/run_eval_diagnostics_dev_008.json` — portion-band errors and
  leave-one-plate-out calibration analysis.
- `docs/ledger/002-dinov2-encoder.md` — current DINOv2 weight-head recipe and
  paired DEV baseline.
- `docs/ledger/README.md` — pre-registration, DEV-only tuning, and decision
  requirements.

## Result

The candidate trained for 100 epochs with seed 42 and skipped the WED test
split. Epoch selection used the 10% plate-group carve from WED TRAIN; best
training-validation MAE was 16.27 g. No test views were loaded.

Fresh deployable-path DEV comparison (21 plates, 1,218 ROIs): baseline MAE
15.034 g; candidate MAE 16.268 g; paired candidate-minus-baseline difference
+1.234 g, plate-bootstrap 95% CI [+0.539, +1.947]. Coverage was 0.8522 vs
0.8563. The candidate was also worse on all five paired stress transforms:
brightness/contrast +1.070 g [0.380, 1.781], blur +1.213 g [0.495, 1.957],
perspective +1.552 g [0.868, 2.291], JPEG +1.087 g [0.461, 1.736], and half
resolution +1.218 g [0.527, 1.926].

This DEV tier is the same deterministic 10% TRAIN-plate carve used for epoch
selection, not a second independent holdout. These results are development
evidence only; they do not establish broad generalization. The candidate is
rejected without consulting WED LOCKED.

The deployed checkpoint and sigma were restored and their SHA-256 hashes match
their pre-evaluation backups exactly.

Candidate checkpoint SHA-256:
`74af0fd2eee52490489d8bafe18e88ee9c5036ad0c509bc868070c71d3f7e1fe`.
Deployed checkpoint SHA-256 after restore:
`4ae02ef39de2610d5dede9b95f84c66bfd1c797c5cff7f5d7125e56c40bae1a1`.

Reports:

- `data/reports/weight_head_train_017_sqrt_mass.json`
- `data/reports/run_eval_dev_017_base_stress.json`
- `data/reports/run_eval_dev_017_sqrt_mass_stress.json`
- `data/reports/run_eval_dev_017_comparison.json`

## Decision

- **Rejected** — DEV MAE and all five stress MAEs worsened with paired CIs
  above zero. The opt-in loss-weighting code was removed; the deployed
  checkpoint remains unchanged. LOCKED was not read.

## Follow-ups

- Do not replace the deployed weight checkpoint based on the subgroup result
  alone; promotion requires the full paired DEV and stress comparison above.
- This experiment uses existing WED data only and does not assume new capture,
  annotation, or downloads.
