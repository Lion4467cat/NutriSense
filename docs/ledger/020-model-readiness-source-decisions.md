# 020 — Model readiness: source compatibility and promotion decisions

- **date**: 2026-10-30
- **baseline**: deployable WED DINOv2-S weight head; development carve only
- **baseline report**: `data/reports/run_eval_dev_008_baseline.json`
- **one-time final report**: `data/reports/run_eval_locked_final_008.json`
- **selection rule**: paired plate bootstrap on the fixed WED DEV carve; no
  LOCKED result used for tuning

## Goal and result

The current WED DEV reference is 15.034 g MAE across 108 views, 21 plates,
and 1,218 food ROIs (plate-bootstrap 95% CI 12.227–18.889 g). DEV is also
the plate carve used for epoch selection, so all DEV comparisons here are
model-selection evidence and do not establish independent generalization.

Three point-estimate candidates were evaluated on DEV and none passed the
paired improvement gate:

| Candidate | DEV MAE | Paired change vs baseline | Decision |
|---|---:|---:|---|
| Higher weight on large targets (ledger 017) | 16.268 g | +1.234 g; CI +0.539 to +1.947 | Reject |
| Cross-fitted per-food median bias correction (ledger 018) | 15.187 g | +0.153 g; CI −0.396 to +0.735 | Reject; no gain |
| ROI geometry features (ledger 019) | 15.613 g | +0.580 g; CI −0.186 to +1.312 | Reject |

A fourth candidate (10x AdamW weight decay; ledger 021) reduced pooled
WED TRAIN outer-CV MAE from 16.421 g to 16.274 g (paired plate-bootstrap
95% CI for the change [−0.281, −0.016] g), but increased boondi MAE by
39.1% over 62 ROIs. It failed its preregistered subgroup guardrail and was
rejected. The paired result is in `data/reports/compare_cv_weight_decay_021.json`.

The existing stronger-augmentation experiment (ledger 006) also regressed
DEV by 1.414 g. The serving checkpoint and sigma artifact remain byte-for-byte
the baseline. After model/configuration selection and threshold freeze, the
one-time LOCKED report measured **14.667 g MAE** over 2,793 ROIs / 48 plates
(plate-bootstrap 95% CI 13.331–16.029 g), with 82.77% nominal 90% interval
coverage. This is the final locked report, not a tuning result; it will not be
used to change weights, thresholds or claims.

## Source decisions

- **WED** is the only local source with the same target definition (food
  portion grams) and compatible capture/evaluation path. It remains the only
  source for the deployed mass head.
- **Nutrition5k** has image and per-ingredient gram targets, but its 555-row
  local run is a separate overhead-image task. Its 32.4 g test metric is a
  macro per-ingredient error and cannot be compared with WED per-ROI MAE.
  The preregistered leave-ingredient-out gate failed or lacked test coverage
  for several selected ingredients (ledger 012), so its checkpoint was
  rejected for serving. A separate 47-dish held-out nutrient report
  (`data/reports/nutrition5k_test_nutrients.json`) found all-slot meal totals
  unusable (3,208.595 g mass MAE; 2,916.463 kcal MAE). The oracle-present
  ingredient diagnostic is not deployable because it uses true test labels.
  It must not be concatenated as WED plate-grain rows.
- **ECUSTFD** has image/box/coin records in the local copy but no verified
  `portions.csv` measured mass/volume targets. It is not mass-loss eligible.
- **FinnFoodPics** has snack identity and calorie-tier workbook labels, not
  verified per-image food grams. It remains a snack/energy-tier auxiliary
  dataset only; no mass targets are inferred from kcal tiers.
- **Local ArUco captures** contain 23 images in six groups. Filename values
  do not prove food-only mass, tare semantics, or image correspondence;
  zero rows are currently score-eligible.

Therefore no multi-source mass training run was launched. Combining the
current sources into one gram target would violate the target compatibility
and leakage rules. A future source becomes eligible only after an auditable
adapter proves target semantics and the source passes an independent
one-source ablation.

## Grouped generalization estimate

Five-fold outer CV over WED TRAIN plates produced 16.421 g pooled MAE over
11,759 held-out ROIs / 198 plates (fold MAEs 15.684–18.096 g; fold standard
deviation 0.884 g). The fixed DEV plates were excluded from both fold fitting
and epoch selection; WED LOCKED was not read by this run. This is variability
evidence for the baseline recipe, not a candidate improvement or independent
dataset transfer result. Full report: `data/reports/cv_weight_head_s42_k5.json`.

## Promotion

**No promotion.** A lower in-sample loss, different task metric, or point
estimate without a negative paired plate-bootstrap interval is insufficient.
The existing deployable model remains in place. Remaining work is to address
plate/session systematic errors without adapting to plate identity at serving,
then evaluate on frozen development groups and the single final locked report.
