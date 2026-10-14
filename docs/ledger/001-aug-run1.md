# 001 — Train-time photometric augmentation + random erasing for the WED weight head

- **id**: 001
- **branch**: `loop-aug-run1`
- **date**: 2026-10-14
- **author**: agent (Buffy / Codebuff)

## Hypothesis

The deployable-path DEV MAE (20.30 g, entry 000) sits well above the head's
in-training val MAE (16.21 g golden). Part of that gap is overfitting to the
pixel statistics of the specific WED train captures: every image is fed to
the head with essentially its original photometry (train=True only applies a
p=0.5 horizontal flip). Real plates — and the frozen stress suite — vary
photometrically (brightness, contrast, blur, compression) and with partial
occlusion of the food region. Training exposure to those two axes should
reduce the overfit gap, moving both the central DEV MAE and the stress-suite
deltas in the improving direction.

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| DEV MAE (g) | 20.30 | ≤ 18.0, or at least paired-BETTER | plate-bootstrap 95% CI |
| DEV stress deltas (g) | +0.17 … +5.64 | each not worse beyond its CI | `tools/stress_suite`, "WED stress test, not real-world" |
| DEV coverage_90 | 0.8645 | stays within [0.80, 0.95] | guard — head retrain regenerates `weight_head_sigma.yaml`, which feeds the MC intervals |
| train/val curve gap | 16.21 val vs train | narrows | diagnostic only |

## Success criterion (written BEFORE coding)

One run, DEV tier only: the paired plate-bootstrap 95% CI of
ΔMAE (cand − base, `tools/compare_runs.py` vs the entry-000 baseline report
`data/reports/run_eval_dev.json`) excludes 0 in the improving direction, AND
no stress-suite delta worsens beyond its own paired CI. Additionally — added
before coding, same status — DEV 90% coverage must stay within [0.80, 0.95]
(because a keep regenerates `data/weight_head_sigma.yaml`, which feeds the
MC interval machinery). Keep ⇒ checkpoint + sigma + the 30-view golden MAE in
`tests/test_weight_head_load.py` are re-verified and re-pinned together, each
with the same documented reason. Failure ⇒ revert the augmentation commit,
keep this entry, proceed to lever (b) as a new entry.

## Change

- `tools/train_weight_head.py` — train-only (`WedPlates(train=True)`)
  augmentation added after the existing hflip, in one seeded block:
  photometric sequence (brightness/contrast/saturation jitter ≤ 0.4,
  Gaussian blur σ ≤ 1.5, JPEG/compression emulation of the stress axis) and
  random erasing (small cutout fraction of the ROI crop). No geometric augs
  beyond hflip (plates are top-down in WED); no mixup/CutMix (class-
  conditional gram regression makes label mixing semantically wrong).
  Single-variable discipline: epochs=100, AdamW(lr=1e-3, wd=1e-4),
  OneCycleLR(pct_start=0.3), seed=42, val split untouched — identical to the
  baseline recipe except the augmentation block.
- `data/weight_head.pt`, `data/weight_head_sigma.yaml` — regenerated only on
  a keep (run by the train tool itself).
- `tests/test_weight_head_load.py` — golden 30-view val MAE re-pinned only on
  a keep, documented here.

## Sources

- `docs/ledger/000-baseline.md` — baseline numbers and harness definition.
- `tools/stress_suite.py` — frozen STAGE 1B perturbations (the robustness axis this entry targets).
- Zhong et al., *Random Erasing Data Augmentation* — https://arxiv.org/abs/1708.04896 (AAAI 2020) — cutout prior art; also available as `torchvision.transforms.RandomErasing`.

## Result

TBD — DEV run + stress + paired comparison pending.

## Decision

TBD.

## Follow-ups

TBD.
