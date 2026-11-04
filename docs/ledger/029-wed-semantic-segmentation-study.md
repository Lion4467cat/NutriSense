# 029 — controlled WED semantic segmentation study

- **id**: 029
- **branch**: `codex/iter-synthetic-card-homography-check`
- **date**: 2026-11-03
- **author**: Codex

## Hypothesis

Higher resolution, class-balanced meal sampling, food-appropriate augmentation, or a boundary-aware loss may improve small WED semantic regions. DeepLabV3+ or SegFormer-B0 may improve the frozen DeepLabV3 baseline at a comparable training budget.

## Expected effect

Improve tiny-region pixel recall and macro food IoU while preserving foreground IoU, region F1, priority-class IoU, boundary F1, merge/fragmentation proxies, and acceptable inference latency.

## Success criterion (written BEFORE coding)

As fixed in [the controlled study protocol](../../experiments/wed_native_segmentation/study_protocol.md) before candidate training: require at least +0.01 absolute macro food IoU and +5 percentage points in tiny-region pixel recall or IoU≥0.5 region recall, with paired 95% physical-group bootstrap intervals above zero for both; no foreground IoU or region F1 lower bound below −0.01; no priority-class IoU loss worse than −0.05; merge and fragmentation upper-bound increase at most +0.25 per meal; boundary F1 loss at most −0.01; and batch-1 latency at most 2× the frozen baseline.

## Change

Added a TRAIN-only controlled study runner and DeepLabV3+ / SegFormer-B0 variants. Stage A varied one factor at a time with a 10-epoch budget; Stage B compared the selected DeepLabV3 recipe with the two alternate architectures. All candidate checkpoints were frozen before evaluation on the same 108-view / 21-group WED DEV carve. The original DeepLabV3 checkpoint was re-evaluated as the reference and its SHA-256 remained `946a8adc50b131465da421c14caee19f03e4471ed883c8d77bdce119cb0ae963`.

The high-resolution candidate required a run-time adjustment: its physical batch was 1 with accumulation 2, and the ASPP global-pooling BatchNorm was held in evaluation mode after the first attempt stopped on a singleton-batch error. This makes it a practical high-resolution candidate, not a perfectly isolated resolution-only ablation. There were no GPU OOM events. No LOCKED, ArUco, WED test, synthetic, geometry, or weight data/code were used.

## Sources

- [Study protocol](../../experiments/wed_native_segmentation/study_protocol.md) — data separation, fixed training budget, metrics, and promotion rule.
- [Comparison report](../../experiments/wed_segmentation_study/dev_comparison/comparison_report.md) — DEV metrics, all candidate comparison, visual outputs, and recommendation.
- [Comparison JSON](../../experiments/wed_segmentation_study/dev_comparison/comparison_report.json) — all candidate per-class IoUs, group-bootstrap intervals, latency, memory, checkpoint hashes, and per-view semantic-region diagnostics.
- [Training summary](../../experiments/wed_segmentation_study/training_study_report.json) — group hashes, recipes, selected epochs, and training summaries.

## Result

Data tier: WED DEV, 108 views from 21 physical meal groups. The best candidate by DEV macro food IoU was the 10-epoch boundary-loss DeepLabV3. Global paired differences against the frozen reference:

| Comparison | Tier | Macro food IoU base → candidate | Paired Δ [95% group-bootstrap CI] | Tiny pixel recall base → candidate | Paired Δ [95% CI] |
|---|---|---:|---:|---:|---:|
| Frozen DeepLabV3 vs boundary-loss DeepLabV3 | dev | 0.8211 → 0.8047 | −0.0164 [−0.0245, −0.0072] | 0.3403 → 0.4162 | +0.0759 [+0.0152, +0.1256] |

The tiny-region IoU≥0.5 recall stayed at 0.0054 (2/370 semantic components); the candidate missed the required region-recall gain. Foreground IoU changed 0.9196 → 0.9034 (Δ −0.0162, 95% CI [−0.0181, −0.0145]); boundary F1 changed 0.5973 → 0.4873 (Δ −0.1100, 95% CI [−0.1234, −0.0973]). All seven candidates failed the predeclared promotion gate. The frozen reference was trained for 20 epochs; the fresh matched DeepLabV3 control and candidate comparisons used 10 epochs each.

## Decision

- **revert** — no candidate met the predeclared improvement gate, so keep the frozen DeepLabV3 as the product reference and retain the candidate checkpoints only as research artifacts.

## Follow-ups

Review the visual comparisons and priority-class tradeoffs before choosing a next supervised experiment. WED contains semantic masks but no instance IDs; all region, merge, and fragmentation values remain connected-component proxies and do not establish serving-level instance accuracy.
