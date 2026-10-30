# 022 — Synthetic mask spill and base-plane sensitivity

- **id**: 022
- **branch**: `codex/synthetic-mask-spill-loop`
- **date**: 2026-10-30
- **author**: Codex
- **status**: preregistered diagnostic; no pipeline candidate

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
the exact food mask, a mask with controlled vessel spill, and an oracle
food-only mask. Outputs are synthetic evidence, not field accuracy evidence.

## Sources

- `tests/synth/scene.py` — renderer supplies metric depth, object IDs, food mask, and grams ground truth.
- `models/portion_estimator.py` — current ring/table base-plane and height-volume implementation.
- `experiments/oracle_ablation/REPORT.md` — EVAL-ONLY ArUco diagnosis motivated this hypothesis; those images and labels are not inputs to this trial.

## Result

Not run yet. No WED DEV, WED TRAIN, WED LOCKED, or ArUco observations are used
as a tuning signal in this diagnostic.

## Decision

- **revert** — provisional until the preregistered criterion is evaluated; this entry authorizes no product-code change.

## Follow-ups

Only if the synthetic mechanism is reproduced, design a separate candidate
experiment with an independent evaluation protocol before changing the
estimator. Do not tune or score against the ArUco plates.
