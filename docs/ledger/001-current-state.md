# 001 — Current deployable-state snapshot (DINOv2 head, DEV 20.30 → 15.03 g)

- **id**: 001
- **branch**: `ui-motion-polish` (current HEAD `79aaeaf` + prior merges incl. `c5b3486`)
- **date**: 2026-10-15
- **author**: agent (doc refresh pass)

## Hypothesis

The backend is in a known deployable state: measured-tier scale anchor with card calibration, SIGLIP2 gallery-first classification with abstain, MoGe-2 depth calibrated on the card, geometry + learned-weight portioning, Monte Carlo nutrient intervals, and compliance scoring with coverage factors. The current run_eval tree reflects the latest deployable checkpoint and eval code; the docs and README flowchart should match that state rather than the earlier 20.30 g snapshot.

## Expected effect

No metric is being tuned here — this entry records the current state verbatim from a fresh `run_eval --tier dev` (+ `--stress`) run, the accompanying `compare_runs` outputs (cross-report + pairwise stress), and the updated README pipeline flowchart. Any later experiment should baseline against these numbers.

## Success criterion (written BEFORE editing docs)

- Fresh `run_eval --tier dev` completes and reports MAE with 95% CI and coverage_90 with 95% CI.
- Fresh `run_eval --tier dev --stress` completes and reports the five WED stress perturbations.
- `tools/compare_runs` runs both modes: cross-report (clean vs stress) and single-report pairwise stress (`--stress-x` / `--stress-y`), each producing a paired CI.
- `docs/ledger/001-current-state.md` records the exact numbers and compare_runs outputs.
- `README.md` pipeline flowchart is updated to reflect current stage language (lint note, classification abstain, depth calibration, learned-weight vs geometry no-card paths, MC n=4000, compliance coverage product).
- No protected file is edited; no eval lock is regenerated.

## Change

- Regenerated current-format reports under `/tmp` for the doc refresh:
  - `tools/run_eval --tier dev --out /tmp/doc_dev_clean.json`
  - `tools/run_eval --tier dev --stress --out /tmp/doc_dev_stress.json`
- Ran `tools/compare_runs` twice:
  - cross-report: `/tmp/doc_dev_clean.json` vs `/tmp/doc_dev_stress.json` → `/tmp/doc_compare_cross.json`
  - pairwise stress: `/tmp/doc_dev_stress.json` vs itself with `--stress-x brightness_contrast_0.7 --stress-y jpeg_q30` → `/tmp/doc_compare_pairwise.json`
  - pairwise stress auto: same report with `--stress-x perspective_30deg` → `/tmp/doc_compare_pairwise_auto.json`
- Updated `README.md` pipeline mermaid flowchart only (no other README section touched in this pass).
- Added `docs/ledger/001-current-state.md` as the current-state record.
- Committed `tools/compare_runs.py` separately as `79aaeaf` (pairwise stress CLI).

No protected file touched. The `/tmp` artifacts were used for doc writing and then deleted; `data/reports/` was deliberately left unchanged so the locked/manifest paths and any existing report history are not disturbed by a doc pass.

## Sources

- `/tmp/doc_dev_clean.json` — fresh DEV clean run_eval report (the numbers below).
- `/tmp/doc_dev_stress.json` — fresh DEV stress run_eval report.
- `/tmp/doc_compare_cross.json` — cross-report paired comparison.
- `/tmp/doc_compare_pairwise.json` — pairwise stress comparison (brightness_contrast_0.7 vs jpeg_q30).
- `/tmp/doc_compare_pairwise_auto.json` — pairwise stress auto-pick (perspective_30deg vs first other perturbation).
- `tools/run_eval.py`, `tools/compare_runs.py` — the tools that produced the numbers.
- `README.md` — prior flowchart text, replaced in place.

## Result

All commands completed with exit 0. The current deployable DEV numbers are:

| report | tier | views | plates | samples | MAE (g) | 95% CI (g) | MAPE % | coverage_90 | 95% CI (cov) | mean interval width (g) | wall_s | peak_vram_mb |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DEV clean | dev | 108 | 21 | 1218 | 15.034 | [12.227, 18.889] | 18.3 | 0.8522 | [0.792, 0.899] | 62.16 | 5.06 | 121.0 |
| DEV stress | dev | 108 | 21 | 1218 | 15.034 | [12.227, 18.889] | 18.3 | 0.8522 | [0.792, 0.899] | 62.16 | 20.57 | 121.0 |

Config common to both: device `cuda`, checkpoint `data/weight_head.pt`, limit `None`, split `WED val carve from train plates (seed 42, 10% of plates)`, seed 42, split_seed 42, val_frac 0.1, bootstrap_reps 2000, z90 1.644854, n_skipped_no_sigma 0.

Worst-3 dishes (both clean and stress, identical): `beans-curry` 40.64 g, `non-spicy-curry` 31.06 g, `steamed-rice` 28.08 g.

DEV stress perturbation deltas (label `WED stress test, not real-world`):

| perturbation | MAE (g) | MAPE % | coverage_90 | worst3 |
| --- | --- | --- | --- | --- |
| brightness_contrast_0.7 | 15.176 | 18.59 | 0.8473 | beans-curry 40.42, non-spicy-curry 32.12, steamed-rice 29.02 |
| gaussian_blur_k9 | 15.197 | 18.56 | 0.8489 | beans-curry 40.45, non-spicy-curry 30.91, steamed-rice 28.4 |
| perspective_30deg | 17.901 | 22.08 | 0.7997 | beans-curry 42.3, steamed-rice 40.77, non-spicy-curry 39.45 |
| jpeg_q30 | 15.2 | 18.59 | 0.8448 | beans-curry 40.7, non-spicy-curry 30.74, steamed-rice 29.02 |
| half_resolution | 15.05 | 18.36 | 0.8514 | beans-curry 40.63, non-spicy-curry 31.05, steamed-rice 28.1 |

`compare_runs` cross-report (clean vs stress): MAE diff 0.0, paired 95% CI [0.0, 0.0]; coverage_90 diff 0.0, paired 95% CI [0.0, 0.0]. Stress perturbations were all `missing_in_baseline` because the clean report has no stress block — that is expected and not a failure.

`compare_runs` pairwise stress (single report, brightness_contrast_0.7 vs jpeg_q30): mae_g baseline 15.176 → candidate 15.2, diff 0.024, paired 95% CI [-0.208, 0.231]; coverage_90 baseline 0.8473 → candidate 0.8448, diff -0.0025, paired 95% CI [-0.0146, 0.0095].

`compare_runs` pairwise stress auto-pick (single report, perspective_30deg vs auto-picked brightness_contrast_0.7): mae_g baseline 17.901 → candidate 15.176, diff -2.726, paired 95% CI [-3.452, -1.958]; coverage_90 baseline 0.7997 → candidate 0.8473, diff 0.0476, paired 95% CI [0.0244, 0.071].

## Decision

- **keep** — this entry is a state record, not a model change. The current numbers are internally consistent (clean and stress DEVs identical because stress runs the same checkpoint/plates on perturbed images; cross-report diff is 0 because both reports are from the same deployable path), and the docs now reflect the current flowchart language.

## Follow-ups

- The prior DEV baseline in `docs/ledger/000-baseline.md` still says 20.298 g; that is historically correct for the old harness state and is not overwritten here. If the team wants a single “current reference” number, point new experiments at this entry and at a fresh `run_eval --tier dev`.
- The stale `data/reports/run_eval_dev_stress.json` in the tree lacks `per_plate` and is refused by `compare_runs`; regenerate it with current `run_eval` before using it in a comparison.
- Committing the fresh run_eval JSONs to `data/reports/` is a separate decision; this doc pass intentionally did not do that.
