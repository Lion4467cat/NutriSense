# 023 — Synthetic per-pixel surface-area integration

- **id**: 023
- **branch**: `codex/synthetic-mask-spill-loop`
- **date**: 2026-10-30
- **author**: Codex
- **status**: completed synthetic candidate; no serving change

## Hypothesis

The current estimator applies a single anchor scale and global tilt correction
to every pixel in a food mask. On elevated, curved food, the image scale varies
with depth and position. Integrating height against local world-space XY pixel
area may reduce the scene-dependent gram error seen with exact synthetic food
masks.

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| Absolute grams percent error | current estimator on exact synthetic food mask | at least 5 percentage points lower in ≥4 of 6 scenes | paired within each rendered scene |
| Largest per-scene absolute-error regression | 0 pp | no more than 2 percentage points | guard against a gain concentrated in a subset |

## Success criterion (written BEFORE coding)

The per-pixel candidate lowers absolute grams percent error by at least 5 percentage points in at least four of the six fixed synthetic scenes, with no scene regressing by more than 2 points.

## Change

Experiment-only candidate in `experiments/oracle_ablation/`; do not edit
`models/portion_estimator.py`, parameters, weights, or evaluation data. Render
the same six seeded scenes as ledger 022. Compare the current estimator on
the exact renderer food mask against integration of height times local
world-space XY pixel area derived from the synthetic metric depth and the
current fitted base plane. This is synthetic evidence only; it does not
authorize serving-path promotion.

## Sources

- `experiments/oracle_ablation/synthetic_mask_spill.py` — fixed six-scene renderer protocol and exact synthetic masks.
- `models/portion_estimator.py` — current global scale/tilt area and mean-height calculation.
- `docs/ledger/022-synthetic-mask-spill.md` — preceding diagnostic; clean exact-mask errors varied by scene and the 25% vessel-spill criterion failed.

## Result

The preregistered criterion was **not met**: improvement of at least 5
percentage points occurred in 0/6 scenes, and the largest absolute-error
regression was 21.11 percentage points. The per-pixel candidate underpredicted
all six scenes. No WED DEV, WED TRAIN, WED LOCKED, or ArUco observations were
used.

| Scene | Truth (g) | Global estimator (g; signed %) | Surface integration (g; signed %) | Change in absolute error (pp) |
| --- | ---: | ---: | ---: | ---: |
| plate_150_low | 150.00 | 154.99 (+3.33%) | 136.54 (−8.98%) | +5.65 |
| plate_250_mid | 250.00 | 239.67 (−4.13%) | 223.93 (−10.43%) | +6.30 |
| plate_450_high | 450.00 | 503.49 (+11.89%) | 387.05 (−13.99%) | +2.10 |
| bowl_150_low | 150.00 | 153.08 (+2.06%) | 115.24 (−23.17%) | +21.11 |
| bowl_250_mid | 250.00 | 237.17 (−5.13%) | 189.72 (−24.11%) | +18.98 |
| bowl_450_high | 450.00 | 499.25 (+10.95%) | 317.31 (−29.49%) | +18.54 |

Raw paired measurements are in
`experiments/oracle_ablation/synthetic_surface_area.jsonl`; command output is
in `experiments/oracle_ablation/synthetic_surface_area.stdout.txt`.

## Decision

- **revert** — the candidate failed the registered criterion and regressed all six synthetic scenes, so it is not a serving-path change.

## Follow-ups

Even a synthetic pass is not field validation. Keep any candidate isolated
until a separate, eligible real-world evaluation set and protocol exist.
