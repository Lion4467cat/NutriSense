# 022 — Synthetic mask spill and base-plane sensitivity

- **id**: 022
- **branch**: `codex/synthetic-mask-spill-loop`
- **date**: 2026-10-30
- **author**: Codex
- **status**: completed diagnostic; no pipeline candidate

## Hypothesis

The geometry estimator may turn non-food vessel pixels in an oversized mask
into positive food volume. In particular, extending a food mask to the vessel
edge can move the ring-fit base from the food surface boundary to the table;
raised rim pixels can then contribute height. This trial uses renderer ground
truth only to isolate that mechanism.

## Expected effect

| metric | baseline | expected after | note |
| --- | --- | --- | --- |
| Absolute total-grams percent error on the exact renderer food mask | synthetic GT | ≤5% on at least 5 of 6 scenes | sanity check for the renderer/estimator harness |
| Error increase after adding vessel pixels up to 25% of food-mask area | exact food mask | ≥10 percentage points on at least 4 of 6 scenes | controlled spill; scene is the paired unit |

## Success criterion (written BEFORE coding)

The harness reproduces the clean estimate within 5% in at least five of six synthetic scenes and adding vessel pixels equal to 25% of food-mask area increases absolute percentage error by at least 10 points in at least four paired scenes.

## Change

Diagnostic harness only, under `experiments/oracle_ablation/`; no estimator,
model, threshold, configuration, or checkpoint changes. It renders six
predefined plate/bowl scenes with known grams and compares the estimator on
the exact renderer food mask against that same mask plus vessel pixels equal
to 25% of the food-mask area. Outputs are synthetic evidence, not field
accuracy evidence.

## Sources

- `tests/synth/scene.py` — renderer supplies metric depth, object IDs, food mask, and grams ground truth.
- `models/portion_estimator.py` — current ring/table base-plane and height-volume implementation.
- `experiments/oracle_ablation/REPORT.md` — EVAL-ONLY ArUco diagnosis motivated this hypothesis; those images and labels are not inputs to this trial.

## Result

The preregistered criterion was **not met**: clean estimates were within 5%
in 3/6 scenes, and the absolute-error increase was at least 10 percentage
points in 0/6 scenes. The added spill increased estimated grams in all six
scenes, by 5.09–17.54 g, while absolute percentage error improved in two
under-predicted scenes. The fitted method stayed `ring` in all clean/spill
pairs. Added vessel pixels were at the food-base height in five scenes; in
`plate_450_high`, 0.5% of added pixels were on the 8 mm raised rim. The fitted
ring-plane camera-z intercept shifted +0.57 to +2.76 mm with spill. No WED
DEV, WED TRAIN, WED LOCKED, or ArUco observations were used as a tuning signal.

Per-scene outputs (`truth → clean / spill`, signed errors, and paired changes):

| Scene | Truth (g) | Clean (g; signed %) | 25% vessel spill (g; signed %) | Δ grams | Δ absolute error (pp) | Ring-plane c shift (mm) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| plate_150_low | 150.00 | 154.99 (+3.33%) | 160.08 (+6.72%) | +5.09 | +3.39 | +0.57 |
| plate_250_mid | 250.00 | 239.67 (−4.13%) | 248.52 (−0.59%) | +8.86 | −3.54 | +0.92 |
| plate_450_high | 450.00 | 503.49 (+11.89%) | 520.28 (+15.62%) | +16.79 | +3.73 | +1.37 |
| bowl_150_low | 150.00 | 153.08 (+2.06%) | 159.30 (+6.20%) | +6.22 | +4.15 | +1.29 |
| bowl_250_mid | 250.00 | 237.17 (−5.13%) | 247.43 (−1.03%) | +10.26 | −4.10 | +1.87 |
| bowl_450_high | 450.00 | 499.25 (+10.95%) | 516.80 (+14.84%) | +17.54 | +3.90 | +2.76 |

Exact per-run telemetry is in `experiments/oracle_ablation/synthetic_mask_spill.jsonl`;
the reproduction command output is in `experiments/oracle_ablation/synthetic_mask_spill.stdout.txt`.

## Decision

- **revert** — the preregistered criterion failed, so this run does not justify an estimator change.

## Follow-ups

Only if the synthetic mechanism is reproduced, design a separate candidate
experiment with an independent evaluation protocol before changing the
estimator. Do not tune or score against the ArUco plates.
